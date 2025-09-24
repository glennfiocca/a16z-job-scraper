import asyncio
import os
from playwright.async_api import async_playwright
from flask import Flask
from models import db, Job
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    return app

async def scrape_a16z_jobs():
    """Scrape job listings from a16z jobs website"""
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        async with async_playwright() as p:
            # Launch browser in headless mode for efficiency
            browser = await p.chromium.launch(headless=True)
            
            try:
                # Step 1: Collect all job URLs first
                job_urls = await collect_all_job_urls(browser)
                print(f"Found {len(job_urls)} total job postings")
                
                # Step 2: Process each job URL individually
                for i, (job_url, company_name) in enumerate(job_urls):
                    try:
                        print(f"Processing job {i+1}/{len(job_urls)}: {job_url}")
                        
                        # Create a fresh page for each job to avoid context issues
                        page = await browser.new_page()
                        
                        try:
                            await page.goto(job_url, timeout=30000)
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            
                            # Wait for provider-specific elements to load
                            await wait_for_provider_elements(page, job_url)
                            
                            # Extract job information with provider-specific parsing
                            job_data = await extract_job_details_advanced(page, job_url, company_name)
                            
                            # Save to database
                            save_job_to_db(job_data)
                            
                            print(f"Saved job: {job_data.get('title', 'Unknown Title')} at {job_data.get('company', 'Unknown Company')}")
                            
                        except Exception as e:
                            print(f"Error processing job {i+1}: {e}")
                            continue
                        finally:
                            await page.close()
                        
                    except Exception as e:
                        print(f"Error with job {i+1}: {e}")
                        continue
                
            except Exception as e:
                print(f"Error during scraping: {e}")
            finally:
                await browser.close()
                
        print("Scraping completed!")

