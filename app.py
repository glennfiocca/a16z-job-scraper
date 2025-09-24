import os
import asyncio
import threading
from flask import Flask, render_template, request, jsonify
from models import db, Job
from datetime import datetime, timedelta
from sqlalchemy import desc, func

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
        stats = {
            'total_jobs': Job.query.filter(Job.title != 'Unknown Title').count(),
            'companies': db.session.query(func.count(func.distinct(Job.company))).filter(
                Job.company.isnot(None), Job.title != 'Unknown Title'
            ).scalar(),
            'latest_update': Job.query.order_by(desc(Job.scraped_at)).first().scraped_at if Job.query.count() > 0 else None
        }
        
        # Get company list for filter dropdown
        companies = db.session.query(Job.company).filter(
            Job.company.isnot(None), Job.title != 'Unknown Title'
        ).distinct().order_by(Job.company).all()
        companies = [c[0] for c in companies]
        
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
        } for job in jobs])

@app.route('/stats')
def stats():
    """Statistics page"""
    with app.app_context():
        # Company breakdown
        company_stats = db.session.query(
            Job.company, 
            func.count(Job.id).label('count')
        ).filter(
            Job.company.isnot(None), Job.title != 'Unknown Title'
        ).group_by(Job.company).order_by(func.count(Job.id).desc()).all()
        
        # Recent jobs (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_jobs = Job.query.filter(
            Job.scraped_at >= cutoff,
            Job.title != 'Unknown Title'
        ).order_by(desc(Job.scraped_at)).limit(10).all()
        
        stats_data = {
            'total_jobs': Job.query.filter(Job.title != 'Unknown Title').count(),
            'companies': len(company_stats),
            'company_breakdown': company_stats,
            'recent_jobs': recent_jobs
        }
        
        return render_template('stats.html', stats=stats_data)

@app.route('/trigger-scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger the job scraper"""
    try:
        # Import the scraper function
        from main import scrape_a16z_jobs
        
        # Run the async scraper in a separate thread
        def run_scraper():
            asyncio.run(scrape_a16z_jobs())
        
        # Start scraping in background thread
        thread = threading.Thread(target=run_scraper)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': 'Job scraping started! Check back in a few minutes for new jobs.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error starting scraper: {str(e)}'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)