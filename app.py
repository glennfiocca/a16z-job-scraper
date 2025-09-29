import os
import asyncio
import threading
from flask import Flask, render_template, request, jsonify
from models import db, Job
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import signal
import sys

def create_app():
    app = Flask(__name__)
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        print("WARNING: Using auto-generated secret key. Set FLASK_SECRET_KEY environment variable for production.")
    app.secret_key = secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    return app

app = create_app()

# Global variables to track scraping state
scraping_thread = None
scraping_status = {
    'is_running': False,
    'message': '',
    'start_time': None,
    'current_company': None,
    'total_companies': 0,
    'completed_companies': 0
}

@app.route('/')
def index():
    """Homepage with job listings"""
    page = request.args.get('page', 1, type=int)
    company_filter = request.args.get('company', '')
    search_query = request.args.get('search', '')
    
    with app.app_context():
        # Base query
        query = Job.query.filter(Job.title != 'Unknown Title')
        
        # Apply filters
        if company_filter:
            query = query.filter(Job.company.ilike(f'%{company_filter}%'))
        
        if search_query:
            query = query.filter(
                Job.title.ilike(f'%{search_query}%') |
                Job.description.ilike(f'%{search_query}%') |
                Job.company.ilike(f'%{search_query}%')
            )
        
        # Paginate results
        jobs = query.order_by(desc(Job.scraped_at)).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Get statistics
        total_jobs = Job.query.filter(Job.title != 'Unknown Title').count()
        latest_job = Job.query.order_by(desc(Job.scraped_at)).first()
        
        stats = {
            'total_jobs': total_jobs,
            'companies': db.session.query(func.count(func.distinct(Job.company))).filter(
                Job.company.isnot(None), Job.title != 'Unknown Title'
            ).scalar() if total_jobs > 0 else 0,
            'latest_update': latest_job.scraped_at if latest_job else None
        }
        
        # Get company list for filter dropdown
        if total_jobs > 0:
            companies = db.session.query(Job.company).filter(
                Job.company.isnot(None), Job.title != 'Unknown Title'
            ).distinct().order_by(Job.company).all()
            companies = [c[0] for c in companies]
        else:
            companies = []
        
        return render_template('index.html', 
                             jobs=jobs, 
                             stats=stats, 
                             companies=companies,
                             current_company=company_filter,
                             current_search=search_query)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    """Individual job detail page"""
    with app.app_context():
        job = Job.query.get_or_404(job_id)
        return render_template('job_detail.html', job=job)

@app.route('/api/jobs')
def api_jobs():
    """API endpoint for job data"""
    with app.app_context():
        jobs = Job.query.filter(Job.title != 'Unknown Title').order_by(desc(Job.scraped_at)).limit(100).all()
        
        return jsonify([{
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'employment_type': job.employment_type,
            'url': job.url,
            'posted_date': job.posted_date,
            'scraped_at': job.scraped_at.isoformat() if job.scraped_at else None
        } for job in jobs] if jobs else [])

@app.route('/stats')
@app.route('/stats/')
def stats():
    """Statistics page"""
    with app.app_context():
        # Company breakdown
        total_jobs = Job.query.filter(Job.title != 'Unknown Title').count()
        
        if total_jobs > 0:
            company_stats = db.session.query(
                Job.company, 
                func.count(Job.id).label('count')
            ).filter(
                Job.company.isnot(None), Job.title != 'Unknown Title'
            ).group_by(Job.company).order_by(func.count(Job.id).desc()).all()
            
            # Job source breakdown using the source column
            source_breakdown = db.session.query(
                Job.source, 
                func.count(Job.id).label('count')
            ).filter(
                Job.source.isnot(None), 
                Job.title != 'Unknown Title'
            ).group_by(Job.source).order_by(func.count(Job.id).desc()).all()
            
            # Convert Row objects to tuples for template compatibility
            source_breakdown = [(row.source, row.count) for row in source_breakdown]
            
            # Recent jobs (last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_jobs = Job.query.filter(
                Job.scraped_at >= cutoff,
                Job.title != 'Unknown Title'
            ).order_by(desc(Job.scraped_at)).limit(10).all()
        else:
            company_stats = []
            source_breakdown = []
            recent_jobs = []
        
        stats_data = {
            'total_jobs': total_jobs,
            'companies': len(company_stats),
            'company_breakdown': company_stats,
            'source_breakdown': source_breakdown,
            'recent_jobs': recent_jobs
        }
        
        return render_template('stats.html', stats=stats_data)

@app.route('/trigger-scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger the job scraper"""
    global scraping_thread, scraping_status
    
    try:
        # Check if already running
        if scraping_status['is_running']:
            return jsonify({
                'status': 'error',
                'message': 'Scraping is already in progress!'
            }), 400
        
        # Import the scraper function
        from main import scrape_a16z_jobs
        
        # Update status
        scraping_status['is_running'] = True
        scraping_status['message'] = 'Starting scraper...'
        scraping_status['start_time'] = datetime.utcnow()
        scraping_status['current_company'] = None
        scraping_status['total_companies'] = 0
        scraping_status['completed_companies'] = 0
        
        # Run the async scraper in a separate thread
        def run_scraper():
            global scraping_status
            try:
                print("Starting scraper in background thread...")
                asyncio.run(scrape_a16z_jobs())
                print("Scraper completed successfully")
            except Exception as e:
                print(f"Scraper error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                scraping_status['is_running'] = False
                scraping_status['message'] = 'Scraping completed!'
                print("Scraper thread finished")
        
        # Start scraping in background thread
        scraping_thread = threading.Thread(target=run_scraper)
        scraping_thread.daemon = True
        scraping_thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': 'Job scraping started! Processing companies in batches...'
        })
        
    except Exception as e:
        scraping_status['is_running'] = False
        return jsonify({
            'status': 'error',
            'message': f'Error starting scraper: {str(e)}'
        }), 500

@app.route('/stop-scrape', methods=['POST'])
def stop_scrape():
    """Stop the running scraper"""
    global scraping_thread, scraping_status
    
    try:
        if not scraping_status['is_running']:
            return jsonify({
                'status': 'error',
                'message': 'No scraping process is currently running.'
            }), 400
        
        # Set stop flag
        scraping_status['is_running'] = False
        scraping_status['message'] = 'Stopping scraper...'
        
        # Wait for thread to finish (with timeout)
        if scraping_thread and scraping_thread.is_alive():
            scraping_thread.join(timeout=5)
        
        return jsonify({
            'status': 'success',
            'message': 'Scraping stopped successfully.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error stopping scraper: {str(e)}'
        }), 500

@app.route('/scrape-status')
def scrape_status():
    """Get current scraping status"""
    global scraping_status
    
    return jsonify({
        'is_running': scraping_status['is_running'],
        'message': scraping_status['message'],
        'start_time': scraping_status['start_time'].isoformat() if scraping_status['start_time'] else None,
        'current_company': scraping_status['current_company'],
        'total_companies': scraping_status['total_companies'],
        'completed_companies': scraping_status['completed_companies']
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)