async def collect_all_job_urls(browser):
    """Collect all individual job posting URLs from the a16z jobs site"""
    page = await browser.new_page()
    job_urls = []
    
    try:
        print("Collecting job URLs from a16z jobs page...")
        await page.goto('https://jobs.a16z.com/jobs')
        await page.wait_for_load_state('networkidle')
        
        # Scroll to load all jobs with bounded strategy
        await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let previousHeight = 0;
                    let stableCount = 0;
                    let maxIterations = 50; // Max 50 scroll attempts
                    let iterations = 0;
                    
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        iterations++;
                        
                        // Check if height is stable (no new content loaded)
                        if (scrollHeight === previousHeight) {
                            stableCount++;
                        } else {
                            stableCount = 0;
                            previousHeight = scrollHeight;
                        }
                        
                        // Stop if: reached bottom, height stable for 3 cycles, or max iterations
                        if (totalHeight >= scrollHeight || stableCount >= 3 || iterations >= maxIterations) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 200);
                });
            }
        """)
        
        await page.wait_for_timeout(2000)  # Wait for any lazy-loaded content
        
        # Look for external ATS links (Greenhouse, Lever, etc.) - these are actual job postings
        external_links = await page.query_selector_all('a[href*="greenhouse"], a[href*="lever"], a[href*="ashby"], a[href*="workday"], a[href*="smartrecruiters"], a[href*="workable"]')
        
        for link in external_links:
            try:
                url = await link.get_attribute('href')
                # Accept all major ATS providers
                if url and any(provider in url.lower() for provider in ['greenhouse', 'lever', 'ashby', 'workday', 'smartrecruiters', 'workable']):
                    # Don't extract company from listing page (it's unreliable)
                    # Let the individual page extraction handle it via URL parsing
                    company_name = "Unknown Company"
                    
                    job_urls.append((url, company_name))  # Store both URL and company
                    print(f"Found external job: {url} at {company_name}")
            except Exception as e:
                print(f"Error extracting external link: {e}")
                continue
        
        # Also look for a16z internal job pages (these might be company overview pages with individual jobs)
        internal_links = await page.query_selector_all('a[href*="/jobs/"][href*="a16z.com"]')
        
        for link in internal_links:
            try:
                url = await link.get_attribute('href')
                if url and '/jobs/' in url and url not in job_urls:
                    # Make sure it's a full URL
                    if not url.startswith('http'):
                        url = 'https://jobs.a16z.com' + url
                    
                    job_urls.append((url, "Unknown Company"))
                    print(f"Found internal job page: {url}")
            except Exception as e:
                print(f"Error extracting internal link: {e}")
                continue
                
    except Exception as e:
        print(f"Error collecting job URLs: {e}")
    finally:
        await page.close()
    
    # Remove duplicates by URL while preserving company names
    seen_urls = set()
    unique_jobs = []
    for url, company in job_urls:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append((url, company))
    
    print(f"Collected {len(unique_jobs)} unique job URLs")
    return unique_jobs

async def wait_for_provider_elements(page, job_url):
    """Wait for provider-specific elements to load"""
    try:
        if 'greenhouse' in job_url.lower():
            await page.wait_for_selector('h1.app-title, #content, h1', timeout=5000)
        elif 'lever' in job_url.lower():
            await page.wait_for_selector('.posting-headline, .posting-content', timeout=5000)
        elif 'ashby' in job_url.lower():
            await page.wait_for_selector('h1, .job-description', timeout=5000)
        elif 'workday' in job_url.lower():
            await page.wait_for_selector('[data-automation-id="jobPostingHeader"], h1', timeout=5000)
        elif 'smartrecruiters' in job_url.lower():
            await page.wait_for_selector('h1, .job-title', timeout=5000)
        elif 'workable' in job_url.lower():
            await page.wait_for_selector('h1, .job-title', timeout=5000)
        # For internal pages, wait for any heading
        else:
            await page.wait_for_selector('h1, h2', timeout=5000)
    except Exception as e:
        print(f"Timeout waiting for elements on {job_url}: {e}")

async def extract_job_details_advanced(page, job_url, company_name):
    """Extract job details with provider-specific parsing"""
    job_data = {
        'url': job_url,
        'company': company_name
    }
    
    try:
        # For known ATS providers, immediately override with URL-derived company
        if any(p in job_url.lower() for p in ["greenhouse", "lever", "ashby", "workday", "smartrecruiters", "workable"]):
            job_data['company'] = extract_company_from_url(job_url)
        
        # Determine ATS provider and use appropriate selectors
        if 'greenhouse' in job_url.lower():
            job_data = await extract_greenhouse_job(page, job_data)
        elif 'lever' in job_url.lower():
            job_data = await extract_lever_job(page, job_data)
        elif 'ashby' in job_url.lower():
            job_data = await extract_ashby_job(page, job_data)
        elif 'workday' in job_url.lower():
            job_data = await extract_workday_job(page, job_data)
        else:
            # Fall back to generic extraction for a16z internal pages
            job_data = await extract_generic_job(page, job_data)
            
    except Exception as e:
        print(f"Error extracting job details from {job_url}: {e}")
    
    return job_data

async def extract_greenhouse_job(page, job_data):
    """Extract job details from Greenhouse ATS"""
    try:
        # Title
        title_selectors = ['h1.app-title', '.job-title', 'h1']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company (override if found on page, or extract from URL)
        company_selectors = ['.company-name', '.header-company-name', '[data-mapped="company"]']
        company = await get_text_by_selectors(page, company_selectors)
        if company:
            job_data['company'] = company
        elif not job_data.get('company') or job_data.get('company') == "Unknown Company":
            # Try to extract company from URL as fallback
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location
        location_selectors = ['.location', '[data-mapped="location"]', '.job-location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Employment type
        type_selectors = ['.employment-type', '[data-mapped="employment_type"]']
        emp_type = await get_text_by_selectors(page, type_selectors)
        if emp_type:
            job_data['employment_type'] = emp_type
        
        # Description
        desc_selectors = ['#content', '.section-wrapper', '.job-description']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['description'] = description[:5000]  # Limit length
        
        # Posted date
        date_selectors = ['.posted-date', '.publication-date']
        posted_date = await get_text_by_selectors(page, date_selectors)
        if posted_date:
            job_data['posted_date'] = posted_date
            
    except Exception as e:
        print(f"Error parsing Greenhouse job: {e}")
    
    return job_data

async def extract_lever_job(page, job_data):
    """Extract job details from Lever ATS"""
    try:
        # Title
        title_selectors = ['.posting-headline h2', '.job-title', 'h2']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company (extract from URL if not found on page)
        if not job_data.get('company') or job_data.get('company') == "Unknown Company":
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location
        location_selectors = ['.posting-categories .location', '.location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Employment type
        type_selectors = ['.posting-categories .commitment', '.employment-type']
        emp_type = await get_text_by_selectors(page, type_selectors)
        if emp_type:
            job_data['employment_type'] = emp_type
        
        # Description
        desc_selectors = ['.posting-content', '.section-wrapper']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['description'] = description[:5000]
            
    except Exception as e:
        print(f"Error parsing Lever job: {e}")
    
    return job_data

async def extract_ashby_job(page, job_data):
    """Extract job details from Ashby ATS"""
    try:
        # Title
        title_selectors = ['h1', '.job-title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company (extract from URL if not found on page)
        if not job_data.get('company') or job_data.get('company') == "Unknown Company":
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location and other details are often in a details section
        location_selectors = ['.location-text', '.job-details-location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Description
        desc_selectors = ['.job-description', '.markdown-content']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['description'] = description[:5000]
            
    except Exception as e:
        print(f"Error parsing Ashby job: {e}")
    
    return job_data

async def extract_workday_job(page, job_data):
    """Extract job details from Workday ATS"""
    try:
        # Title
        title_selectors = ['h1[data-automation-id="jobPostingHeader"]', 'h1', '.job-title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company (extract from URL if not found on page)
        if not job_data.get('company') or job_data.get('company') == "Unknown Company":
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location
        location_selectors = ['[data-automation-id="jobPostingLocation"]', '.location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Description
        desc_selectors = ['[data-automation-id="jobPostingDescription"]', '.job-description']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['description'] = description[:5000]
            
    except Exception as e:
        print(f"Error parsing Workday job: {e}")
    
    return job_data

async def extract_generic_job(page, job_data):
    """Generic extraction for a16z internal pages and unknown providers"""
    try:
        # Title
        title_selectors = ['h1', '.job-title', '.title', 'h2']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Location
        location_selectors = ['.location', '.job-location', '[class*="location"]']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Description
        desc_selectors = ['.description', '.job-description', 'main', '.content']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['description'] = description[:5000]
            
    except Exception as e:
        print(f"Error parsing generic job: {e}")
    
    return job_data

async def get_text_by_selectors(page, selectors):
    """Try multiple selectors and return the first successful text extraction"""
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return None

def extract_company_from_greenhouse_url(url):
    """Extract company name from Greenhouse URL"""
    try:
        if 'greenhouse' in url.lower():
            # Format: https://job-boards.greenhouse.io/COMPANY/jobs/...
            # or https://boards.greenhouse.io/COMPANY/jobs/...
            parts = url.split('/')
            for i, part in enumerate(parts):
                if 'greenhouse' in part and i + 1 < len(parts):
                    company_slug = parts[i + 1]
                    # Clean up company slug to readable name
                    company_name = company_slug.replace('-', ' ').replace('_', ' ')
                    return company_name.title()
    except Exception:
        pass
    return "Unknown Company"

def extract_company_from_url(url):
    """Extract company name from various ATS URLs"""
    try:
        if 'greenhouse' in url.lower():
            return extract_company_from_greenhouse_url(url)
        elif 'lever' in url.lower():
            # Format: https://jobs.lever.co/COMPANY/job-id
            parts = url.split('/')
            for i, part in enumerate(parts):
                if 'lever.co' in part and i + 1 < len(parts):
                    company_slug = parts[i + 1]
                    return company_slug.replace('-', ' ').replace('_', ' ').title()
        elif 'ashby' in url.lower():
            # Format: https://jobs.ashbyhq.com/COMPANY/job-id
            parts = url.split('/')
            for i, part in enumerate(parts):
                if 'ashbyhq.com' in part and i + 1 < len(parts):
                    company_slug = parts[i + 1]
                    return company_slug.replace('-', ' ').replace('_', ' ').title()
        elif 'workday' in url.lower():
            # Format: https://COMPANY.wd12.myworkdayjobs.com/...
            if '.wd' in url and '.myworkdayjobs.com' in url:
                domain_part = url.split('//')[1].split('.')[0]
                return domain_part.replace('-', ' ').replace('_', ' ').title()
    except Exception:
        pass
    return "Unknown Company"

def save_job_to_db(job_data):
    """Save job data to the database"""
    try:
        # Check if job already exists by URL to avoid duplicates
        existing_job = Job.query.filter_by(url=job_data.get('url')).first()
        if existing_job:
            print(f"Job already exists: {job_data.get('title', 'Unknown Title')}")
            return
        
        # Only save if we have a title (minimum requirement)
        if not job_data.get('title'):
            print("Skipping job - no title found")
            return
        
        # Create new job record - don't default company to 'a16z'
        job = Job(
            title=job_data.get('title'),
            company=job_data.get('company'),  # Let it be None if not found
            location=job_data.get('location'),
            employment_type=job_data.get('employment_type'),
            description=job_data.get('description'),
            url=job_data.get('url'),
            posted_date=job_data.get('posted_date'),
            scraped_at=datetime.utcnow()
        )
        
        db.session.add(job)
        db.session.commit()
        
    except Exception as e:
        print(f"Error saving job to database: {e}")
        db.session.rollback()

if __name__ == "__main__":
    print("Starting a16z jobs scraper...")
    asyncio.run(scrape_a16z_jobs())
