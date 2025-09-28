#!/usr/bin/env python3
"""
Phase 1: Delete non-full-time jobs from database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from sqlalchemy import func

def cleanup_non_fulltime_jobs():
    """Delete all jobs that are explicitly not full-time"""
    app = create_app()
    
    with app.app_context():
        print("🧹 PHASE 1: CLEANING UP NON-FULL-TIME JOBS")
        print("=" * 60)
        
        # Get current total using raw SQL
        total_before = db.session.execute(db.text("SELECT COUNT(*) FROM jobs")).scalar()
        print(f"📊 Total jobs before cleanup: {total_before:,}")
        
        # Define non-full-time employment types to delete
        non_fulltime_patterns = [
            # Explicit non-full-time types
            "Remote /",
            "Contract",
            "International EOR /", 
            "Contract /",
            "Part Time /",
            "Fixed Term /",
            "Part time",
            "International Office Entity /",
            "Intern /",
            "Temporary /",
            "Internship /",
            "Sales /",
            "Part - Time /"
        ]
        
        deleted_count = 0
        
        # Delete jobs with explicit non-full-time types
        for pattern in non_fulltime_patterns:
            count = db.session.execute(db.text(
                "SELECT COUNT(*) FROM jobs WHERE employment_type = :pattern"
            ), {'pattern': pattern}).scalar()
            
            if count > 0:
                print(f"   🗑️  Deleting {count:,} jobs with employment_type: '{pattern}'")
                db.session.execute(db.text(
                    "DELETE FROM jobs WHERE employment_type = :pattern"
                ), {'pattern': pattern})
                deleted_count += count
        
        # Delete jobs with keyword patterns (case insensitive)
        keyword_patterns = [
            ("part%", "part"),
            ("contract%", "contract"), 
            ("temp%", "temp"),
            ("intern%", "intern")
        ]
        
        for pattern, keyword in keyword_patterns:
            count = db.session.execute(db.text(
                "SELECT COUNT(*) FROM jobs WHERE employment_type ILIKE :pattern"
            ), {'pattern': pattern}).scalar()
            
            if count > 0:
                print(f"   🗑️  Deleting {count:,} jobs matching pattern: '{keyword}%'")
                db.session.execute(db.text(
                    "DELETE FROM jobs WHERE employment_type ILIKE :pattern"
                ), {'pattern': pattern})
                deleted_count += count
        
        # Commit the deletions
        db.session.commit()
        
        # Get final count
        total_after = db.session.execute(db.text("SELECT COUNT(*) FROM jobs")).scalar()
        
        print(f"\n📊 CLEANUP RESULTS:")
        print(f"   Jobs deleted: {deleted_count:,}")
        print(f"   Total jobs before: {total_before:,}")
        print(f"   Total jobs after: {total_after:,}")
        print(f"   Reduction: {total_before - total_after:,} jobs")
        
        return deleted_count

if __name__ == "__main__":
    cleanup_non_fulltime_jobs()
