import asyncio
import os
import re
from playwright.async_api import async_playwright
from flask import Flask
from models import db, Job
from datetime import datetime

def parse_salary_range(salary_text):
    """Parse salary text and extract clean numeric range"""
    if not salary_text or salary_text == "Not provided" or salary_text.strip() == "":
        return "Not provided"
    
    # Remove common prefixes and suffixes
    clean_text = salary_text.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        r'^US Salary Range\s*',
        r'^Salary Range\s*',
        r'^Compensation\s*',
        r'^Pay Range\s*',
        r'^Base Salary\s*',
        r'^Annual Salary\s*',
        r'^Salary\s*',
    ]
    
    for prefix in prefixes_to_remove:
        clean_text = re.sub(prefix, '', clean_text, flags=re.IGNORECASE)
    
    # Remove common suffixes
    suffixes_to_remove = [
        r'\s*USD$',
        r'\s*per year$',
        r'\s*annually$',
        r'\s*per annum$',
        r'\s*base salary$',
    ]
    
    for suffix in suffixes_to_remove:
        clean_text = re.sub(suffix, '', clean_text, flags=re.IGNORECASE)
    
    # Extract salary range patterns
    patterns = [
        # $100,000 - $200,000
        r'\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)',
        # $100K - $200K
        r'\$?([\d,]+)K\s*[-–—]\s*\$?([\d,]+)K',
        # 100000 - 200000
        r'([\d,]+)\s*[-–—]\s*([\d,]+)',
        # $100,000 to $200,000
        r'\$?([\d,]+)\s+to\s+\$?([\d,]+)',
        # $100K to $200K
        r'\$?([\d,]+)K\s+to\s+\$?([\d,]+)K',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            min_salary = match.group(1).replace(',', '')
            max_salary = match.group(2).replace(',', '')
            
            # Handle K notation
            if 'K' in match.group(0).upper():
                min_salary = str(int(min_salary) * 1000)
                max_salary = str(int(max_salary) * 1000)
            
            return f"{min_salary} - {max_salary}"
    
    # Extract single salary
    single_patterns = [
        r'\$?([\d,]+)K',
        r'\$?([\d,]+)',
    ]
    
    for pattern in single_patterns:
        match = re.search(pattern, clean_text)
        if match:
            salary = match.group(1).replace(',', '')
            if 'K' in match.group(0).upper():
                salary = str(int(salary) * 1000)
            return salary
    
    # If no pattern matches, return original text
    return salary_text

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
    """Scrape job listings from a16z jobs website by company"""
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Import global status tracking
        from app import scraping_status
        
        # Ensure we have the latest status
        print(f"Initial scraping status: {scraping_status}")
        
        # Force the status to be running since we're in the scraper thread
        scraping_status['is_running'] = True
        print(f"Set status to running: {scraping_status}")
        
        async with async_playwright() as p:
            # Launch browser in headless mode for efficiency
            browser = await p.chromium.launch(headless=True)
            
            try:
                # Step 1: Get list of all companies from /companies page
                scraping_status['message'] = 'Fetching company list...'
                companies = await get_company_list(browser)
                scraping_status['total_companies'] = len(companies)
                scraping_status['completed_companies'] = 0
                print(f"Found {len(companies)} companies to scrape")
                
                if not companies:
                    scraping_status['message'] = 'No companies found! Check the website structure.'
                    print("❌ No companies found - this indicates a problem with the company discovery")
                    return
                
                # Step 2: Process each company individually
                total_jobs_scraped = 0
                for i, company_info in enumerate(companies):
                    # Check if scraping should stop
                    print(f"Checking status before company {i+1}: is_running={scraping_status['is_running']}")
                    if not scraping_status['is_running']:
                        print("🛑 Scraping stopped by user request")
                        break
                    
                    company_name = company_info['name']
                    company_url = company_info['url']
                    
                    # Update status
                    scraping_status['current_company'] = company_name
                    scraping_status['message'] = f'Processing {company_name} ({i+1}/{len(companies)})'
                    
                    print(f"\n🏢 Processing company {i+1}/{len(companies)}: {company_name}")
                    print(f"Company URL: {company_url}")
                    
                    try:
                        # Get jobs for this specific company
                        company_jobs = await collect_company_jobs(browser, company_name, company_url)
                        print(f"Found {len(company_jobs)} jobs for {company_name}")
                        
                        # Process each job for this company
                        for j, (job_url, job_company) in enumerate(company_jobs):
                            # Check if scraping should stop
                            if not scraping_status['is_running']:
                                print("🛑 Scraping stopped by user request")
                                break
                                
                            try:
                                print(f"  📋 Processing job {j+1}/{len(company_jobs)}: {job_url}")
                                
                                # Create a fresh page for each job
                                page = await browser.new_page()
                                
                                try:
                                    await page.goto(job_url, timeout=30000)
                                    await page.wait_for_load_state('networkidle', timeout=10000)
                                    
                                    # Wait for provider-specific elements to load
                                    await wait_for_provider_elements(page, job_url)
                                    
                                    # Extract job information with company context
                                    job_data = await extract_job_details_advanced(page, job_url, company_name)
                                    
                                    # Skip if job was filtered out (e.g., Workday jobs)
                                    if job_data is None:
                                        print(f"  ⏭️  Skipped: {job_url}")
                                        continue
                                    
                                    # Ensure company name is set correctly
                                    job_data['company'] = company_name
                                    
                                    # Save to database
                                    save_job_to_db(job_data)
                                    
                                    print(f"  ✅ Saved: {job_data.get('title', 'Unknown Title')} at {company_name}")
                                    total_jobs_scraped += 1
                                    
                                except Exception as e:
                                    print(f"  ❌ Error processing job {j+1}: {e}")
                                    continue
                                finally:
                                    await page.close()
                                
                            except Exception as e:
                                print(f"  ❌ Error with job {j+1}: {e}")
                                continue
                        
                        # Update completed companies count
                        scraping_status['completed_companies'] = i + 1
                        print(f"✅ Completed {company_name}: {len(company_jobs)} jobs processed")
                        
                    except Exception as e:
                        print(f"❌ Error processing company {company_name}: {e}")
                        continue
                
                if scraping_status['is_running']:
                    scraping_status['message'] = f'Scraping completed! Total jobs: {total_jobs_scraped}'
                    print(f"\n🎉 Scraping completed! Total jobs scraped: {total_jobs_scraped}")
                else:
                    print(f"\n🛑 Scraping stopped. Jobs scraped: {total_jobs_scraped}")
                
            except Exception as e:
                scraping_status['message'] = f'Error during scraping: {e}'
                print(f"Error during scraping: {e}")
            finally:
                await browser.close()
                
        print("Scraping completed!")

async def get_company_list(browser):
    """Get list of all companies from the a16z companies page with infinite scroll handling"""
    page = await browser.new_page()
    companies = []
    
    try:
        print("🔍 Fetching company list from /companies page...")
        await page.goto('https://jobs.a16z.com/companies', timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Wait for initial page to load completely
        await page.wait_for_timeout(3000)
        
        print("🔄 Starting infinite scroll to load all companies...")
        
        # Track unique company URLs to detect when no more companies are loading
        seen_company_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 50  # Prevent infinite loop
        no_new_companies_count = 0
        max_no_new_companies = 3  # Stop if no new companies found after 3 consecutive scrolls
        
        while scroll_attempts < max_scroll_attempts and no_new_companies_count < max_no_new_companies:
            # Get current company data and extract unique URLs
            current_company_data = await page.eval_on_selector_all(
                'a[href*="/jobs/"]',
                'els => els.map(a => ({ href: a.getAttribute("href"), text: a.innerText.trim() }))'
            )
            
            # Count unique company URLs (not total links)
            current_unique_urls = set()
            for link in current_company_data:
                if link['href'] and link['href'] not in ['/jobs', '/']:
                    # Normalize URL for comparison
                    if link['href'].startswith('/'):
                        normalized_url = 'https://jobs.a16z.com' + link['href']
                    else:
                        normalized_url = link['href']
                    current_unique_urls.add(normalized_url)
            
            # Count how many new unique URLs we found
            new_urls = current_unique_urls - seen_company_urls
            new_count = len(new_urls)
            total_unique_count = len(current_unique_urls)
            
            print(f"  📊 Scroll attempt {scroll_attempts + 1}: Found {total_unique_count} unique companies ({new_count} new)")
            
            # Update our seen URLs
            seen_company_urls.update(current_unique_urls)
            
            # Check if we got new unique companies
            if new_count > 0:
                print(f"  ✅ Found {new_count} new unique companies, continuing scroll...")
                no_new_companies_count = 0
            else:
                no_new_companies_count += 1
                print(f"  ⏳ No new unique companies found ({no_new_companies_count}/{max_no_new_companies})")
            
            # Scroll down to load more content
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait for new content to load
            await page.wait_for_timeout(2000)
            
            # Wait for network to be idle (new content loaded)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                # If networkidle times out, continue anyway
                pass
            
            scroll_attempts += 1
        
        if scroll_attempts >= max_scroll_attempts:
            print(f"⚠️ Reached maximum scroll attempts ({max_scroll_attempts}), stopping")
        elif no_new_companies_count >= max_no_new_companies:
            print(f"✅ No new companies found after {max_no_new_companies} consecutive scrolls, stopping")
        
        print(f"🎯 Final scroll completed. Extracting company data...")
        
        # Now extract all company information after scrolling
        company_data = await page.eval_on_selector_all(
            'a[href*="/jobs/"]',
            'els => els.map(a => ({ href: a.getAttribute("href"), text: a.innerText.trim() }))'
        )
        
        print(f"📋 Found {len(company_data)} total company links after infinite scroll")
        
        # Process company links and extract names from URLs
        seen_urls = set()
        for link in company_data:
            if link['href'] and link['href'] not in ['/jobs', '/']:
                # Skip if we've already processed this URL
                if link['href'] in seen_urls:
                    continue
                seen_urls.add(link['href'])
                
                # Normalize URL
                if link['href'].startswith('/'):
                    company_url = 'https://jobs.a16z.com' + link['href']
                else:
                    company_url = link['href']
                
                # Extract company name from URL
                # Format: /jobs/whatnot -> Whatnot
                url_parts = link['href'].split('/')
                if 'jobs' in url_parts:
                    job_index = url_parts.index('jobs')
                    if job_index + 1 < len(url_parts):
                        company_slug = url_parts[job_index + 1].split('?')[0]  # Remove query params
                        company_name = company_slug.replace('-', ' ').replace('_', ' ')
                        # Capitalize each word
                        company_name = ' '.join(word.capitalize() for word in company_name.split())
                        
                        companies.append({
                            'name': company_name,
                            'url': company_url
                        })
                        print(f"  📋 Added company: {company_name}")
        
        # Remove duplicates by name
        seen_names = set()
        unique_companies = []
        for company in companies:
            if company['name'] not in seen_names:
                seen_names.add(company['name'])
                unique_companies.append(company)
        
        print(f"✅ Collected {len(unique_companies)} unique companies after infinite scroll")
        return unique_companies
        
    except Exception as e:
        print(f"Error collecting company list: {e}")
        return []
    finally:
        await page.close()

async def collect_company_jobs(browser, company_name, company_url):
    """Collect job URLs for a specific company with infinite scroll support"""
    page = await browser.new_page()
    job_urls = []
    
    try:
        print(f"  🔍 Collecting jobs for {company_name}...")
        await page.goto(company_url, timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Wait for job listings to load
        await page.wait_for_timeout(3000)
        
        print(f"  🔄 Starting infinite scroll to load all jobs for {company_name}...")
        
        # Track unique job URLs to detect when no more jobs are loading
        seen_job_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 100  # Higher limit for companies with massive job boards (like Anduril)
        no_new_jobs_count = 0
        max_no_new_jobs = 3  # Stop if no new jobs found after 3 consecutive scrolls
        
        while scroll_attempts < max_scroll_attempts and no_new_jobs_count < max_no_new_jobs:
            # Get current job data and extract unique URLs
            current_job_data = await page.eval_on_selector_all(
                'a',
                '''
                els => els.map(a => {
                    const href = a.getAttribute("href");
                    const text = a.innerText.trim();
                    
                    // Look for job-related links with more comprehensive patterns
                    if (href && (
                        href.includes('greenhouse') ||
                        href.includes('lever') ||
                        href.includes('ashby') ||
                        href.includes('workday') ||
                        href.includes('smartrecruiters') ||
                        href.includes('workable') ||
                        href.includes('stripe.com/jobs') ||
                        href.includes('/jobs/') ||
                        href.includes('/job/') ||
                        href.includes('careers') ||
                        href.includes('apply') ||
                        text.includes('View') && text.includes('jobs') ||
                        text.includes('Apply') ||
                        text.includes('Learn more') ||
                        text.includes('View Job') ||
                        text.includes('View Role') ||
                        text.includes('Open Position')
                    )) {
                        return href;
                    }
                    return null;
                }).filter(href => href)
                '''
            )
            
            # Count unique job URLs (not total links)
            current_unique_urls = set()
            for url in current_job_data:
                if url:
                    # Normalize URL for comparison
                    if url.startswith('/'):
                        normalized_url = 'https://jobs.a16z.com' + url
                    else:
                        normalized_url = url
                    current_unique_urls.add(normalized_url)
            
            # Count how many new unique URLs we found
            new_urls = current_unique_urls - seen_job_urls
            new_count = len(new_urls)
            total_unique_count = len(current_unique_urls)
            
            print(f"    📊 Scroll attempt {scroll_attempts + 1}: Found {total_unique_count} unique jobs ({new_count} new)")
            
            # Update our seen URLs
            seen_job_urls.update(current_unique_urls)
            
            # Check if we got new unique jobs
            if new_count > 0:
                print(f"    ✅ Found {new_count} new unique jobs, continuing scroll...")
                no_new_jobs_count = 0
            else:
                no_new_jobs_count += 1
                print(f"    ⏳ No new unique jobs found ({no_new_jobs_count}/{max_no_new_jobs})")
            
            # Scroll down to load more content
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait for new content to load
            await page.wait_for_timeout(2000)
            
            # Wait for network to be idle (new content loaded)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                # If networkidle times out, continue anyway
                pass
            
            # Try to detect and click "Load More" or "Show More" buttons if they exist
            try:
                load_more_selectors = [
                    'button:has-text("Load More")',
                    'button:has-text("Show More")',
                    'button:has-text("View More")',
                    '.load-more',
                    '.show-more',
                    '[data-testid="load-more"]'
                ]
                
                for selector in load_more_selectors:
                    try:
                        load_more_button = await page.query_selector(selector)
                        if load_more_button:
                            await load_more_button.click()
                            print(f"    🔄 Clicked load more button: {selector}")
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            except:
                pass
            
            scroll_attempts += 1
        
        if scroll_attempts >= max_scroll_attempts:
            print(f"    ⚠️ Reached maximum scroll attempts ({max_scroll_attempts}) for {company_name}")
        elif no_new_jobs_count >= max_no_new_jobs:
            print(f"    ✅ No new jobs found after {max_no_new_jobs} consecutive scrolls for {company_name}")
        
        print(f"  🎯 Final scroll completed for {company_name}. Extracting job data...")
        
        # Now extract all job information after scrolling
        job_links = await page.eval_on_selector_all(
            'a',
            '''
            els => els.map(a => {
                const href = a.getAttribute("href");
                const text = a.innerText.trim();
                
                // Look for job-related links with more comprehensive patterns
                if (href && (
                    href.includes('greenhouse') ||
                    href.includes('lever') ||
                    href.includes('ashby') ||
                    href.includes('workday') ||
                    href.includes('smartrecruiters') ||
                    href.includes('workable') ||
                    href.includes('stripe.com/jobs') ||
                    href.includes('/jobs/') ||
                    href.includes('/job/') ||
                    href.includes('careers') ||
                    href.includes('apply') ||
                    text.includes('View') && text.includes('jobs') ||
                    text.includes('Apply') ||
                    text.includes('Learn more') ||
                    text.includes('View Job') ||
                    text.includes('View Role') ||
                    text.includes('Open Position')
                )) {
                    return href;
                }
                return null;
            }).filter(href => href)
            '''
        )
        
        print(f"  📋 Found {len(job_links)} total job links after infinite scroll for {company_name}")
        
        for url in job_links:
            if not url:
                continue
                
            # Normalize relative URLs
            if url.startswith('/'):
                url = 'https://jobs.a16z.com' + url
            
            # Accept all major ATS providers and internal job pages
            if (any(provider in url.lower() for provider in ['greenhouse', 'lever', 'ashby', 'workday', 'smartrecruiters', 'workable']) or 
                'stripe.com/jobs' in url.lower() or '/jobs/' in url or '/job/' in url or 'careers' in url.lower() or 'apply' in url.lower()):
                job_urls.append((url, company_name))
                print(f"    ✅ Found job: {url}")
        
        # If no jobs found with the above method, try a more generic approach
        if not job_urls:
            print(f"  🔄 No jobs found with primary method, trying alternative...")
            
            # Look for any links that might be jobs
            all_links = await page.eval_on_selector_all(
                'a',
                'els => els.map(a => a.getAttribute("href"))'
            )
            
            for url in all_links:
                if not url:
                    continue
                    
                # Normalize relative URLs
                if url.startswith('/'):
                    url = 'https://jobs.a16z.com' + url
                
                # Check if this looks like a job URL
                if (any(provider in url.lower() for provider in ['greenhouse', 'lever', 'ashby', 'workday', 'smartrecruiters', 'workable']) or 
                    'stripe.com/jobs' in url.lower() or '/jobs/' in url or '/job/' in url or 'careers' in url.lower() or 'apply' in url.lower() or
                    'jobs' in url.lower()):
                    job_urls.append((url, company_name))
                    print(f"    ✅ Found job (alt method): {url}")
        
        # Remove duplicates
        seen_urls = set()
        unique_jobs = []
        for url, company in job_urls:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append((url, company))
        
        print(f"  🎯 {company_name}: {len(unique_jobs)} unique jobs found after infinite scroll")
        return unique_jobs
        
    except Exception as e:
        print(f"  ❌ Error collecting jobs for {company_name}: {e}")
        return []
    finally:
        await page.close()


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
        elif 'stripe.com' in job_url.lower():
            await page.wait_for_selector('h1, main, .job-title', timeout=5000)
        # For internal pages, wait for any heading
        else:
            await page.wait_for_selector('h1, h2', timeout=5000)
    except Exception as e:
        print(f"Timeout waiting for elements on {job_url}: {e}")

async def extract_job_details_advanced(page, job_url, company_name):
    """Extract job details with provider-specific parsing"""
    job_data = {
        'url': job_url,
        'company': company_name,
        'source': extract_source_from_url(job_url)
    }
    
    try:
        # For known ATS providers, immediately override with URL-derived company
        if any(p in job_url.lower() for p in ["greenhouse", "lever", "ashby", "smartrecruiters", "workable"]):
            job_data['company'] = extract_company_from_url(job_url)
        
        # Check if this is a Workday job - skip if so
        if 'workday' in job_url.lower():
            print(f"Skipping Workday job (non-US company): {job_url}")
            return None
        
        # Determine ATS provider and use appropriate selectors
        if 'greenhouse' in job_url.lower():
            job_data = await extract_greenhouse_job(page, job_data)
        elif 'lever' in job_url.lower():
            job_data = await extract_lever_job(page, job_data)
        elif 'ashby' in job_url.lower():
            job_data = await extract_ashby_job(page, job_data)
        elif 'stripe.com' in job_url.lower():
            job_data = await extract_stripe_job(page, job_data)
        elif 'databricks.com' in job_url.lower():
            job_data = await extract_databricks_job(page, job_data)
        elif 'withwaymo.com' in job_url.lower():
            job_data = await extract_waymo_job(page, job_data)
        elif 'navan.com' in job_url.lower():
            job_data = await extract_navan_job(page, job_data)
        elif 'wiz.io' in job_url.lower():
            job_data = await extract_wiz_job(page, job_data)
        elif 'fivetran.com' in job_url.lower():
            job_data = await extract_fivetran_job(page, job_data)
        else:
            # Fall back to generic extraction for a16z internal pages
            job_data = await extract_generic_job(page, job_data)
            
    except Exception as e:
        print(f"Error extracting job details from {job_url}: {e}")
    
    return job_data

async def extract_databricks_job(page, job_data):
    """Extract comprehensive job details from Databricks custom job board"""
    try:
        # Title - usually in h1
        title_selectors = ['h1', '.job-title', 'title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company is always Databricks
        job_data['company'] = 'Databricks'
        
        # Location - look for location text in the page content
        location = await page.evaluate('''
            () => {
                // Get all text content and look for location patterns
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for location patterns in the text
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for lines that contain location keywords and are reasonably short
                    if (line.length > 2 && line.length < 100 && 
                        !line.includes('Spear Street') && 
                        !line.includes('1-866') && 
                        !line.includes('Phone') &&
                        !line.includes('Address') &&
                        !line.includes('Apply now') &&
                        !line.includes('P-') &&
                        (line.includes('India') || 
                         line.includes('Costa Rica') || 
                         line.includes('Bengaluru') ||
                         line.includes('San Francisco') ||
                         line.includes('New York') ||
                         line.includes('Remote') ||
                         line.includes('United States') ||
                         line.includes('Canada') ||
                         line.includes('Europe') ||
                         line.includes('Asia') ||
                         line.includes('London') ||
                         line.includes('Berlin') ||
                         line.includes('Paris') ||
                         line.includes('Tokyo') ||
                         line.includes('Singapore')
                        )) {
                        return line;
                    }
                }
                
                // Fallback: look for any element containing location keywords
                const elements = document.querySelectorAll('*');
                for (let el of elements) {
                    const text = el.innerText.trim();
                    if (text && text.length > 2 && text.length < 100 && 
                        !text.includes('Spear Street') && 
                        !text.includes('1-866') && 
                        !text.includes('Phone') &&
                        !text.includes('Address') &&
                        (text.includes('India') || 
                         text.includes('Costa Rica') || 
                         text.includes('Bengaluru') ||
                         text.includes('San Francisco') ||
                         text.includes('New York') ||
                         text.includes('Remote') ||
                         text.includes('United States') ||
                         text.includes('Canada') ||
                         text.includes('Europe') ||
                         text.includes('Asia') ||
                         text.includes('London') ||
                         text.includes('Berlin') ||
                         text.includes('Paris') ||
                         text.includes('Tokyo') ||
                         text.includes('Singapore')
                        )) {
                        return text;
                    }
                }
                return null;
            }
        ''')
        
        if location:
            job_data['location'] = location
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                # Extract job ID from URL (usually the last part before query params)
                job_id = url_parts[-1].split('?')[0]
                if job_id and job_id != 'careers':
                    job_data['job_id'] = job_id
        except:
            pass
        
        # Extract detailed content
        content_selectors = ['main', '.job-description', '.content', 'article']
        full_content = ""
        
        for selector in content_selectors:
            try:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 500:  # Only use substantial content
                        full_content = text.strip()
                        break
            except:
                continue
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Databricks: Extracted {len(full_content)} characters of content")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Databricks: Parsed sections: {list(sections.keys())}")
        else:
            print("Databricks: No substantial content found")
        
        # Salary - Databricks typically doesn't include salary information
        # Set to standard message when no salary is provided
        job_data['salary_range'] = "Not provided"
        
    except Exception as e:
        print(f"Error parsing Databricks job: {e}")
    
    return job_data

async def extract_waymo_job(page, job_data):
    """Extract comprehensive job details from Waymo custom job board"""
    try:
        # Title - extract from page title or specific selectors
        title = await page.evaluate('''
            () => {
                // Try to get the actual job title from the page title
                const pageTitle = document.title;
                if (pageTitle && pageTitle.includes(' - ')) {
                    // Extract title before the location part
                    const parts = pageTitle.split(' - ');
                    if (parts.length > 1) {
                        return parts[0].trim();
                    }
                }
                
                // Fallback: look for h1 or other title elements
                const h1 = document.querySelector('h1');
                if (h1 && h1.innerText && !h1.innerText.includes('Working at')) {
                    return h1.innerText.trim();
                }
                
                return pageTitle;
            }
        ''')
        
        if title:
            job_data['title'] = title
        
        # Company is always Waymo
        job_data['company'] = 'Waymo'
        
        # Location - extract from page content
        location = await page.evaluate('''
            () => {
                // Look for location in the page content
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for location patterns - prioritize shorter, cleaner matches
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for lines that contain location keywords and are reasonably short
                    if (line.length > 2 && line.length < 100 && 
                        (line.includes('Washington') || 
                         line.includes('District of Columbia') ||
                         line.includes('United States') ||
                         line.includes('California') ||
                         line.includes('Mountain View') ||
                         line.includes('San Francisco') ||
                         line.includes('Remote') ||
                         line.includes('New York') ||
                         line.includes('Austin') ||
                         line.includes('Phoenix') ||
                         line.includes('Pittsburgh')
                        )) {
                        // Clean up the location text
                        let cleanLocation = line;
                        
                        // Remove common prefixes/suffixes and clean up
                        cleanLocation = cleanLocation.replace(/^.*?WASHINGTON,?\s*/i, 'Washington, ');
                        cleanLocation = cleanLocation.replace(/^.*?DISTRICT OF COLUMBIA,?\s*/i, 'District of Columbia, ');
                        cleanLocation = cleanLocation.replace(/^.*?UNITED STATES,?\s*/i, 'United States');
                        cleanLocation = cleanLocation.replace(/FULL-TIME.*$/i, '').trim();
                        cleanLocation = cleanLocation.replace(/POLICY.*$/i, '').trim();
                        cleanLocation = cleanLocation.replace(/\\d+.*$/i, '').trim();
                        cleanLocation = cleanLocation.replace(/Apply now.*$/i, '').trim();
                        cleanLocation = cleanLocation.replace(/\\s+\\d+\\s*$/i, '').trim(); // Remove trailing numbers
                        
                        // If it's still too long, try to extract just the location part
                        if (cleanLocation.length > 50) {
                            const locationMatch = cleanLocation.match(/(Washington[^,]*,\\s*District of Columbia[^,]*,\\s*United States)/i);
                            if (locationMatch) {
                                cleanLocation = locationMatch[1];
                            }
                        }
                        
                        if (cleanLocation.length > 2 && cleanLocation.length < 100) {
                            return cleanLocation;
                        }
                    }
                }
                
                // Fallback: look for specific location patterns in the text
                const locationPatterns = [
                    /Washington[^,]*,\\s*District of Columbia[^,]*,\\s*United States/i,
                    /Mountain View[^,]*,\\s*California[^,]*,\\s*United States/i,
                    /San Francisco[^,]*,\\s*California[^,]*,\\s*United States/i
                ];
                
                for (let pattern of locationPatterns) {
                    const match = bodyText.match(pattern);
                    if (match) {
                        return match[0];
                    }
                }
                
                return null;
            }
        ''')
        
        if location:
            job_data['location'] = location
        
        # Employment type - extract from page content
        employment_type = await page.evaluate('''
            () => {
                const bodyText = document.body.innerText;
                if (bodyText.includes('Full-Time') || bodyText.includes('Full Time')) {
                    return 'Full time';
                } else if (bodyText.includes('Part-Time') || bodyText.includes('Part Time')) {
                    return 'Part time';
                } else if (bodyText.includes('Contract')) {
                    return 'Contract';
                }
                return 'Full time'; // Default
            }
        ''')
        job_data['employment_type'] = employment_type
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                job_id = url_parts[-1].split('?')[0]
                if job_id and job_id != 'jobs':
                    job_data['job_id'] = job_id
        except:
            pass
        
        # Extract detailed content
        content_selectors = ['main', '.job-description', '.content', 'article', '.page-row']
        full_content = ""
        
        for selector in content_selectors:
            try:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 500:  # Only use substantial content
                        full_content = text.strip()
                        break
            except:
                continue
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Waymo: Extracted {len(full_content)} characters of content")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Waymo: Parsed sections: {list(sections.keys())}")
        else:
            print("Waymo: No substantial content found")
        
        # Salary extraction - Waymo includes salary information
        salary = await page.evaluate('''
            () => {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for salary patterns
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for salary range patterns
                    if (line.includes('$') && (
                        line.includes('—') || 
                        line.includes('-') || 
                        line.includes('to') ||
                        line.includes('USD') ||
                        line.includes('salary')
                    )) {
                        return line;
                    }
                }
                
                // Look for specific salary patterns
                const salaryPatterns = [
                    /\\$[\\d,]+[—\\-]\\$[\\d,]+/g,
                    /\\$[\\d,]+\\s+to\\s+\\$[\\d,]+/g,
                    /\\$[\\d,]+\\s*[—\\-]\\s*\\$[\\d,]+/g
                ];
                
                for (let pattern of salaryPatterns) {
                    const matches = bodyText.match(pattern);
                    if (matches && matches.length > 0) {
                        return matches[0];
                    }
                }
                
                return null;
            }
        ''')
        
        if salary:
            # Parse and clean the salary text
            job_data['salary_range'] = parse_salary_range(salary)
            print(f"Waymo: Found salary: {salary}")
        else:
            job_data['salary_range'] = "Not provided"
            print("Waymo: No salary information found")
        
    except Exception as e:
        print(f"Error parsing Waymo job: {e}")
    
    return job_data

async def extract_navan_job(page, job_data):
    """Extract comprehensive job details from Navan custom job board"""
    try:
        # Title - usually in h1
        title_selectors = ['h1', '.job-title', 'title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company is always Navan
        job_data['company'] = 'Navan'
        
        # Location - extract from page content
        location = await page.evaluate('''
            () => {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for location patterns
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for lines that contain location keywords
                    if (line.includes('Location:') || 
                        (line.includes('Austin') && line.includes('TX')) ||
                        (line.includes('San Francisco') && line.includes('CA')) ||
                        (line.includes('New York') && line.includes('NY')) ||
                        (line.includes('Remote')) ||
                        (line.includes('United States'))
                    ) {
                        // Clean up the location text
                        let cleanLocation = line;
                        cleanLocation = cleanLocation.replace(/^Location:\\s*/i, '').trim();
                        cleanLocation = cleanLocation.replace(/Department:.*$/i, '').trim();
                        
                        if (cleanLocation.length > 2 && cleanLocation.length < 100) {
                            return cleanLocation;
                        }
                    }
                }
                return null;
            }
        ''')
        
        if location:
            job_data['location'] = location
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                job_id = url_parts[-1].split('?')[0]
                if job_id and job_id != 'openings':
                    job_data['job_id'] = job_id
        except:
            pass
        
        # Extract detailed content - Navan has specific structure
        full_content = await page.evaluate('''
            () => {
                // Look for the main job content area
                const contentSelectors = [
                    'main',
                    '.job-description', 
                    '.content',
                    'article',
                    '[class*="container"]',
                    '[class*="content"]'
                ];
                
                for (let selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        const text = element.innerText;
                        if (text && text.length > 500) {
                            return text;
                        }
                    }
                }
                
                // Fallback: get all text content and filter for job-related content
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                let jobContent = [];
                let inJobContent = false;
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    // Start collecting when we find job-related content
                    if (line.includes('What You\\'ll Do:') || 
                        line.includes('What We\\'re Looking For:') ||
                        line.includes('Navan sales organization') ||
                        line.includes('The ideal candidate')) {
                        inJobContent = true;
                    }
                    
                    // Stop collecting at footer/legal content
                    if (line.includes('Equal Opportunity') ||
                        line.includes('Candidate Privacy') ||
                        line.includes('Job Search Best Practices') ||
                        line.includes('© 2025 Navan')) {
                        break;
                    }
                    
                    if (inJobContent && line.length > 10) {
                        jobContent.push(line);
                    }
                }
                
                return jobContent.join('\\n');
            }
        ''')
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Navan: Extracted {len(full_content)} characters of content")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Navan: Parsed sections: {list(sections.keys())}")
        else:
            print("Navan: No substantial content found")
        
        # Salary - Navan typically doesn't include salary information
        # Set to standard message when no salary is provided
        job_data['salary_range'] = "Not provided"
        
    except Exception as e:
        print(f"Error parsing Navan job: {e}")
    
    return job_data

async def extract_wiz_job(page, job_data):
    """Extract comprehensive job details from Wiz custom job board"""
    try:
        # Title - usually in h1
        title_selectors = ['h1', '.job-title', 'title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company is always Wiz
        job_data['company'] = 'Wiz'
        
        # Location - extract from page content
        location = await page.evaluate('''
            () => {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for location patterns
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for lines that contain location keywords
                    if (line.includes('Tel Aviv') || 
                        line.includes('New York') ||
                        line.includes('San Francisco') ||
                        line.includes('Remote') ||
                        line.includes('Engineering') ||
                        line.includes('|')
                    ) {
                        // Clean up the location text
                        let cleanLocation = line;
                        // Extract location from "Tel Aviv | Engineering" format
                        if (cleanLocation.includes('|')) {
                            cleanLocation = cleanLocation.split('|')[0].trim();
                        }
                        // Remove common prefixes
                        cleanLocation = cleanLocation.replace(/^Location:\\s*/i, '').trim();
                        
                        if (cleanLocation.length > 2 && cleanLocation.length < 100) {
                            return cleanLocation;
                        }
                    }
                }
                return null;
            }
        ''')
        
        if location:
            job_data['location'] = location
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                # Extract job ID from URL like /job/4004643006/
                for part in url_parts:
                    if part.isdigit():
                        job_data['job_id'] = part
                        break
        except:
            pass
        
        # Extract detailed content
        content_selectors = ['main', '.job-description', '.content', 'article']
        full_content = ""
        
        for selector in content_selectors:
            try:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 500:  # Only use substantial content
                        full_content = text.strip()
                        break
            except:
                continue
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Wiz: Extracted {len(full_content)} characters of content")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Wiz: Parsed sections: {list(sections.keys())}")
        else:
            print("Wiz: No substantial content found")
        
        # Salary - Wiz typically doesn't include salary information
        # Set to standard message when no salary is provided
        job_data['salary_range'] = "Not provided"
        
    except Exception as e:
        print(f"Error parsing Wiz job: {e}")
    
    return job_data

async def extract_fivetran_job(page, job_data):
    """Extract comprehensive job details from Fivetran custom job board"""
    try:
        # Wait for dynamic content to load
        await page.wait_for_timeout(3000)
        
        # Title - usually in h1
        title_selectors = ['h1', '.job-title', 'title']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company is always Fivetran
        job_data['company'] = 'Fivetran'
        
        # Location - extract from page content
        location = await page.evaluate('''
            () => {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                // Look for location patterns
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Look for lines that contain location keywords
                    if (line.includes('Bengaluru') || 
                        line.includes('Karnataka') ||
                        line.includes('India') ||
                        line.includes('San Francisco') ||
                        line.includes('Denver') ||
                        line.includes('Austin') ||
                        line.includes('New York') ||
                        line.includes('Remote') ||
                        line.includes('United States')
                    ) {
                        // Clean up the location text
                        let cleanLocation = line;
                        // Remove common prefixes
                        cleanLocation = cleanLocation.replace(/^Location:\\s*/i, '').trim();
                        cleanLocation = cleanLocation.replace(/^Job Location:\\s*/i, '').trim();
                        
                        if (cleanLocation.length > 2 && cleanLocation.length < 100) {
                            return cleanLocation;
                        }
                    }
                }
                return null;
            }
        ''')
        
        if location:
            job_data['location'] = location
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('?')
            if len(url_parts) > 1:
                # Extract job ID from query parameter
                query_params = url_parts[1]
                if 'gh_jid=' in query_params:
                    job_id = query_params.split('gh_jid=')[1].split('&')[0]
                    if job_id:
                        job_data['job_id'] = job_id
        except:
            pass
        
        # Extract detailed content
        content_selectors = ['main', '.job-description', '.content', 'article', '.main']
        full_content = ""
        
        for selector in content_selectors:
            try:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 500:  # Only use substantial content
                        full_content = text.strip()
                        break
            except:
                continue
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Fivetran: Extracted {len(full_content)} characters of content")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Fivetran: Parsed sections: {list(sections.keys())}")
        else:
            print("Fivetran: No substantial content found")
        
        # Salary - Fivetran typically doesn't include salary information
        # Set to standard message when no salary is provided
        job_data['salary_range'] = "Not provided"
        
    except Exception as e:
        print(f"Error parsing Fivetran job: {e}")
    
    return job_data

async def extract_greenhouse_job(page, job_data):
    """Extract comprehensive job details from Greenhouse ATS"""
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
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location - Updated selectors for Greenhouse
        location_selectors = ['.job__location', '[class*="location"]', '.location', '[data-mapped="location"]', '.job-location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            job_data['location'] = location
        
        # Employment type
        type_selectors = ['.employment-type', '[data-mapped="employment_type"]']
        emp_type = await get_text_by_selectors(page, type_selectors)
        if emp_type:
            job_data['employment_type'] = emp_type
        
        # Job ID
        job_id = None
        try:
            url_parts = job_data['url'].split('/')
            if 'jobs' in url_parts:
                job_id_index = url_parts.index('jobs') + 1
                if job_id_index < len(url_parts):
                    job_id = url_parts[job_id_index].split('?')[0]
            job_data['job_id'] = job_id
        except:
            pass
        
        # Extract detailed content - stop at "Create a Job Alert" section
        full_content = await page.evaluate('''
            () => {
                // Look for the main job content area
                const contentSelectors = [
                    '#content',
                    '.section-wrapper',
                    '.job-description',
                    '[data-testid="jobDescription"]',
                    '[data-qa="job-description"]',
                    '.gh-content',
                    '.posting-description',
                    '.markdown-content',
                    'main',
                    'article',
                    '[role="main"]'
                ];
                
                let contentElement = null;
                for (let selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        contentElement = element;
                        break;
                    }
                }
                
                if (!contentElement) {
                    return null;
                }
                
                // Get all text content
                const fullText = contentElement.innerText;
                const lines = fullText.split('\\n');
                
                // Find the cutoff point - stop at "Create a Job Alert" or similar
                let cutoffIndex = lines.length;
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    // Stop at job alert sections
                    if (line.includes('Create a Job Alert') ||
                        line.includes('Create alert') ||
                        line.includes('Interested in building your career') ||
                        line.includes('Get future opportunities sent straight to your email') ||
                        line.includes('Apply for this job') ||
                        line.includes('indicates a required field') ||
                        line.includes('Autofill with Greenhouse') ||
                        line.includes('First Name') ||
                        line.includes('Last Name') ||
                        line.includes('Email') ||
                        line.includes('Phone') ||
                        line.includes('Resume') ||
                        line.includes('Cover Letter') ||
                        line.includes('LinkedIn Profile') ||
                        line.includes('Website') ||
                        line.includes('Portfolio') ||
                        line.includes('GitHub') ||
                        line.includes('Submit Application') ||
                        line.includes('To view') && line.includes('privacy policy') ||
                        line.includes('candidate data privacy policy') ||
                        line.includes('applicant-privacy-notice')
                    ) {
                        cutoffIndex = i;
                        break;
                    }
                }
                
                // Return only the content before the cutoff
                const relevantLines = lines.slice(0, cutoffIndex);
                return relevantLines.join('\\n').trim();
            }
        ''')
        
        if full_content:
            job_data['description'] = full_content[:10000]
            print(f"Greenhouse: Extracted {len(full_content)} characters of content (filtered)")
            
            # Parse sections from content
            sections = await parse_job_sections(full_content)
            job_data.update(sections)
            print(f"Greenhouse: Parsed sections: {list(sections.keys())}")
        else:
            print("Greenhouse: No substantial content found after filtering")
        
        
        # Posted date
        date_selectors = ['.posted-date', '.publication-date']
        posted_date = await get_text_by_selectors(page, date_selectors)
        if posted_date:
            job_data['posted_date'] = posted_date
        
        # Salary/compensation (often in content)
        salary_selectors = ['.salary', '.compensation', '.pay-range']
        salary = await get_text_by_selectors(page, salary_selectors)
        if salary:
            # Parse and clean the salary text
            job_data['salary_range'] = parse_salary_range(salary)
        else:
            # Set default message when no salary is found
            job_data['salary_range'] = "Not provided"
            
    except Exception as e:
        print(f"Error parsing Greenhouse job: {e}")
    
    return job_data

async def extract_lever_job(page, job_data):
    """Extract comprehensive job details from Lever ATS"""
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
        
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 2:
                job_data['job_id'] = url_parts[-1].split('?')[0]
        except:
            pass
        
        # Extract detailed content with comprehensive selectors
        content_selectors = [
            '.posting-content',
            '.section-wrapper',
            '.posting-description',
            '.job-description',
            '[data-testid="jobDescription"]',
            '.content',
            'main',
            'article',
            '[role="main"]'
        ]
        
        full_content = ""
        try:
            # Try multiple selectors to find content
            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 100:  # Only use substantial content
                        full_content = text.strip()
                        break
            
            if full_content:
                job_data['description'] = full_content[:10000]
                print(f"Lever: Extracted {len(full_content)} characters of content")
                
                # Parse sections from content
                sections = await parse_job_sections(full_content)
                job_data.update(sections)
                print(f"Lever: Parsed sections: {list(sections.keys())}")
            else:
                print("Lever: No substantial content found with any selector")
                
        except Exception as e:
            print(f"Lever: Error extracting content: {e}")
            # Fallback to basic description
            desc_selectors = ['.posting-content', '.section-wrapper']
            description = await get_text_by_selectors(page, desc_selectors)
            if description:
                job_data['description'] = description[:10000]
        
        # Salary/compensation
        salary_selectors = ['.salary', '.compensation', '.pay-range']
        salary = await get_text_by_selectors(page, salary_selectors)
        if salary:
            # Parse and clean the salary text
            job_data['salary_range'] = parse_salary_range(salary)
        else:
            # Set default message when no salary is found
            job_data['salary_range'] = "Not provided"
            
    except Exception as e:
        print(f"Error parsing Lever job: {e}")
    
    return job_data

async def extract_ashby_job(page, job_data):
    """Extract comprehensive job details from Ashby ATS"""
    try:
        # Title - h1 works well for Ashby
        title_selectors = ['h1']
        title = await get_text_by_selectors(page, title_selectors)
        if title:
            job_data['title'] = title
        
        # Company (extract from URL if not found on page)
        if not job_data.get('company') or job_data.get('company') == "Unknown Company":
            job_data['company'] = extract_company_from_url(job_data['url'])
        
        # Location - use more precise text-based search for Ashby's current structure
        try:
            # Try to find location using a more targeted approach
            location_text = await page.evaluate('''
                () => {
                    // First try to find location in specific elements
                    const locationSelectors = [
                        '[data-testid*="location"]',
                        '[class*="location"]',
                        '.location',
                        '[aria-label*="location" i]'
                    ];
                    
                    for (const selector of locationSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            const text = el.innerText?.trim();
                            if (text && text.length > 2 && text.length < 100 && 
                                !text.includes('window.') && 
                                !text.includes('__appData') &&
                                !text.includes('ddRum') &&
                                (text.includes('Remote') || text.includes('San Francisco') || text.includes('New York') || text.includes('Remote-International'))) {
                                return text;
                            }
                        }
                    }
                    
                    // Fallback: look for location in body text but filter out JavaScript
                    const bodyText = document.body.innerText;
                    const lines = bodyText.split('\\n');
                    
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        if (line.length > 2 && line.length < 100 && 
                            !line.includes('window.') && 
                            !line.includes('__appData') &&
                            !line.includes('ddRum') &&
                            !line.includes('ddRumApplicationId') &&
                            !line.includes('ddRumClientToken') &&
                            !line.includes('environment') &&
                            !line.includes('recaptcha') &&
                            (line === 'Remote-International' || line === 'Remote' || line.includes('San Francisco') || line.includes('New York'))) {
                            return line;
                        }
                    }
                    
                    return null;
                }
            ''')
            if location_text:
                job_data['location'] = location_text
        except Exception as e:
            print(f"Error extracting location: {e}")
        
        # Employment Type
        try:
            emp_type_element = await page.query_selector('div:has-text("Full time"), div:has-text("Employment Type")')
            if emp_type_element:
                emp_text = await emp_type_element.inner_text()
                if 'Full time' in emp_text:
                    job_data['employment_type'] = 'Full time'
                elif 'Part time' in emp_text:
                    job_data['employment_type'] = 'Part time'
                elif 'Contract' in emp_text:
                    job_data['employment_type'] = 'Contract'
        except Exception as e:
            print(f"Error extracting employment type: {e}")
        
        
        # Job ID from URL
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                job_data['job_id'] = url_parts[-1].split('?')[0]
        except:
            pass
        
        # Extract detailed content with updated selectors for Ashby's current structure
        content_selectors = [
            '._descriptionText_oj0x8_198',  # Main description text
            '._description_oj0x8_198',      # Description container
            '.ashby-job-posting-right-pane', # Right pane with content
            '._content_ud4nd_71',          # Main content area
            'div[id="overview"]'           # Overview section
        ]
        
        full_content = ""
        try:
            # Try multiple selectors to find content
            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    text = await content_element.inner_text()
                    if text and len(text.strip()) > 100:  # Only use substantial content
                        full_content = text.strip()
                        print(f"Ashby: Found content with selector {selector} ({len(text)} chars)")
                        break
            
            if full_content:
                job_data['description'] = full_content[:10000]
                print(f"Ashby: Extracted {len(full_content)} characters of content")
                
                # Parse sections from content
                sections = await parse_job_sections(full_content)
                job_data.update(sections)
                print(f"Ashby: Parsed sections: {list(sections.keys())}")
            else:
                print("Ashby: No substantial content found with any selector")
                
        except Exception as e:
            print(f"Ashby: Error extracting content: {e}")
            # Fallback to basic description
            desc_selectors = ['._descriptionText_oj0x8_198', '.ashby-job-posting-right-pane']
            description = await get_text_by_selectors(page, desc_selectors)
            if description:
                job_data['description'] = description[:10000]
        
        # Salary/compensation
        salary_selectors = ['.salary', '.compensation', '.pay-range']
        salary = await get_text_by_selectors(page, salary_selectors)
        if salary:
            # Parse and clean the salary text
            job_data['salary_range'] = parse_salary_range(salary)
        else:
            # Set default message when no salary is found
            job_data['salary_range'] = "Not provided"
            
    except Exception as e:
        print(f"Error parsing Ashby job: {e}")
    
    return job_data


async def extract_stripe_job(page, job_data):
    """Extract comprehensive job details from Stripe's custom job board"""
    try:
        # Title - Look for the actual job title, not the page header
        try:
            title_text = await page.evaluate('''
                () => {
                    // Look for the main job title (usually in a large heading)
                    const headings = document.querySelectorAll('h1, h2, h3');
                    for (let heading of headings) {
                        const text = heading.innerText.trim();
                        // Skip generic page titles like "JOBS" or "Jobs"
                        if (text && text !== 'JOBS' && text !== 'Jobs' && text.length > 5 && text.length < 100) {
                            // Check if it looks like a job title (contains common job title words)
                            if (text.includes('Engineer') || text.includes('Manager') || text.includes('Director') || 
                                text.includes('Analyst') || text.includes('Developer') || text.includes('Designer') ||
                                text.includes('Specialist') || text.includes('Coordinator') || text.includes('Lead')) {
                                return text;
                            }
                        }
                    }
                    return null;
                }
            ''')
            if title_text:
                job_data['title'] = title_text
        except:
            pass
        
        # Company is already set to "Stripe" from URL detection
        if not job_data.get('company'):
            job_data['company'] = 'Stripe'
        
        # Location - Extract from the job details card
        try:
            location_text = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && text.includes('Office locations')) {
                            const lines = text.split('\\n');
                            for (let i = 0; i < lines.length; i++) {
                                if (lines[i].trim() === 'Office locations') {
                                    // Look for the next non-empty line
                                    for (let j = i + 1; j < lines.length; j++) {
                                        const line = lines[j].trim();
                                        if (line && line !== '') {
                                            return line;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    return null;
                }
            ''')
            if location_text:
                job_data['location'] = location_text
        except:
            pass
        
        # Employment Type - Extract from job details
        try:
            emp_type_text = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && text.includes('Job type')) {
                            const lines = text.split('\\n');
                            for (let i = 0; i < lines.length; i++) {
                                if (lines[i].trim() === 'Job type') {
                                    // Look for the next non-empty line
                                    for (let j = i + 1; j < lines.length; j++) {
                                        const line = lines[j].trim();
                                        if (line && line !== '') {
                                            return line;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    return null;
                }
            ''')
            if emp_type_text:
                job_data['employment_type'] = emp_type_text
        except:
            pass
        
        
        # Job ID from URL - Stripe URLs have job IDs at the end
        try:
            url_parts = job_data['url'].split('/')
            if len(url_parts) > 1:
                job_data['job_id'] = url_parts[-1].split('?')[0]
        except:
            pass
        
        # Extract detailed content - Stripe has comprehensive job descriptions
        # Use a more targeted approach to find the actual job description content
        try:
            # First try to find the main content area with job description
            content_text = await page.evaluate('''
                () => {
                    // Look for the main job description content
                    const elements = document.querySelectorAll('*');
                    let bestContent = null;
                    let maxLength = 0;
                    
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && text.length > 1000) {  // Substantial content
                            // Check if it contains job description keywords
                            const hasJobContent = text.includes('About') || 
                                                text.includes('What you') || 
                                                text.includes('You will') ||
                                                text.includes('responsibilities') ||
                                                text.includes('requirements') ||
                                                text.includes('qualifications') ||
                                                text.includes('experience') ||
                                                text.includes('skills') ||
                                                text.includes('benefits');
                            
                            if (hasJobContent && text.length > maxLength) {
                                bestContent = text;
                                maxLength = text.length;
                            }
                        }
                    }
                    return bestContent;
                }
            ''')
            
            if content_text and len(content_text.strip()) > 500:
                job_data['description'] = content_text.strip()[:10000]
                print(f"Stripe: Extracted {len(content_text)} characters of content")
                
                # Parse sections from content
                sections = await parse_job_sections(content_text)
                job_data.update(sections)
                print(f"Stripe: Parsed sections: {list(sections.keys())}")
            else:
                print("Stripe: No substantial job description content found")
                
        except Exception as e:
            print(f"Stripe: Error extracting content: {e}")
            # Fallback to basic description
            desc_selectors = ['main', '.job-description', '.content']
            description = await get_text_by_selectors(page, desc_selectors)
            if description:
                job_data['description'] = description[:10000]
        
        # Salary information - Stripe often includes salary ranges
        try:
            salary_text = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (text.includes('$') || text.includes('salary') || text.includes('compensation'))) {
                            const lines = text.split('\\n');
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i].trim();
                                if (line.includes('$') && (line.includes('base salary') || line.includes('range'))) {
                                    return line;
                                }
                            }
                        }
                    }
                    return null;
                }
            ''')
            if salary_text:
                # Parse and clean the salary text
                job_data['salary_range'] = parse_salary_range(salary_text)
            else:
                # Set default message when no salary is found
                job_data['salary_range'] = "Not provided"
        except:
            # Set default message when no salary is found
            job_data['salary_range'] = "Not provided"
            
    except Exception as e:
        print(f"Error parsing Stripe job: {e}")
    
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
        
        # Salary/compensation
        salary_selectors = ['.salary', '.compensation', '.pay-range']
        salary = await get_text_by_selectors(page, salary_selectors)
        if salary:
            # Parse and clean the salary text
            job_data['salary_range'] = parse_salary_range(salary)
        else:
            # Set default message when no salary is found
            job_data['salary_range'] = "Not provided"
            
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

async def parse_job_sections(content):
    """Parse job content to extract structured sections"""
    sections = {}
    content_lower = content.lower()
    
    try:
        # Split content into lines for easier parsing
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        # Common section headers to look for
        section_headers = {
            'requirements': ['requirements', 'qualifications', 'what you need', 'you have', 'required skills', 'minimum qualifications'],
            'responsibilities': ['responsibilities', 'what you\'ll do', 'you will', 'duties', 'role description', 'job description'],
            'benefits': ['benefits', 'what we offer', 'perks', 'compensation', 'package'],
            'experience_level': ['experience', 'years', 'seniority', 'level'],
            'remote_type': ['remote', 'hybrid', 'onsite', 'location', 'work from']
        }
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            # Check if this line is a section header
            line_lower = line_clean.lower()
            found_section = None
            
            for section_key, keywords in section_headers.items():
                if any(keyword in line_lower for keyword in keywords):
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content)[:2000]
                    
                    current_section = section_key
                    section_content = []
                    found_section = True
                    break
            
            if not found_section and current_section:
                section_content.append(line_clean)
        
        # Save the last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)[:2000]
        
        # Extract salary information
        salary_patterns = [
            r'\$[\d,]+\s*[-–]\s*\$[\d,]+',
            r'\$[\d,]+(?:k|,000)',
            r'[\d,]+\s*[-–]\s*[\d,]+\s*(?:k|,000)',
            r'competitive\s+(?:salary|compensation)',
            r'base\s+salary.*?\$[\d,]+'
        ]
        
        import re
        for pattern in salary_patterns:
            match = re.search(pattern, content_lower)
            if match:
                sections['salary_range'] = match.group(0)
                break
        
        # Extract remote work information - look for specific patterns
        remote_keywords = {
            'remote': ['100% remote', 'fully remote', 'remote-first', 'work from anywhere', 'remote work'],
            'hybrid': ['hybrid', 'flexible', 'part remote', 'hybrid work'],
            'onsite': ['on-site', 'in-office', 'office-based', 'on site']
        }
        
        # Look for remote work info in specific sections, not the entire content
        for section_name, section_content in sections.items():
            if section_content and isinstance(section_content, str):
                section_lower = section_content.lower()
                for remote_type, keywords in remote_keywords.items():
                    if any(keyword in section_lower for keyword in keywords):
                        # Only set if we haven't found a better match
                        if 'remote_type' not in sections or remote_type == 'remote':
                            sections['remote_type'] = remote_type.title()
                            break
                if 'remote_type' in sections:
                    break
        
        # If no remote type found in sections, look in the first 1000 characters of content
        if 'remote_type' not in sections:
            content_sample = content_lower[:1000]  # Only check first 1000 characters
            for remote_type, keywords in remote_keywords.items():
                if any(keyword in content_sample for keyword in keywords):
                    sections['remote_type'] = remote_type.title()
                    break
        
    except Exception as e:
        print(f"Error parsing job sections: {e}")
    
    return sections

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

def is_fulltime_job(job_data):
    """Check if a job is full-time based on employment type"""
    emp_type = job_data.get('employment_type', '').lower()
    
    # If no employment type specified, assume full-time (industry standard)
    if not emp_type or emp_type in ['', 'null', 'none']:
        return True
    
    # Check for full-time indicators
    fulltime_indicators = [
        'full time', 'full-time', 'fulltime', 'full time employee',
        'permanent', 'salaried', 'employee'
    ]
    
    # Check for non-full-time indicators
    non_fulltime_indicators = [
        'part time', 'part-time', 'contract', 'temporary', 'temp',
        'intern', 'internship', 'freelance', 'consultant'
    ]
    
    # If it contains non-full-time indicators, it's not full-time
    for indicator in non_fulltime_indicators:
        if indicator in emp_type:
            return False
    
    # If it contains full-time indicators or is empty, it's full-time
    for indicator in fulltime_indicators:
        if indicator in emp_type:
            return True
    
    # Default to full-time if unclear
    return True

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

def extract_source_from_url(url):
    """Extract source platform from URL"""
    try:
        url_lower = url.lower()
        
        # Check for known ATS platforms
        if 'greenhouse' in url_lower:
            return 'Greenhouse'
        elif 'lever' in url_lower:
            return 'Lever'
        elif 'ashby' in url_lower:
            return 'Ashby'
        elif 'workday' in url_lower:
            return 'Workday'
        elif 'smartrecruiters' in url_lower:
            return 'SmartRecruiters'
        elif 'workable' in url_lower:
            return 'Workable'
        elif 'stripe.com' in url_lower:
            return 'Stripe'
        elif 'databricks.com' in url_lower:
            return 'Databricks'
        elif 'waymo.com' in url_lower:
            return 'Waymo'
        elif 'navan.com' in url_lower:
            return 'Navan'
        elif 'wiz.io' in url_lower:
            return 'Wiz'
        elif 'fivetran.com' in url_lower:
            return 'Fivetran'
        else:
            # Try to extract from domain for other platforms
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain:
                # Remove www. and common TLDs
                domain = domain.replace('www.', '')
                domain = domain.split('.')[0]
                return domain.replace('-', ' ').title()
    except Exception:
        pass
    return 'Other'

def save_job_to_db(job_data):
    """Save comprehensive job data to the database"""
    try:
        # Check if job already exists by URL
        existing_job = Job.query.filter_by(url=job_data.get('url')).first()
        if existing_job:
            # Smart update: only update if the job is incomplete or very old
            should_update = False
            update_reason = ""
            
            # Check if job is incomplete (missing key fields)
            if not existing_job.description or len(existing_job.description) < 200:
                should_update = True
                update_reason = "incomplete description"
            elif not existing_job.location:
                should_update = True
                update_reason = "missing location"
            elif not existing_job.employment_type:
                should_update = True
                update_reason = "missing employment type"
            # Check if job is very old (scraped more than 7 days ago)
            elif existing_job.scraped_at and (datetime.utcnow() - existing_job.scraped_at).days > 7:
                should_update = True
                update_reason = "stale data (7+ days old)"
            
            if should_update:
                print(f"Updating existing job ({update_reason}): {job_data.get('title', 'Unknown Title')}")
                
                # Update all fields with new data
                existing_job.title = job_data.get('title', existing_job.title)
                existing_job.company = job_data.get('company', existing_job.company)
                existing_job.location = job_data.get('location', existing_job.location)
                existing_job.employment_type = job_data.get('employment_type', existing_job.employment_type)
                existing_job.description = job_data.get('description', existing_job.description)
                existing_job.requirements = job_data.get('requirements', existing_job.requirements)
                existing_job.responsibilities = job_data.get('responsibilities', existing_job.responsibilities)
                existing_job.benefits = job_data.get('benefits', existing_job.benefits)
                existing_job.salary_range = job_data.get('salary_range', existing_job.salary_range)
                existing_job.experience_level = job_data.get('experience_level', existing_job.experience_level)
                existing_job.remote_type = job_data.get('remote_type', existing_job.remote_type)
                existing_job.job_id = job_data.get('job_id', existing_job.job_id)
                existing_job.application_deadline = job_data.get('application_deadline', existing_job.application_deadline)
                existing_job.posted_date = job_data.get('posted_date', existing_job.posted_date)
                existing_job.source = job_data.get('source', existing_job.source)
                existing_job.scraped_at = datetime.utcnow()  # Update scrape timestamp
                
                db.session.commit()
                print(f"Successfully updated job: {existing_job.title} at {existing_job.company}")
            else:
                print(f"Skipping complete job: {job_data.get('title', 'Unknown Title')} (already up-to-date)")
            return
        
        # Only save if we have a title (minimum requirement)
        if not job_data.get('title'):
            print("Skipping job - no title found")
            return
        
        # Check if job is full-time (filter out non-full-time jobs)
        if not is_fulltime_job(job_data):
            print(f"Skipping non-full-time job: {job_data.get('title', 'Unknown Title')} (employment_type: {job_data.get('employment_type', 'None')})")
            return
        
        # Standardize employment type to "Full time"
        job_data['employment_type'] = 'Full time'
        
        # Create new job record with all enhanced fields
        job = Job(
            title=job_data.get('title'),
            company=job_data.get('company'),
            location=job_data.get('location'),
            employment_type=job_data.get('employment_type'),
            description=job_data.get('description'),
            requirements=job_data.get('requirements'),
            responsibilities=job_data.get('responsibilities'),
            benefits=job_data.get('benefits'),
            salary_range=job_data.get('salary_range'),
            experience_level=job_data.get('experience_level'),
            remote_type=job_data.get('remote_type'),
            job_id=job_data.get('job_id'),
            application_deadline=job_data.get('application_deadline'),
            url=job_data.get('url'),
            posted_date=job_data.get('posted_date'),
            source=job_data.get('source'),
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
