import asyncio
import os
import re
import json
import requests
from playwright.async_api import async_playwright
from flask import Flask
from models import db, Job
from datetime import datetime

# Global reference to scraping status (set by app.py)
scraping_status = None

# Progress tracking file
PROGRESS_FILE = 'scraping_progress.json'

def load_progress():
    """Load progress from file"""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading progress: {e}")
    return {'last_processed_company': 0, 'total_companies': 0}

def save_progress(company_index, total_companies):
    """Save progress to file"""
    try:
        progress = {
            'last_processed_company': company_index,
            'total_companies': total_companies,
            'last_updated': datetime.now().isoformat()
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"Error saving progress: {e}")

# Pipeline API Configuration
PIPELINE_API_URL = os.environ.get('PIPELINE_API_URL', 'https://atpipeline.com')
PIPELINE_API_KEY = os.environ.get('PIPELINE_API_KEY', 'sPqH575yX54u1x72G2sLoUhc18nsqUJcqnMq3cYR')

def send_job_to_pipeline(job_data):
    """Send job data to Pipeline API"""
    try:
        # Debug: Print the API URL being used
        print(f"🔗 Using Pipeline API URL: {PIPELINE_API_URL}")
        
        # Convert job data to Pipeline format
        pipeline_job = {
            'title': job_data.get('title', 'Unknown Title'),
            'company': job_data.get('company', 'Unknown Company'),
            'aboutJob': job_data.get('about_job', ''),
            'salaryRange': job_data.get('salary_range', ''),
            'location': job_data.get('location', ''),
            'qualifications': job_data.get('qualifications', ''),
            'source': 'A16Z Jobs',
            'sourceUrl': job_data.get('source_url', ''),
            'employmentType': job_data.get('employment_type', 'full-time'),
            'postedDate': job_data.get('posted_date', datetime.now().isoformat()),
            'aboutCompany': job_data.get('about_company', ''),
            'alternateLocations': job_data.get('alternate_locations', '')
        }
        
        # Send to Pipeline API
        response = requests.post(
            f"{PIPELINE_API_URL}/api/webhook/jobs",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={
                'jobs': [pipeline_job],
                'source': 'A16Z Scraper'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sent job to Pipeline: {job_data.get('title', 'Unknown Title')} at {job_data.get('company', 'Unknown')}")
            return True
        else:
            print(f"❌ Failed to send job to Pipeline: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending job to Pipeline: {e}")
        return False

def send_batch_to_pipeline(jobs_data):
    """Send multiple jobs to Pipeline API in batch"""
    try:
        # Convert jobs data to Pipeline format
        pipeline_jobs = []
        for job_data in jobs_data:
            pipeline_job = {
                'title': job_data.get('title', 'Unknown Title'),
                'company': job_data.get('company', 'Unknown Company'),
                'aboutJob': job_data.get('about_job', ''),
                'salaryRange': job_data.get('salary_range', ''),
                'location': job_data.get('location', ''),
                'qualifications': job_data.get('qualifications', ''),
                'source': 'A16Z Jobs',
                'sourceUrl': job_data.get('source_url', ''),
                'employmentType': job_data.get('employment_type', 'full-time'),
                'postedDate': job_data.get('posted_date', datetime.now().isoformat()),
                'aboutCompany': job_data.get('about_company', ''),
                'alternateLocations': job_data.get('alternate_locations', '')
            }
            pipeline_jobs.append(pipeline_job)
        
        # Send batch to Pipeline API
        response = requests.post(
            f"{PIPELINE_API_URL}/api/batch/jobs",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={
                'jobs': pipeline_jobs,
                'source': 'A16Z Scraper'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sent batch to Pipeline: {result.get('created', 0)} jobs created, {result.get('skipped', 0)} skipped")
            return True
        else:
            print(f"❌ Failed to send batch to Pipeline: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending batch to Pipeline: {e}")
        return False

def set_scraping_status(status_dict):
    """Set the global scraping status dictionary from app.py"""
    global scraping_status
    scraping_status = status_dict

def parse_locations(location_text):
    """Parse location text and separate primary location from alternate locations"""
    if not location_text or location_text.strip() == "":
        return None, None
    
    # Clean the location text
    clean_text = location_text.strip()
    
    # Common separators for multiple locations (in order of preference)
    separators = [
        ';',  # Semicolon - most reliable for multiple locations
        '|',  # Pipe
        '\n',  # Newline
        ' and ',  # " and " (case insensitive)
        ' or ',   # " or " (case insensitive)
        ' • ',    # Bullet point
        ' / ',    # Forward slash
    ]
    
    # Try to split on separators
    locations = []
    for separator in separators:
        if separator in clean_text:
            # Split and clean each location
            parts = clean_text.split(separator)
            locations = [part.strip() for part in parts if part.strip()]
            
            # Check if any of the parts contain other separators and need further splitting
            expanded_locations = []
            for part in locations:
                # Check if this part contains other separators
                has_other_separators = any(sep in part for sep in separators if sep != separator)
                if has_other_separators:
                    # Recursively parse this part
                    sub_primary, sub_alternate = parse_locations(part)
                    if sub_primary:
                        expanded_locations.append(sub_primary)
                    if sub_alternate:
                        expanded_locations.extend(sub_alternate.split('; '))
                else:
                    expanded_locations.append(part)
            
            locations = expanded_locations
            # If we found locations, break and don't try other separators
            break
    
    # If no separators found, check if it looks like multiple locations with commas
    if not locations:
        # Only split on commas if it looks like multiple distinct locations
        # (e.g., "City, State, City, State" pattern)
        comma_parts = clean_text.split(', ')
        
        # Check if this looks like multiple locations by looking for state abbreviations
        location_keywords = ['CA', 'NY', 'TX', 'FL', 'WA', 'OR', 'CO', 'IL', 'MA', 'PA', 'GA', 'NC', 'VA', 'AZ', 'OH', 'MI', 'TN', 'IN', 'MO', 'MD', 'WI', 'MN', 'LA', 'AL', 'KY', 'SC', 'IA', 'OK', 'CT', 'UT', 'AR', 'NV', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI', 'NH', 'ME', 'RI', 'MT', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY']
        has_state_abbrevs = any(keyword in clean_text for keyword in location_keywords)
        
        if has_state_abbrevs and len(comma_parts) >= 3:
            # Try to group parts into city, state pairs
            grouped_locations = []
            i = 0
            while i < len(comma_parts):
                if i + 1 < len(comma_parts):
                    # Check if this looks like a city, state pair
                    current_part = comma_parts[i].strip()
                    next_part = comma_parts[i + 1].strip()
                    
                    # If next part is a state abbreviation, group them together
                    if next_part in location_keywords:
                        grouped_locations.append(f"{current_part}, {next_part}")
                        i += 2
                    else:
                        # Single part location
                        grouped_locations.append(current_part)
                        i += 1
                else:
                    # Last part
                    grouped_locations.append(comma_parts[i].strip())
                    i += 1
            
            if len(grouped_locations) > 1:
                locations = grouped_locations
            else:
                locations = [clean_text]
        else:
            locations = [clean_text]
    
    # Filter out empty or invalid locations
    valid_locations = []
    for loc in locations:
        loc = loc.strip()
        if loc and len(loc) > 1:
            valid_locations.append(loc)
    
    # If we have valid locations, separate primary from alternates
    if valid_locations:
        primary_location = valid_locations[0]
        alternate_locations = valid_locations[1:] if len(valid_locations) > 1 else []
        
        # Join alternate locations with semicolon for storage
        alternate_text = '; '.join(alternate_locations) if alternate_locations else None
        
        return primary_location, alternate_text
    
    return None, None

def is_us_based_job(location, alternate_locations=None):
    """
    Check if a job is US-based by examining location strings.
    Returns True if job is US-based, False if international.
    """
    if not location:
        # If no location specified, assume it might be international - skip to be safe
        return False
    
    # US state abbreviations
    us_states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]
    
    # US indicators (case insensitive)
    us_indicators = [
        'united states', 'usa', 'u.s.a', 'u.s.', 'us',
        'remote - us', 'remote (us)', 'remote us', 'us remote',
        'anywhere in the us', 'anywhere in the united states',
        'us-based', 'us based', 'nationwide'
    ]
    
    # International indicators (immediate red flags)
    international_indicators = [
        'uk', 'united kingdom', 'london', 'england', 'scotland', 'wales',
        'canada', 'toronto', 'vancouver', 'montreal', 'ottawa',
        'europe', 'european union', 'eu',
        'australia', 'sydney', 'melbourne',
        'india', 'bangalore', 'mumbai', 'delhi', 'hyderabad',
        'singapore', 'hong kong', 'china', 'beijing', 'shanghai',
        'japan', 'tokyo', 'germany', 'berlin', 'france', 'paris',
        'netherlands', 'amsterdam', 'sweden', 'switzerland',
        'israel', 'tel aviv', 'ireland', 'dublin',
        'mexico', 'brazil', 'argentina', 'chile',
        'emea', 'apac', 'latam'
    ]
    
    # Combine location and alternate locations for checking
    all_locations = [location]
    if alternate_locations:
        all_locations.extend([loc.strip() for loc in alternate_locations.split(';')])
    
    location_text = ' '.join(all_locations).lower()
    
    # First check: If ANY international indicator is present, reject immediately
    for indicator in international_indicators:
        if indicator in location_text:
            return False
    
    # Second check: Look for US indicators
    for indicator in us_indicators:
        if indicator in location_text:
            return True
    
    # Third check: Look for US state abbreviations (with word boundaries)
    location_upper = ' '.join(all_locations).upper()
    for state in us_states:
        # Check if state appears as whole word (not part of another word)
        if re.search(r'\b' + state + r'\b', location_upper):
            return True
    
    # Common US cities (not exhaustive, but covers major tech hubs)
    us_cities = [
        'new york', 'nyc', 'san francisco', 'los angeles', 'chicago',
        'seattle', 'boston', 'austin', 'denver', 'portland',
        'atlanta', 'miami', 'dallas', 'houston', 'phoenix',
        'philadelphia', 'san diego', 'san jose', 'palo alto',
        'mountain view', 'menlo park', 'cupertino', 'santa clara',
        'redmond', 'raleigh', 'durham', 'nashville', 'salt lake city',
        'minneapolis', 'detroit', 'pittsburgh', 'columbus', 'charlotte'
    ]
    
    for city in us_cities:
        if city in location_text:
            return True
    
    # If we can't determine it's US-based, default to False (skip the job)
    # This is conservative - we'd rather miss a US job than include an international one
    return False

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

async def scrape_a16z_jobs(batch_size=None, resume_from_progress=True):
    """Scrape job listings from a16z jobs website by company with batch processing"""
    app = create_app()
    
    # Get batch size from environment variable or use default
    if batch_size is None:
        batch_size = int(os.environ.get('SCRAPER_BATCH_SIZE', '20'))
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Import global status tracking
        from app import scraping_status
        
        # Load previous progress if resuming
        progress = load_progress() if resume_from_progress else {'last_processed_company': 0, 'total_companies': 0}
        start_company_index = progress['last_processed_company']
        
        print(f"🚀 Starting batch scraping: batch_size={batch_size}, resume_from={start_company_index}")
        
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
                
                # Step 2: Process companies in batches
                total_jobs_scraped = 0
                skipped_companies = 0
                
                # Calculate batch range
                end_company_index = min(start_company_index + batch_size, len(companies))
                companies_to_process = companies[start_company_index:end_company_index]
                
                print(f"📊 Processing companies {start_company_index + 1} to {end_company_index} of {len(companies)}")
                print(f"🎯 Batch size: {len(companies_to_process)} companies")
                
                for i, company_info in enumerate(companies_to_process):
                    global_company_index = start_company_index + i
                    
                    # Check if scraping should stop
                    print(f"Checking status before company {global_company_index + 1}: is_running={scraping_status['is_running']}")
                    if not scraping_status['is_running']:
                        print("🛑 Scraping stopped by user request")
                        break
                    
                    company_name = company_info['name']
                    company_url = company_info['url']
                    
                    # Update status
                    scraping_status['current_company'] = company_name
                    scraping_status['message'] = f'Processing {company_name} ({global_company_index + 1}/{len(companies)})'
                    
                    print(f"\n🏢 Processing company {global_company_index + 1}/{len(companies)}: {company_name}")
                    print(f"Company URL: {company_url}")
                    
                    # Save progress after each company
                    save_progress(global_company_index + 1, len(companies))
                    
                    # Check if this company needs scraping
                    needs_scraping, reason = should_scrape_company(company_name)
                    
                    if not needs_scraping:
                        print(f"⏭️  Skipping {company_name}: {reason}")
                        scraping_status['completed_companies'] = global_company_index + 1
                        skipped_companies += 1
                        continue
                    else:
                        print(f"🔄 Scraping {company_name}: {reason}")
                    
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
                        scraping_status['completed_companies'] = global_company_index + 1
                        print(f"✅ Completed {company_name}: {len(company_jobs)} jobs processed")
                        
                    except Exception as e:
                        print(f"❌ Error processing company {company_name}: {e}")
                        continue
                
                if scraping_status['is_running']:
                    batch_completed = end_company_index - start_company_index
                    scraping_status['message'] = f'Batch completed! Jobs: {total_jobs_scraped}, Companies: {batch_completed}'
                    print(f"\n🎉 Batch scraping completed!")
                    print(f"   📊 Total jobs scraped in this batch: {total_jobs_scraped}")
                    print(f"   ⏭️  Companies skipped (already complete): {skipped_companies}")
                    print(f"   🏢 Companies processed in this batch: {batch_completed - skipped_companies}")
                    print(f"   📈 Progress: {end_company_index}/{len(companies)} companies")
                    
                    # Check if we've completed all companies
                    if end_company_index >= len(companies):
                        print(f"   🎯 All companies completed! Resetting progress for next full cycle.")
                        save_progress(0, len(companies))  # Reset for next full cycle
                    else:
                        print(f"   ⏭️  Next batch will start from company {end_company_index + 1}")
                else:
                    print(f"\n🛑 Scraping stopped.")
                    print(f"   📊 Jobs scraped: {total_jobs_scraped}")
                    print(f"   ⏭️  Companies skipped: {skipped_companies}")
                
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

async def extract_raw_page_content(page):
    """Extract raw text content from job page for AI parsing"""
    try:
        raw_content = await page.evaluate('''
            () => {
                // Remove navigation, footer, and other non-job content
                const elementsToRemove = [
                    'nav', 'header', 'footer', 
                    '.navigation', '.nav', '.menu', 
                    '.cookie-banner', '.cookie-notice',
                    '[role="navigation"]', '[role="banner"]'
                ];
                
                elementsToRemove.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => el.remove());
                });
                
                // Get main content area or body text
                const mainContent = document.querySelector('main, article, .job-content, .job-description, #content, body');
                
                if (mainContent) {
                    return mainContent.innerText.trim();
                } else {
                    return document.body.innerText.trim();
                }
            }
        ''')
        
        return raw_content if raw_content else ""
    except Exception as e:
        print(f"Error extracting raw content: {e}")
        return ""

async def extract_job_details_advanced(page, job_url, company_name):
    """Extract job details with AI-first parsing"""
    job_data = {
        'source_url': job_url,
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
        
        # AI-FIRST APPROACH: Try AI parsing first
        global scraping_status
        
        try:
            from ai_parser import get_ai_parser
            
            # Extract raw page content
            raw_content = await extract_raw_page_content(page)
            
            if raw_content and len(raw_content) > 100:
                print(f"🤖 Using AI to parse: {job_url}")
                
                # Track AI call
                if scraping_status:
                    scraping_status['ai_calls'] = scraping_status.get('ai_calls', 0) + 1
                
                    # Estimate tokens (rough: ~750 chars per 1000 tokens)
                    # Now using up to 10000 chars input
                    estimated_input_tokens = len(raw_content[:10000]) / 0.75
                    
                    # Estimate cost (GPT-4o-mini: $0.00015 per 1K input tokens, $0.0006 per 1K output tokens)
                    # With comprehensive extraction, expecting ~500-800 output tokens
                    estimated_output_tokens = 600
                    estimated_cost = (estimated_input_tokens / 1000 * 0.00015) + (estimated_output_tokens / 1000 * 0.0006)
                    scraping_status['estimated_cost'] = scraping_status.get('estimated_cost', 0.0) + estimated_cost
                
                # Get AI parser instance
                ai_parser = get_ai_parser()
                
                # Parse with AI
                ai_result = await ai_parser.parse_job_safe(raw_content, job_url)
                
                # If AI successfully extracted data, use it
                if ai_result and ai_result.get('title') and ai_result.get('company'):
                    print(f"  ✅ AI successfully parsed: {ai_result.get('title')} at {ai_result.get('company')}")
                    
                    # Track AI success
                    if scraping_status:
                        scraping_status['ai_success'] = scraping_status.get('ai_success', 0) + 1
                    
                    # Merge AI results with job_data, prioritizing AI results
                    for key, value in ai_result.items():
                        if value:  # Only update if AI found a value
                            job_data[key] = value
                    
                    # Mark as AI-parsed
                    job_data['parsing_method'] = 'ai'
                    return job_data
                else:
                    print(f"  ⚠️  AI parsing incomplete, falling back to manual parsing")
                    if scraping_status:
                        scraping_status['manual_fallbacks'] = scraping_status.get('manual_fallbacks', 0) + 1
            else:
                print(f"  ⚠️  Insufficient content for AI parsing, using manual parsing")
                if scraping_status:
                    scraping_status['manual_fallbacks'] = scraping_status.get('manual_fallbacks', 0) + 1
                
        except Exception as ai_error:
            print(f"  ❌ AI parsing failed: {ai_error}, falling back to manual parsing")
            if scraping_status:
                scraping_status['manual_fallbacks'] = scraping_status.get('manual_fallbacks', 0) + 1
        
        # FALLBACK: Use manual provider-specific parsing
        print(f"📋 Using manual parsing for: {job_url}")
        job_data['parsing_method'] = 'manual'
        
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
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
            job_data['about_job'] = full_content[:10000]
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
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
            job_data['about_job'] = full_content[:10000]
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
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
            job_data['about_job'] = full_content[:10000]
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
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
            job_data['about_job'] = full_content[:10000]
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Employment type - assume Full time for most roles
        job_data['employment_type'] = 'Full time'
        
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
            job_data['about_job'] = full_content[:10000]
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

def should_filter_job_by_employment_type(job_data):
    """Check if job should be filtered based on employment type"""
    title = job_data.get('title', '').lower()
    description = job_data.get('description', '').lower()
    employment_type = job_data.get('employment_type', '').lower()
    
    # First check employment_type field - this is the most reliable indicator
    if employment_type in ['contract', 'part time', 'part-time', 'temporary', 'temp', 'internship', 'intern']:
        return True, f"Employment type is: '{employment_type}'"
    
    # Only check content for very specific patterns that indicate non-full-time work
    # Avoid false positives from legal compliance text
    content = f"{title} {description}"
    
    # More specific patterns that are less likely to be false positives
    specific_patterns = [
        r'\bpart.?time\b', r'\binternship\b', r'\bintern\b',
        r'\bapprentice\b', r'\bco.?op\b', r'\bseasonal\b', r'\bhourly\b',
        r'\btemporary position\b', r'\btemp position\b', r'\bfreelance\b'
    ]
    
    # Check for specific non-full-time indicators
    for pattern in specific_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found non-full-time indicator: '{pattern}'"
    
    # Only check for "contract" in very specific contexts to avoid legal text
    contract_context_patterns = [
        r'\bcontract position\b', r'\bcontract role\b', r'\bcontractor position\b',
        r'\bcontract work\b', r'\bcontract job\b'
    ]
    
    for pattern in contract_context_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found contract position indicator: '{pattern}'"
    
    return False, "Passed employment type filter"

def extract_work_environment_enhanced(content):
    """Extract work environment with robust pattern matching"""
    content_lower = content.lower()
    
    # Work environment detection patterns
    remote_patterns = [
        r'\bremote\b', r'\bwork from home\b', r'\bwfh\b', r'\bdistributed\b',
        r'\bvirtual\b', r'\btelecommute\b', r'\bfully remote\b', r'\b100% remote\b'
    ]
    
    hybrid_patterns = [
        r'\bhybrid\b', r'\bmix of remote and office\b', r'\bflexible\b',
        r'\bpartially remote\b', r'\bremote first\b', r'\boffice optional\b'
    ]
    
    in_office_patterns = [
        r'\bon.?site\b', r'\bin.?office\b', r'\bon.?premises\b', r'\boffice\b',
        r'\blocation\b', r'\bheadquarters\b', r'\bworkspace\b'
    ]
    
    # Check for remote work indicators
    for pattern in remote_patterns:
        if re.search(pattern, content_lower):
            return 'remote'
    
    # Check for hybrid work indicators
    for pattern in hybrid_patterns:
        if re.search(pattern, content_lower):
            return 'hybrid'
    
    # Check for in-office indicators
    for pattern in in_office_patterns:
        if re.search(pattern, content_lower):
            return 'in-office'
    
    return 'in-office'  # Default assumption

async def extract_greenhouse_salary(page, content):
    """Extract salary information from Greenhouse job posting"""
    salary_info = {}
    
    try:
        # First, try to find salary in dedicated sections
        salary_selectors = [
            '.salary', 
            '.compensation', 
            '.pay-range',
            '[class*="salary"]',
            '[class*="compensation"]',
            '[class*="pay"]'
        ]
        
        salary_text = await get_text_by_selectors(page, salary_selectors)
        
        # If not found in dedicated selectors, search in content
        if not salary_text and content:
            # Look for salary patterns in the content
            import re
            salary_patterns = [
                r'US Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
                r'Annual Base Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
                r'Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
                r'Compensation[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
                r'Pay Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
                r'\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?(?=\s|$)',
                r'\$?([\d,]+)K\s*[-–—]\s*\$?([\d,]+)K\s*USD?',
                r'\$?([\d,]+)\s*to\s*\$?([\d,]+)\s*USD?',
                r'\$?([\d,]+)K\s*to\s*\$?([\d,]+)K\s*USD?',
                # Add simple patterns for basic salary ranges
                r'\$([\d,]+)\s*[-–—]\s*\$([\d,]+)',
                r'\$([\d,]+)\s*to\s*\$([\d,]+)',
                r'Salary Range\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)',
                r'Compensation\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)',
                # Enhanced patterns for Anduril-style listings
                r'US Salary Range\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)\s*USD',
                r'Salary Range\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)\s*USD',
                r'\$([\d,]+)\s*[-–—]\s*\$([\d,]+)\s*USD',
                r'\$([\d,]+)\s*to\s*\$([\d,]+)\s*USD'
            ]
            
            for pattern in salary_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    min_salary = match.group(1).replace(',', '')
                    max_salary = match.group(2).replace(',', '')
                    
                    # Handle K notation
                    if 'K' in match.group(0).upper():
                        min_salary = str(int(min_salary) * 1000)
                        max_salary = str(int(max_salary) * 1000)
                    
                    salary_info['salary_range'] = f"${min_salary} - ${max_salary}"
                    salary_info['salary_min'] = int(min_salary)
                    salary_info['salary_max'] = int(max_salary)
                    return salary_info
        
        # If found in dedicated selectors, parse it
        if salary_text:
            parsed_salary = parse_salary_range(salary_text)
            if parsed_salary and parsed_salary != "Not provided":
                salary_info['salary_range'] = parsed_salary
                
                # Extract min/max from parsed salary
                if ' - ' in parsed_salary:
                    parts = parsed_salary.split(' - ')
                    if len(parts) == 2:
                        try:
                            salary_info['salary_min'] = int(parts[0].replace('$', '').replace(',', ''))
                            salary_info['salary_max'] = int(parts[1].replace('$', '').replace(',', ''))
                        except ValueError:
                            pass
                else:
                    try:
                        salary_info['salary_min'] = int(parsed_salary.replace('$', '').replace(',', ''))
                        salary_info['salary_max'] = None
                    except ValueError:
                        pass
                
                return salary_info
    
    except Exception as e:
        print(f"Error extracting Greenhouse salary: {e}")
    
    return None

def is_benefits_section_header(line):
    """Check if a line is a proper benefits section header"""
    line_lower = line.lower()
    benefit_headers = [
        'benefits', 'what we offer', 'perks', 'compensation', 'package',
        'healthcare benefits', 'additional benefits', 'retirement savings plan',
        'income protection', 'generous time off', 'family planning',
        'mental health resources', 'professional development',
        'comprehensive benefits', 'benefits package',
        'what you can expect', 'compensation and benefits', 'total rewards',
        'employee benefits', 'company benefits', 'work benefits'
    ]
    
    # Exclude salary-related lines that shouldn't trigger benefits section
    salary_indicators = [
        'us salary range', 'salary range', 'annual base salary range',
        'pay transparency disclosure', 'in addition to salary'
    ]
    
    # Only trigger if it's a benefits header AND not a salary-related line
    has_benefit_header = any(header in line_lower for header in benefit_headers)
    is_salary_line = any(indicator in line_lower for indicator in salary_indicators)
    
    return has_benefit_header and not is_salary_line

def clean_job_description(description, sections):
    """Clean job description by removing content that's now in separate sections"""
    if not description:
        return description
    
    lines = description.split('\n')
    cleaned_lines = []
    
    # Specific section headers to remove
    section_headers_to_remove = [
        'REQUIRED QUALIFICATIONS', 'PREFERRED QUALIFICATIONS', 'QUALIFICATIONS',
        'US Salary Range', 'Salary Range', 'Healthcare Benefits', 'Additional Benefits',
        'Benefits', 'What We Offer', 'Perks', 'Compensation', 'Package',
        'Retirement Savings Plan', 'Income Protection', 'Generous time off',
        'Family Planning', 'Mental Health Resources', 'Professional Development',
        'Commuter Benefits', 'Relocation Assistance'
    ]
    
    in_removable_section = False
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        line_lower = line_clean.lower()
        
        # Check if this line is a section header we want to remove
        if any(header.lower() in line_lower for header in section_headers_to_remove):
            in_removable_section = True
            continue
        
        # Check if we should stop removing content
        if in_removable_section:
            # Stop if we hit a new major section or end of content
            if any(phrase in line_lower for phrase in [
                'about the job', 'the opportunity', 'about this role',
                'what you\'ll do', 'responsibilities', 'duties',
                'create a job alert', 'apply for this job', 'back to jobs',
                'voluntary self-identification', 'equal employment opportunity'
            ]):
                in_removable_section = False
                # Add this line as it might be the start of a new section
                if not any(header.lower() in line_lower for header in section_headers_to_remove):
                    cleaned_lines.append(line_clean)
            continue
        
        # Add lines that are not in removable sections
        cleaned_lines.append(line_clean)
    
    return '\n'.join(cleaned_lines)

async def parse_greenhouse_sections(content):
    """Parse Greenhouse job content to extract structured sections"""
    sections = {}
    
    try:
        # Split content into lines for easier parsing
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        # Greenhouse-specific section headers - enhanced for better matching
        section_headers = {
            'responsibilities': [
                'what you\'ll do', 'what you will do', 'you will', 'responsibilities', 
                'duties', 'key responsibilities', 'role description', 'what you do',
                'about the job', 'the opportunity', 'about this role', 'key responsibilities',
                'what you\'ll be doing', 'what you will be doing', 'role overview',
                'position overview', 'job overview', 'responsibility',
                'you\'ll work to', 'you will work to', 'as a', 'in this role',
                'the ideal candidate will', 'you\'ll be responsible for', 'you will be responsible for'
            ],
            'qualifications': [
                'required qualifications', 'requirements', 'you should have', 
                'you have', 'qualifications', 'required skills', 'minimum qualifications',
                'preferred qualifications', 'nice to have', 'bonus points',
                'we\'d love to hear from you if you have', 'minimum qualifications',
                'preferred qualifications', 'qualifications', 'you should have',
                'required experience', 'experience required', 'skills required',
                'what we\'re looking for', 'ideal candidate', 'candidate requirements',
                'years of experience', 'experience in', 'proficiency in', 'knowledge of',
                'strong', 'excellent', 'ability to', 'must have', 'should have',
                '8+ years', '5+ years', '3+ years', '2+ years', '1+ years'
            ],
            'benefits': [
                'benefits', 'what we offer', 'perks', 'package',
                'healthcare benefits', 'additional benefits', 'retirement savings plan',
                'income protection', 'generous time off', 'family planning',
                'mental health resources', 'professional development',
                'comprehensive benefits', 'benefits package',
                'what you can expect', 'compensation and benefits', 'total rewards',
                'employee benefits', 'company benefits', 'work benefits',
                'us roles', 'uk & aus roles', 'ie roles', 'traditional 401k', 'roth', 
                'pension plan', 'superannuation plan', 'healthcare benefits', 'dental', 
                'vision plans', 'caregiver & wellness leave', 'family planning & parenting support',
                'commuter benefits', 'relocation assistance'
            ],
            'work_environment': [
                'remote work', 'work remotely', 'work from home', 'wfh', 'fully remote',
                'hybrid work', 'hybrid role', 'onsite work', 'on-site work', 'in-office',
                'this role can be held remotely', 'this role can be held from',
                'work location', 'office location', 'must be located', 'work arrangement',
                'work model', 'work style', 'location', 'workplace', 'work environment',
                'this is a hybrid role', 'this is a remote role', 'this is an onsite role'
            ]
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
                # Skip lines that are clearly not part of the current section
                skip_indicators = [
                    'create a job alert', 'create alert', 'apply for this job',
                    'indicates a required field', 'autofill with', 'first name',
                    'last name', 'email', 'phone', 'resume', 'cover letter',
                    'linkedin profile', 'website', 'portfolio', 'github',
                    'submit application', 'privacy policy', 'candidate data privacy',
                    'applicant-privacy-notice', 'voluntary self-identification',
                    'equal employment opportunity', 'global data privacy notice',
                    'commitment to equal opportunity', 'by applying for this job',
                    'flexible pto', 'company holidays', 'work-life balance',
                    'health insurance', 'dental', 'vision insurance', 'premium coverage',
                    'back to jobs', 'apply', 'powered by', 'greenhouse',
                    'read our privacy policy', 'don\'t check off every box',
                    'studies have shown that some of us', 'waymark is dedicated to building',
                    'you may be just the right candidate', 'interested in building your career',
                    'get future opportunities sent straight to your email',
                    'public burden statement', 'paperwork reduction act', 'omb control number',
                    'expires', 'survey should take', 'minutes to complete'
                ]
                
                # Special handling for different sections
                if current_section == 'benefits':
                    # For benefits section, stop at application forms or other major sections
                    if any(phrase in line_lower for phrase in [
                        'create a job alert', 'apply for this job', 'requirements',
                        'qualifications', 'responsibilities', 'what you\'ll do',
                        'back to jobs', 'apply', 'powered by', 'voluntary self-identification',
                        'equal employment opportunity', 'public burden statement'
                    ]):
                        break
                elif current_section == 'qualifications':
                    # For qualifications section, stop at benefits or application forms
                    if any(phrase in line_lower for phrase in [
                        'benefits', 'what we offer', 'perks', 'compensation',
                        'create a job alert', 'apply for this job', 'back to jobs',
                        'apply', 'powered by', 'us salary range'
                    ]):
                        break
                elif current_section == 'responsibilities':
                    # For responsibilities section, stop at qualifications or application forms
                    if any(phrase in line_lower for phrase in [
                        'qualifications', 'requirements', 'you should have',
                        'create a job alert', 'apply for this job', 'back to jobs',
                        'apply', 'powered by'
                    ]):
                        break
                
                if not any(indicator in line_lower for indicator in skip_indicators):
                    section_content.append(line_clean)
        
        # Save the last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)[:2000]
        
        # Post-process to extract benefits from compensation sections if not already found or if benefits section is too short
        if 'benefits' not in sections or len(sections.get('benefits', '')) < 100:
            content_lower = content.lower()
            benefits_indicators = [
                'offers equity', 'health insurance', 'dental', 'vision', 'retirement',
                '401k', 'pto', 'vacation', 'parental leave', 'wellness benefits',
                'mental health', 'generous pto', 'company holidays', 'work-life balance',
                'flexible pto', 'stock options', 'equity', 'benefits package',
                'comprehensive benefits', 'total rewards', 'additional benefits',
                'us salary range', 'salary range', 'us roles', 'uk & aus roles',
                'ie roles', 'traditional 401k', 'roth', 'pension plan', 'superannuation plan',
                'healthcare benefits', 'income protection', 'family planning',
                'professional development', 'commuter benefits', 'relocation assistance'
            ]
            
            # Look for benefits content in the full text
            benefits_content = []
            lines = content.split('\n')
            in_benefits_section = False
            
            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue
                    
                line_lower = line_clean.lower()
                
                # Check if this line starts a benefits section
                if any(phrase in line_lower for phrase in [
                    'healthcare benefits', 'additional benefits', 'benefits & perks',
                    'what we offer', 'perks', 'package',
                    'retirement savings plan', 'income protection', 'generous time off',
                    'family planning', 'mental health resources', 'professional development',
                    'anduril offers top-tier benefits', 'comprehensive medical, dental, and vision',
                    'income protection:', 'generous time off:', 'family planning & parenting support:',
                    'mental health resources:', 'professional development:', 'commuter benefits:',
                    'relocation assistance:', 'retirement savings plan'
                ]) and not any(salary_phrase in line_lower for salary_phrase in [
                    'salary range', 'us salary range', 'annual base salary range',
                    'pay transparency disclosure', 'in addition to salary',
                    'compensation factors', 'salary offer', 'base salary'
                ]):
                    in_benefits_section = True
                    benefits_content.append(line_clean)
                elif in_benefits_section and len(line_clean) > 20:  # Continue if we're in benefits section
                    # Stop if we hit application forms or other sections
                    if any(phrase in line_lower for phrase in [
                        'create a job alert', 'apply for this job', 'qualifications',
                        'requirements', 'responsibilities', 'what you\'ll do',
                        'voluntary self-identification', 'equal employment opportunity',
                        'public burden statement', 'back to jobs', 'apply', 'powered by',
                        'us salary range', 'salary range'
                    ]):
                        break
                    benefits_content.append(line_clean)
                elif in_benefits_section and len(line_clean) < 20:
                    # Short lines might be continuation
                    benefits_content.append(line_clean)
            
            if benefits_content:
                sections['benefits'] = '\n'.join(benefits_content)[:2000]
        
        # Fallback section detection for missed sections
        if 'responsibilities' not in sections or 'qualifications' not in sections:
            content_lower = content.lower()
            lines = content.split('\n')
            
            # Look for responsibilities patterns even without clear headers
            if 'responsibilities' not in sections:
                responsibilities_content = []
                in_responsibilities = False
                
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    line_lower = line_clean.lower()
                    
                    # Check for responsibilities indicators
                    if any(phrase in line_lower for phrase in [
                        'you\'ll work to', 'you will work to', 'as a', 'in this role',
                        'you\'ll be responsible for', 'you will be responsible for',
                        'the ideal candidate will', 'you\'ll generate', 'you\'ll shape',
                        'you\'ll bring', 'you\'ll lead', 'you\'ll drive', 'you\'ll create'
                    ]):
                        in_responsibilities = True
                        responsibilities_content.append(line_clean)
                    elif in_responsibilities and len(line_clean) > 20:
                        # Continue if we're in responsibilities section
                        if any(phrase in line_lower for phrase in [
                            'qualifications', 'requirements', 'benefits', 'compensation',
                            'create a job alert', 'apply for this job'
                        ]):
                            break
                        responsibilities_content.append(line_clean)
                
                if responsibilities_content:
                    sections['responsibilities'] = '\n'.join(responsibilities_content)[:2000]
            
            # Look for qualifications patterns even without clear headers
            if 'qualifications' not in sections:
                qualifications_content = []
                in_qualifications = False
                
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    line_lower = line_clean.lower()
                    
                    # Check for qualifications indicators
                    if any(phrase in line_lower for phrase in [
                        'years of experience', 'experience in', 'proficiency in', 'knowledge of',
                        'strong', 'excellent', 'ability to', 'must have', 'should have',
                        '8+ years', '5+ years', '3+ years', '2+ years', '1+ years',
                        'bachelor\'s degree', 'master\'s degree', 'phd', 'degree in'
                    ]):
                        in_qualifications = True
                        qualifications_content.append(line_clean)
                    elif in_qualifications and len(line_clean) > 20:
                        # Continue if we're in qualifications section
                        if any(phrase in line_lower for phrase in [
                            'benefits', 'compensation', 'what we offer',
                            'create a job alert', 'apply for this job'
                        ]):
                            break
                        qualifications_content.append(line_clean)
                
                if qualifications_content:
                    sections['qualifications'] = '\n'.join(qualifications_content)[:2000]
        
        # Special handling for work environment - look for specific patterns
        if 'work_environment' not in sections:
            content_lower = content.lower()
            
            # Look for specific remote work indicators
            if any(phrase in content_lower for phrase in [
                'this role can be held remotely', 'work remotely', 'fully remote',
                'work from home', 'remote work', 'wfh'
            ]):
                sections['work_environment'] = 'Remote'
            # Look for hybrid work indicators
            elif any(phrase in content_lower for phrase in [
                'hybrid work', 'hybrid role', 'mix of remote and office'
            ]):
                sections['work_environment'] = 'Hybrid'
            # Look for onsite work indicators
            elif any(phrase in content_lower for phrase in [
                'onsite work', 'on-site work', 'in-office', 'must be located',
                'work at our office', 'office location'
            ]):
                sections['work_environment'] = 'Onsite'
        
    except Exception as e:
        print(f"Error parsing Greenhouse sections: {e}")
    
    return sections

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
            job_data['company'] = extract_company_from_url(job_data['source_url'])
        
        # Location - Enhanced selectors for Greenhouse
        location_selectors = [
            '.job__location', 
            '[class*="location"]', 
            '.location', 
            '[data-mapped="location"]', 
            '.job-location',
            '.job-location-info',
            '.office-location',
            '.work-location'
        ]
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        else:
            # Fallback: look for location in the main content
            location_fallback = await page.evaluate('''
                () => {
                    const text = document.body.innerText;
                    const locationMatch = text.match(/([A-Za-z\\s,]+(?:California|New York|Texas|Florida|Washington|Illinois|Pennsylvania|Ohio|Georgia|North Carolina|Virginia|Massachusetts|Michigan|New Jersey|Arizona|Tennessee|Indiana|Missouri|Maryland|Wisconsin|Colorado|Minnesota|South Carolina|Alabama|Louisiana|Kentucky|Oregon|Oklahoma|Connecticut|Utah|Iowa|Nevada|Arkansas|Mississippi|Kansas|New Mexico|Nebraska|West Virginia|Idaho|Hawaii|New Hampshire|Maine|Montana|Rhode Island|Delaware|South Dakota|North Dakota|Alaska|Vermont|Wyoming|United States|Remote|Hybrid|Onsite|On-site|Work from home|WFH)\\s*[\\n\\r]/);
                    return locationMatch ? locationMatch[1].trim() : null;
                }
            ''')
            if location_fallback:
                primary_location, alternate_locations = parse_locations(location_fallback)
                job_data['location'] = primary_location
                job_data['alternate_locations'] = alternate_locations
        
        # Employment type - Enhanced detection with better logic
        type_selectors = ['.employment-type', '[data-mapped="employment_type"]']
        emp_type = await get_text_by_selectors(page, type_selectors)
        if emp_type:
            job_data['employment_type'] = emp_type
        else:
            # Fallback: infer from content with more precise logic
            emp_type_fallback = await page.evaluate('''
                () => {
                    const text = document.body.innerText.toLowerCase();
                    
                    // Look for explicit employment type indicators in job content
                    // Avoid legal compliance text by looking for patterns near job-related keywords
                    const jobContent = text.split('apply')[0]; // Focus on job content, not legal text
                    
                    // Check for part-time indicators first (more specific)
                    if (jobContent.includes('part time') || jobContent.includes('part-time') || 
                        jobContent.includes('parttime') || jobContent.includes('pt ')) {
                        return 'Part time';
                    }
                    
                    // Check for internship indicators
                    if (jobContent.includes('internship') || jobContent.includes('intern ')) {
                        return 'Internship';
                    }
                    
                    // Check for contract indicators in job context (not legal text)
                    if (jobContent.includes('contract position') || 
                        jobContent.includes('contract role') ||
                        jobContent.includes('contractor position') ||
                        jobContent.includes('temporary position') ||
                        jobContent.includes('temp position')) {
                        return 'Contract';
                    }
                    
                    // Check for full-time indicators
                    if (jobContent.includes('full time') || jobContent.includes('full-time') || 
                        jobContent.includes('fulltime') || jobContent.includes('ft ')) {
                        return 'Full time';
                    }
                    
                    // Default to full-time for most professional positions
                    return 'Full time';
                }
            ''')
            job_data['employment_type'] = emp_type_fallback
        
        # Check if job should be filtered based on employment type
        should_filter, filter_reason = should_filter_job_by_employment_type(job_data)
        if should_filter:
            print(f"Greenhouse: Job filtered - {filter_reason}")
            return None
        
        # Extract detailed content - use a simpler approach
        try:
            # Try to get content from the main content area
            content_element = await page.query_selector('main')
            if not content_element:
                content_element = await page.query_selector('body')
            
            if content_element:
                full_content = await content_element.inner_text()
                
                # Clean up the content by removing application form sections
                lines = full_content.split('\n')
                cleaned_lines = []
                
                # Skip initial navigation elements but continue processing
                skip_initial_phrases = ['Back to jobs', 'Apply']
                in_job_content = False
                lines_processed = 0
                
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    lines_processed += 1
                    
                    # Skip initial navigation elements
                    if not in_job_content and any(phrase in line_clean for phrase in skip_initial_phrases):
                        continue
                    
                    # Mark that we've started processing job content - be more inclusive
                    if not in_job_content:
                        # Start job content if we find company description, job title context, or job-related content
                        if (any(phrase in line_clean.lower() for phrase in [
                            'about', 'company', 'startup', 'building', 'developing', 'creating',
                            'job', 'role', 'position', 'responsibilities', 'requirements', 'qualifications',
                            'benefits', 'compensation', 'salary', 'perks', 'what we', 'who we',
                            'mission', 'vision', 'values', 'team', 'work', 'career'
                        ]) or lines_processed > 5):  # Start after skipping initial nav elements
                            in_job_content = True
                    
                    # Stop at application forms and job alerts (but only after we've started processing content)
                    if in_job_content and any(phrase in line_clean for phrase in [
                        'Create a Job Alert', 'Apply for this job', 'indicates a required field',
                        'First Name', 'Last Name', 'Email', 'Phone', 'Resume', 'Cover Letter',
                        'Submit Application', 'Powered by', 'Privacy Policy', 
                        'Don\'t check off every box', 'Studies have shown',
                        'Waymark is dedicated', 'You may be just the right candidate',
                        'Voluntary Self-Identification', 'Form CC-305', 'OMB Control Number'
                    ]):
                        break
                    
                    if in_job_content:
                        cleaned_lines.append(line_clean)
                
                full_content = '\n'.join(cleaned_lines)
            else:
                full_content = None
        except Exception as e:
            print(f"Error extracting content: {e}")
            full_content = None
        
        if full_content:
            # Parse sections from content with enhanced Greenhouse-specific parsing
            sections = await parse_greenhouse_sections(full_content)
            
            # Clean the description by removing content that's now in separate sections
            cleaned_description = clean_job_description(full_content, sections)
            
            # Combine responsibilities into about_job if present
            if 'responsibilities' in sections:
                responsibilities_text = sections['responsibilities']
                combined_about_job = cleaned_description + '\n\n' + responsibilities_text
                job_data['about_job'] = combined_about_job[:10000]
                del sections['responsibilities']
            else:
                job_data['about_job'] = cleaned_description[:10000]
            
            job_data.update(sections)
            print(f"Greenhouse: Extracted {len(full_content)} characters of content (filtered)")
            print(f"Greenhouse: Cleaned description to {len(job_data.get('about_job', ''))} characters")
            print(f"Greenhouse: Parsed sections: {list(sections.keys())}")
            
            # Enhanced work environment extraction
            job_data['work_environment'] = extract_work_environment_enhanced(full_content)
        else:
            print("Greenhouse: No substantial content found after filtering")
        
        # Posted date
        date_selectors = ['.posted-date', '.publication-date']
        posted_date = await get_text_by_selectors(page, date_selectors)
        if posted_date:
            job_data['posted_date'] = posted_date
        
        # Enhanced salary extraction - look in multiple places
        salary_info = await extract_greenhouse_salary(page, full_content)
        if salary_info:
            job_data.update(salary_info)
        else:
            job_data['salary_range'] = "Not provided"
            job_data['salary_min'] = None
            job_data['salary_max'] = None
            
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
            job_data['company'] = extract_company_from_url(job_data['source_url'])
        
        # Location
        location_selectors = ['.posting-categories .location', '.location']
        location = await get_text_by_selectors(page, location_selectors)
        if location:
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Employment type
        type_selectors = ['.posting-categories .commitment', '.employment-type']
        emp_type = await get_text_by_selectors(page, type_selectors)
        if emp_type:
            job_data['employment_type'] = emp_type
        
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
                job_data['about_job'] = full_content[:10000]
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
                job_data['about_job'] = description[:10000]
        
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
            job_data['company'] = extract_company_from_url(job_data['source_url'])
        
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
                # Parse locations to separate primary from alternates
                primary_location, alternate_locations = parse_locations(location_text)
                job_data['location'] = primary_location
                job_data['alternate_locations'] = alternate_locations
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
                job_data['about_job'] = full_content[:10000]
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
                job_data['about_job'] = description[:10000]
        
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
                # Parse locations to separate primary from alternates
                primary_location, alternate_locations = parse_locations(location_text)
                job_data['location'] = primary_location
                job_data['alternate_locations'] = alternate_locations
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
                job_data['about_job'] = content_text.strip()[:10000]
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
                job_data['about_job'] = description[:10000]
        
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
            # Parse locations to separate primary from alternates
            primary_location, alternate_locations = parse_locations(location)
            job_data['location'] = primary_location
            job_data['alternate_locations'] = alternate_locations
        
        # Description
        desc_selectors = ['.description', '.job-description', 'main', '.content']
        description = await get_text_by_selectors(page, desc_selectors)
        if description:
            job_data['about_job'] = description[:5000]
        
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
            'about_company': ['about us', 'about the company', 'about', 'who we are', 'our company', 'our mission', 'company overview', 'our story'],
            'qualifications': ['requirements', 'qualifications', 'what you need', 'you have', 'required skills', 'minimum qualifications'],
            'responsibilities': ['responsibilities', 'what you\'ll do', 'you will', 'duties', 'role description', 'job description'],
            'benefits': ['benefits', 'what we offer', 'perks', 'compensation', 'package'],
            'work_environment': ['remote', 'hybrid', 'onsite', 'location', 'work from']
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
                for work_env_type, keywords in remote_keywords.items():
                    if any(keyword in section_lower for keyword in keywords):
                        # Only set if we haven't found a better match
                        if 'work_environment' not in sections or work_env_type == 'remote':
                            sections['work_environment'] = work_env_type.title()
                            break
                if 'work_environment' in sections:
                    break
        
        # If no work environment found in sections, look in the first 1000 characters of content
        if 'work_environment' not in sections:
            content_sample = content_lower[:1000]  # Only check first 1000 characters
            for work_env_type, keywords in remote_keywords.items():
                if any(keyword in content_sample for keyword in keywords):
                    sections['work_environment'] = work_env_type.title()
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

def should_scrape_company(company_name):
    """Check if a company needs to be scraped based on existing data"""
    try:
        # Get all jobs for this company
        company_jobs = Job.query.filter_by(company=company_name).all()
        
        # If no jobs exist, definitely scrape
        if not company_jobs:
            return True, "no existing jobs"
        
        # Check if any jobs are incomplete or stale
        now = datetime.utcnow()
        incomplete_count = 0
        stale_count = 0
        
        for job in company_jobs:
            # Check for incomplete data
            if not job.about_job or len(job.about_job) < 200:
                incomplete_count += 1
            elif not job.location or not job.employment_type:
                incomplete_count += 1
            # Check for stale data (more than 7 days old)
            elif job.scraped_at and (now - job.scraped_at).days > 7:
                stale_count += 1
        
        # If we have any incomplete or stale jobs, scrape this company
        if incomplete_count > 0:
            return True, f"{incomplete_count} incomplete job(s)"
        if stale_count > 0:
            return True, f"{stale_count} stale job(s) (7+ days old)"
        
        # All jobs are complete and recent
        return False, f"all {len(company_jobs)} job(s) are complete and recent"
        
    except Exception as e:
        print(f"Error checking company status: {e}")
        # If there's an error, scrape to be safe
        return True, "error checking status"

def save_job_to_db(job_data):
    """Save comprehensive job data to the database"""
    try:
        # Import salary parser for filtering
        from salary_parser import SalaryParser
        parser = SalaryParser()
        
        # Check if job should be skipped due to hourly-only salary
        salary_text = job_data.get('salary_range', '')
        if salary_text and parser.should_skip_job(salary_text):
            print(f"Skipping hourly-only job: {job_data.get('title', 'Unknown Title')} (salary: {salary_text[:50]}...)")
            return
        
        # Check if job is US-based (skip international jobs)
        location = job_data.get('location', '')
        alternate_locations = job_data.get('alternate_locations', '')
        if not is_us_based_job(location, alternate_locations):
            print(f"🌍 Skipping international job: {job_data.get('title', 'Unknown Title')} at {job_data.get('company', 'Unknown')} (location: {location})")
            return
        
        # Skip jobs from Andreessen Horowitz itself (the VC firm - we want portfolio companies only)
        company_name = job_data.get('company', '').lower()
        a16z_variations = ['andreessen horowitz', 'andreesen horowitz', 'a16z', 'a16 z', 'horowitz']
        if any(variation in company_name for variation in a16z_variations):
            print(f"🏢 Skipping Andreessen Horowitz job (VC firm itself): {job_data.get('title', 'Unknown Title')}")
            return
        
        # Check if job already exists by URL
        existing_job = Job.query.filter_by(source_url=job_data.get('source_url')).first()
        if existing_job:
            # Smart update: only update if the job is incomplete or very old
            should_update = False
            update_reason = ""
            
            # Check if job is incomplete (missing key fields)
            if not existing_job.about_job or len(existing_job.about_job) < 200:
                should_update = True
                update_reason = "incomplete about_job"
            elif not existing_job.location:
                should_update = True
                update_reason = "missing location"
            elif not existing_job.employment_type:
                should_update = True
                update_reason = "missing employment type"
            # Check if job has location but no alternate_locations (needs location parsing)
            elif existing_job.location and not existing_job.alternate_locations:
                # Check if the location text contains multiple locations that could be parsed
                primary, alternate = parse_locations(existing_job.location)
                if alternate:  # If parsing would create alternate locations
                    should_update = True
                    update_reason = "location needs parsing for alternate locations"
            # Check if job is very old (scraped more than 7 days ago)
            elif existing_job.scraped_at and (datetime.utcnow() - existing_job.scraped_at).days > 7:
                should_update = True
                update_reason = "stale data (7+ days old)"
            
            if should_update:
                print(f"Updating existing job ({update_reason}): {job_data.get('title', 'Unknown Title')}")
                
                # Update all fields with new data
                existing_job.title = job_data.get('title', existing_job.title)
                existing_job.company = job_data.get('company', existing_job.company)
                existing_job.about_company = job_data.get('about_company', existing_job.about_company)
                existing_job.location = job_data.get('location', existing_job.location)
                existing_job.alternate_locations = job_data.get('alternate_locations', existing_job.alternate_locations)
                existing_job.employment_type = job_data.get('employment_type', existing_job.employment_type)
                existing_job.about_job = job_data.get('about_job', existing_job.about_job)
                existing_job.qualifications = job_data.get('qualifications', existing_job.qualifications)
                existing_job.benefits = job_data.get('benefits', existing_job.benefits)
                existing_job.salary_range = job_data.get('salary_range', existing_job.salary_range)
                existing_job.salary_min = job_data.get('salary_min', existing_job.salary_min)
                existing_job.salary_max = job_data.get('salary_max', existing_job.salary_max)
                existing_job.work_environment = job_data.get('work_environment', existing_job.work_environment)
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
        
        # Parse and standardize salary data
        if salary_text:
            standardized_salary = parser.standardize_salary_range(salary_text)
            job_data['salary_range'] = standardized_salary
            
            # Also parse for min/max values (for future use)
            salary_data = parser.parse_salary(salary_text)
            job_data['salary_min'] = salary_data.min_salary
            job_data['salary_max'] = salary_data.max_salary
        
        # Create new job record with all enhanced fields
        job = Job(
            title=job_data.get('title'),
            company=job_data.get('company'),
            about_company=job_data.get('about_company'),
            location=job_data.get('location'),
            alternate_locations=job_data.get('alternate_locations'),
            employment_type=job_data.get('employment_type'),
            about_job=job_data.get('about_job'),
            qualifications=job_data.get('qualifications'),
            benefits=job_data.get('benefits'),
            salary_range=job_data.get('salary_range'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max'),
            work_environment=job_data.get('work_environment'),
            source_url=job_data.get('source_url'),
            posted_date=job_data.get('posted_date'),
            source=job_data.get('source'),
            scraped_at=datetime.utcnow()
        )
        
        db.session.add(job)
        db.session.commit()
        
        # Also send to Pipeline API
        send_job_to_pipeline(job_data)
        
    except Exception as e:
        print(f"Error saving job to database: {e}")
        db.session.rollback()

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    batch_size = None
    resume = True
    
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
            print(f"Using batch size from command line: {batch_size}")
        except ValueError:
            print(f"Invalid batch size: {sys.argv[1]}. Using default.")
    
    if len(sys.argv) > 2:
        resume = sys.argv[2].lower() in ['true', '1', 'yes', 'y']
        print(f"Resume from progress: {resume}")
    
    print("Starting a16z jobs scraper...")
    asyncio.run(scrape_a16z_jobs(batch_size=batch_size, resume_from_progress=resume))
