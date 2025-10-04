#!/usr/bin/env python3
"""
Cleanup script to remove existing jobs that only have hourly salary data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from salary_parser import SalaryParser
from app import create_app
from models import db, Job

def cleanup_hourly_jobs(dry_run=True):
    """Remove jobs that only have hourly salary data"""
    app = create_app()
    
    with app.app_context():
        parser = SalaryParser()
        
        print("🧹 CLEANING UP HOURLY-ONLY JOBS")
        print("=" * 60)
        
        # Get all jobs with salary data
        jobs_with_salary = Job.query.filter(
            Job.salary_range.isnot(None),
            Job.salary_range != '',
            Job.salary_range != 'NULL'
        ).all()
        
        print(f"📊 Found {len(jobs_with_salary):,} jobs with salary data")
        
        if len(jobs_with_salary) == 0:
            print("✅ No jobs with salary data found")
            return
        
        # Analyze jobs to find hourly-only ones
        hourly_jobs = []
        annual_jobs = []
        no_salary_jobs = []
        
        print(f"\n🔍 Analyzing salary data...")
        
        for job in jobs_with_salary:
            salary_text = job.salary_range
            
            if parser.should_skip_job(salary_text):
                hourly_jobs.append(job)
            else:
                # Check if it has actual salary data or is just "Not specified"
                if salary_text and salary_text.strip().lower() not in ['not specified', 'null', 'none', '']:
                    annual_jobs.append(job)
                else:
                    no_salary_jobs.append(job)
        
        print(f"📊 Analysis Results:")
        print(f"   Jobs with annual salary: {len(annual_jobs):,}")
        print(f"   Jobs with no salary data: {len(no_salary_jobs):,}")
        print(f"   Jobs with hourly-only data: {len(hourly_jobs):,}")
        
        if len(hourly_jobs) == 0:
            print("✅ No hourly-only jobs found - nothing to clean up")
            return
        
        # Show sample hourly jobs that would be deleted
        print(f"\n📋 Sample hourly-only jobs to be deleted:")
        for i, job in enumerate(hourly_jobs[:10], 1):
            print(f"   {i:2d}. {job.title} at {job.company}")
            print(f"       Salary: {job.salary_range[:80]}{'...' if len(job.salary_range) > 80 else ''}")
            print(f"       URL: {job.source_url}")
            print()
        
        if len(hourly_jobs) > 10:
            print(f"   ... and {len(hourly_jobs) - 10:,} more jobs")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No jobs were actually deleted")
            print(f"   To actually delete {len(hourly_jobs):,} hourly-only jobs, run with dry_run=False")
            return
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: About to delete {len(hourly_jobs):,} jobs!")
        print("✅ Proceeding with deletion as requested...")
        
        # Delete hourly-only jobs
        print(f"\n🗑️  Deleting hourly-only jobs...")
        deleted_count = 0
        
        for job in hourly_jobs:
            try:
                db.session.delete(job)
                deleted_count += 1
                if deleted_count % 100 == 0:
                    print(f"   Deleted {deleted_count:,} jobs...")
            except Exception as e:
                print(f"   ❌ Error deleting job {job.id}: {e}")
                continue
        
        # Commit deletions
        try:
            db.session.commit()
            print(f"\n✅ Successfully deleted {deleted_count:,} hourly-only jobs")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing deletions: {e}")
            return
        
        # Show final statistics
        remaining_jobs = Job.query.count()
        print(f"\n📊 Final Statistics:")
        print(f"   Jobs deleted: {deleted_count:,}")
        print(f"   Remaining jobs: {remaining_jobs:,}")
        
        return deleted_count

def analyze_salary_data():
    """Analyze current salary data distribution without making changes"""
    app = create_app()
    
    with app.app_context():
        parser = SalaryParser()
        
        print("📊 SALARY DATA ANALYSIS")
        print("=" * 60)
        
        # Get all jobs
        all_jobs = Job.query.all()
        print(f"Total jobs in database: {len(all_jobs):,}")
        
        # Categorize jobs
        categories = {
            'no_salary': 0,
            'annual_salary': 0,
            'hourly_only': 0,
            'not_specified': 0
        }
        
        sample_jobs = {
            'no_salary': [],
            'annual_salary': [],
            'hourly_only': [],
            'not_specified': []
        }
        
        for job in all_jobs:
            salary_text = job.salary_range
            
            if not salary_text or salary_text.strip().lower() in ['null', 'none', '']:
                categories['no_salary'] += 1
                if len(sample_jobs['no_salary']) < 3:
                    sample_jobs['no_salary'].append(job)
            elif salary_text.strip().lower() in ['not specified']:
                categories['not_specified'] += 1
                if len(sample_jobs['not_specified']) < 3:
                    sample_jobs['not_specified'].append(job)
            elif parser.should_skip_job(salary_text):
                categories['hourly_only'] += 1
                if len(sample_jobs['hourly_only']) < 3:
                    sample_jobs['hourly_only'].append(job)
            else:
                categories['annual_salary'] += 1
                if len(sample_jobs['annual_salary']) < 3:
                    sample_jobs['annual_salary'].append(job)
        
        # Print results
        for category, count in categories.items():
            percentage = (count / len(all_jobs)) * 100
            print(f"\n{category.replace('_', ' ').title()}: {count:,} jobs ({percentage:.1f}%)")
            
            if sample_jobs[category]:
                print("   Sample jobs:")
                for job in sample_jobs[category]:
                    salary_display = job.salary_range[:50] + "..." if job.salary_range and len(job.salary_range) > 50 else job.salary_range
                    print(f"     • {job.title} at {job.company}")
                    print(f"       Salary: {salary_display or 'None'}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up hourly-only jobs from database')
    parser.add_argument('--dry-run', action='store_true', default=True, 
                       help='Analyze without making changes (default)')
    parser.add_argument('--analyze', action='store_true', 
                       help='Just analyze salary data distribution')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually delete hourly-only jobs')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_salary_data()
    elif args.execute:
        cleanup_hourly_jobs(dry_run=False)
    else:
        cleanup_hourly_jobs(dry_run=True)
