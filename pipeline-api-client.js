/**
 * Pipeline API Client for External Scrapers
 * 
 * This client allows external scrapers to send job data directly to Pipeline's database
 * using the webhook and batch API endpoints.
 */

class PipelineAPIClient {
    constructor(baseURL, apiKey) {
        this.baseURL = baseURL.replace(/\/$/, ''); // Remove trailing slash
        this.apiKey = apiKey;
    }

    /**
     * Test the connection to Pipeline API
     */
    async testConnection() {
        try {
            const response = await fetch(`${this.baseURL}/api/health`, {
                method: 'GET',
                headers: {
                    'X-API-Key': this.apiKey
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Pipeline API connection successful:', data);
                return true;
            } else {
                console.error('❌ Pipeline API connection failed:', response.status, response.statusText);
                return false;
            }
        } catch (error) {
            console.error('❌ Pipeline API connection error:', error.message);
            return false;
        }
    }

    /**
     * Send a single job to Pipeline (real-time processing)
     */
    async createJob(jobData) {
        try {
            const response = await fetch(`${this.baseURL}/api/webhook/jobs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    jobs: [jobData],
                    source: 'A16Z Scraper'
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Job created successfully:', result);
                return result;
            } else {
                const error = await response.text();
                console.error('❌ Failed to create job:', response.status, error);
                return null;
            }
        } catch (error) {
            console.error('❌ Error creating job:', error.message);
            return null;
        }
    }

    /**
     * Send multiple jobs to Pipeline (batch processing)
     */
    async createJobsBatch(jobsData) {
        try {
            const response = await fetch(`${this.baseURL}/api/batch/jobs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    jobs: jobsData,
                    source: 'A16Z Scraper'
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log(`✅ Batch created successfully: ${result.created} jobs created, ${result.skipped} skipped`);
                return result;
            } else {
                const error = await response.text();
                console.error('❌ Failed to create batch:', response.status, error);
                return null;
            }
        } catch (error) {
            console.error('❌ Error creating batch:', error.message);
            return null;
        }
    }

    /**
     * Convert scraper job data to Pipeline format
     */
    convertJobData(scraperJob) {
        return {
            title: scraperJob.title || 'Unknown Title',
            company: scraperJob.company || 'Unknown Company',
            aboutJob: scraperJob.description || scraperJob.about_job || '',
            salaryRange: scraperJob.salary_range || scraperJob.salary || '',
            location: scraperJob.location || '',
            qualifications: scraperJob.qualifications || scraperJob.requirements || '',
            source: 'A16Z Jobs',
            sourceUrl: scraperJob.url || scraperJob.job_url || '',
            employmentType: scraperJob.employment_type || 'full-time',
            postedDate: scraperJob.posted_date || new Date().toISOString(),
            // Map any additional fields as needed
            aboutCompany: scraperJob.about_company || '',
            alternateLocations: scraperJob.alternate_locations || ''
        };
    }
}

export default PipelineAPIClient;
