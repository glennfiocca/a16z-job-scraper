#!/usr/bin/env python3
"""
Phase 2: Standardize all employment types to "Full time"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def standardize_employment_type():
    """Standardize all employment types to 'Full time'"""
    app = create_app()
    
    with app.app_context():
        print("🔄 PHASE 2: STANDARDIZING EMPLOYMENT TYPES")
        print("=" * 60)
        
        # Get current employment type distribution
        print("📊 Current employment type distribution:")
        emp_types = db.session.execute(db.text("""
            SELECT employment_type, COUNT(*) as count
            FROM jobs 
            WHERE employment_type IS NOT NULL 
            AND employment_type != ''
            AND employment_type != 'NULL'
            GROUP BY employment_type 
            ORDER BY COUNT(*) DESC
        """)).fetchall()
        
        for emp_type, count in emp_types:
            print(f"   {emp_type}: {count:,} jobs")
        
        # Count NULL values
        null_count = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE employment_type IS NULL 
            OR employment_type = '' 
            OR employment_type = 'NULL'
        """)).scalar()
        print(f"   NULL/Empty: {null_count:,} jobs")
        
        print(f"\n🔄 Standardizing all to 'Full time'...")
        
        # Update all existing employment types to "Full time"
        updated_existing = db.session.execute(db.text("""
            UPDATE jobs 
            SET employment_type = 'Full time'
            WHERE employment_type IS NOT NULL 
            AND employment_type != ''
            AND employment_type != 'NULL'
        """)).rowcount
        
        # Update NULL values to "Full time"
        updated_null = db.session.execute(db.text("""
            UPDATE jobs 
            SET employment_type = 'Full time'
            WHERE employment_type IS NULL 
            OR employment_type = '' 
            OR employment_type = 'NULL'
        """)).rowcount
        
        # Commit changes
        db.session.commit()
        
        print(f"   ✅ Updated {updated_existing:,} existing employment types")
        print(f"   ✅ Updated {updated_null:,} NULL/empty employment types")
        print(f"   📊 Total jobs updated: {updated_existing + updated_null:,}")
        
        # Verify the results
        print(f"\n📊 Final employment type distribution:")
        final_count = db.session.execute(db.text("""
            SELECT employment_type, COUNT(*) as count
            FROM jobs 
            GROUP BY employment_type 
            ORDER BY COUNT(*) DESC
        """)).fetchall()
        
        for emp_type, count in final_count:
            print(f"   {emp_type}: {count:,} jobs")
        
        return updated_existing + updated_null

if __name__ == "__main__":
    standardize_employment_type()

