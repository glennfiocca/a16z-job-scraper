#!/usr/bin/env python3
"""
Delete all Rappi jobs from the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def delete_rappi_jobs():
    """Delete all Rappi jobs from the database"""
    app = create_app()
    
    with app.app_context():
        print("🗑️  DELETING RAPPI JOBS")
        print("=" * 50)
        
        # Get current Rappi job count
        rappi_count = db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE company = 'Rappi'")).scalar()
        print(f"📊 Found {rappi_count:,} Rappi jobs in database")
        
        if rappi_count == 0:
            print("✅ No Rappi jobs found - nothing to delete")
            return
        
        # Show some sample Rappi jobs before deletion
        print(f"\n📋 Sample Rappi jobs to be deleted:")
        sample_jobs = db.session.execute(db.text("""
            SELECT title, location, url 
            FROM jobs 
            WHERE company = 'Rappi' 
            LIMIT 5
        """)).fetchall()
        
        for title, location, url in sample_jobs:
            print(f"   • {title} - {location or 'No location'}")
            print(f"     URL: {url}")
        
        # Delete all Rappi jobs
        deleted_count = db.session.execute(db.text("DELETE FROM jobs WHERE company = 'Rappi'")).rowcount
        
        # Commit the deletion
        db.session.commit()
        
        print(f"\n📊 DELETION RESULTS:")
        print(f"   Rappi jobs deleted: {deleted_count:,}")
        print(f"   Remaining jobs in database: {db.session.execute(db.text('SELECT COUNT(*) FROM jobs')).scalar():,}")
        
        # Verify deletion
        remaining_rappi = db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE company = 'Rappi'")).scalar()
        if remaining_rappi == 0:
            print(f"✅ SUCCESS: All Rappi jobs have been deleted!")
        else:
            print(f"⚠️  WARNING: {remaining_rappi} Rappi jobs still remain")
        
        return deleted_count

if __name__ == "__main__":
    delete_rappi_jobs()
