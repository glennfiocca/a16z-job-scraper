#!/usr/bin/env python3
"""
New Stripe job extraction function
"""

async def extract_stripe_job(page, job_data):
    """Extract comprehensive job details from Stripe's custom job board"""
    try:
        # Company is already set to "Stripe" from URL detection
        if not job_data.get('company'):
            job_data['company'] = 'Stripe'
        
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
                                if (lines[i].trim() === 'Office locations' && i + 1 < lines.length) {
                                    return lines[i + 1].trim();
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
                                if (lines[i].trim() === 'Job type' && i + 1 < lines.length) {
                                    return lines[i + 1].trim();
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
        
        # Extract detailed content - Get the main job description
        try:
            # Look for the main content area with job description
            content_text = await page.evaluate('''
                () => {
                    // Look for the main job description content
                    const contentSelectors = [
                        'main',
                        '.job-description',
                        '.content',
                        'article',
                        '[class*="description"]',
                        '[class*="content"]'
                    ];
                    
                    for (let selector of contentSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const text = element.innerText;
                            // Make sure it's substantial content (not just navigation)
                            if (text && text.length > 500) {
                                return text;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if content_text:
                job_data['description'] = content_text[:10000]
                
                # Parse sections from content
                sections = await parse_job_sections(content_text)
                job_data.update(sections)
        except Exception as e:
            print(f"Error extracting Stripe content: {e}")
            
    except Exception as e:
        print(f"Error parsing Stripe job: {e}")
    
    return job_data
