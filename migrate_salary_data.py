#!/usr/bin/env python3
"""
Salary Range Standardization Migration Script
Standardizes salary_range field in the jobs database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from salary_parser import SalaryParser
from app import create_app
from models import db, Job
from sqlalchemy import text

def migrate_salary_data():
    """Migrate and standardize salary data"""
    app = create_app()
    
    with app.app_context():
        parser = SalaryParser()
        
        # Get all jobs with salary_range data
        jobs_with_salary = Job.query.filter(
            Job.salary_range.isnot(None),
            Job.salary_range != '',
            Job.salary_range != 'NULL'
        ).all()
        
        print(f"Found {len(jobs_with_salary)} jobs with salary data")
        
        # Statistics tracking
        stats = {
            'processed': 0,
            'standardized': 0,
            'no_salary_found': 0,
            'errors': 0
        }
        
        for job in jobs_with_salary:
            try:
                original_salary = job.salary_range
                
                # Parse and standardize
                standardized = parser.standardize_salary_range(original_salary)
                
                # Update the job record
                job.salary_range = standardized
                
                stats['processed'] += 1
                
                if standardized != "Not specified":
                    stats['standardized'] += 1
                    print(f"✅ {job.title} at {job.company}: {original_salary} → {standardized}")
                else:
                    stats['no_salary_found'] += 1
                    print(f"⚠️  {job.title} at {job.company}: No salary found in '{original_salary[:50]}...'")
                
            except Exception as e:
                stats['errors'] += 1
                print(f"❌ Error processing {job.title}: {e}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Migration completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing changes: {e}")
            return False
        
        # Print statistics
        print(f"\n📊 Migration Statistics:")
        print(f"   Processed: {stats['processed']}")
        print(f"   Standardized: {stats['standardized']}")
        print(f"   No salary found: {stats['no_salary_found']}")
        print(f"   Errors: {stats['errors']}")
        
        return True

def add_salary_columns():
    """Add new standardized salary columns to the database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Add new columns for standardized salary data
            db.engine.execute(text("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS salary_min INTEGER,
                ADD COLUMN IF NOT EXISTS salary_max INTEGER,
                ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(10) DEFAULT 'USD',
                ADD COLUMN IF NOT EXISTS salary_period VARCHAR(20) DEFAULT 'yearly',
                ADD COLUMN IF NOT EXISTS salary_standardized BOOLEAN DEFAULT FALSE
            """))
            
            print("✅ Added standardized salary columns")
            return True
            
        except Exception as e:
            print(f"❌ Error adding columns: {e}")
            return False

def populate_standardized_salary():
    """Populate the new standardized salary columns"""
    app = create_app()
    
    with app.app_context():
        parser = SalaryParser()
        
        # Get all jobs
        jobs = Job.query.all()
        
        for job in jobs:
            if job.salary_range and job.salary_range != 'NULL':
                salary_data = parser.parse_salary(job.salary_range)
                
                # Update standardized columns
                job.salary_min = salary_data.min_salary
                job.salary_max = salary_data.max_salary
                job.salary_currency = salary_data.currency
                job.salary_period = salary_data.period
                job.salary_standardized = True
        
        try:
            db.session.commit()
            print("✅ Populated standardized salary columns")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error populating columns: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Starting salary data standardization...")
    
    # Step 1: Test the parser
    print("\n1. Testing salary parser...")
    from salary_parser import test_salary_parser
    test_salary_parser()
    
    # Step 2: Add new columns
    print("\n2. Adding standardized salary columns...")
    if add_salary_columns():
        # Step 3: Migrate existing data
        print("\n3. Migrating existing salary data...")
        if migrate_salary_data():
            # Step 4: Populate standardized columns
            print("\n4. Populating standardized salary columns...")
            populate_standardized_salary()
            print("\n🎉 Salary standardization complete!")
        else:
            print("\n❌ Migration failed")
    else:
        print("\n❌ Failed to add columns")
