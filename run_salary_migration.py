#!/usr/bin/env python3
"""
Simple script to run salary data migration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from salary_parser import SalaryParser
from app import create_app
from models import db, Job

def main():
    print("🚀 Starting salary data standardization...")
    
    app = create_app()
    
    with app.app_context():
        parser = SalaryParser()
        
        # Get all jobs with salary_range data
        jobs_with_salary = Job.query.filter(
            Job.salary_range.isnot(None),
            Job.salary_range != '',
            Job.salary_range != 'NULL'
        ).all()
        
        print(f"📊 Found {len(jobs_with_salary)} jobs with salary data")
        
        if len(jobs_with_salary) == 0:
            print("No jobs with salary data found. Exiting.")
            return
        
        # Show some examples before migration
        print("\n📋 Sample salary data before standardization:")
        for i, job in enumerate(jobs_with_salary[:5]):
            print(f"  {i+1}. {job.title} at {job.company}: '{job.salary_range}'")
        
        # Ask for confirmation
        response = input(f"\n❓ Proceed with standardizing {len(jobs_with_salary)} salary records? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        
        # Process each job
        stats = {
            'processed': 0,
            'standardized': 0,
            'no_salary_found': 0,
            'errors': 0
        }
        
        print(f"\n🔄 Processing {len(jobs_with_salary)} jobs...")
        
        for i, job in enumerate(jobs_with_salary):
            try:
                original_salary = job.salary_range
                standardized = parser.standardize_salary_range(original_salary)
                
                # Update the job record
                job.salary_range = standardized
                
                stats['processed'] += 1
                
                if standardized != "Not specified":
                    stats['standardized'] += 1
                    if i < 10:  # Show first 10 examples
                        print(f"  ✅ {job.title}: '{original_salary}' → '{standardized}'")
                else:
                    stats['no_salary_found'] += 1
                    if i < 10:  # Show first 10 examples
                        print(f"  ⚠️  {job.title}: No salary found in '{original_salary[:50]}...'")
                
            except Exception as e:
                stats['errors'] += 1
                print(f"  ❌ Error processing {job.title}: {e}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Migration completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing changes: {e}")
            return False
        
        # Print final statistics
        print(f"\n📊 Final Statistics:")
        print(f"   Processed: {stats['processed']}")
        print(f"   Standardized: {stats['standardized']}")
        print(f"   No salary found: {stats['no_salary_found']}")
        print(f"   Errors: {stats['errors']}")
        
        # Show some examples after migration
        print(f"\n📋 Sample salary data after standardization:")
        updated_jobs = Job.query.filter(
            Job.salary_range.isnot(None),
            Job.salary_range != '',
            Job.salary_range != 'NULL'
        ).limit(5).all()
        
        for i, job in enumerate(updated_jobs):
            print(f"  {i+1}. {job.title} at {job.company}: '{job.salary_range}'")
        
        return True

if __name__ == "__main__":
    main()

