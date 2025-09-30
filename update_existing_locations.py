#!/usr/bin/env python3
"""
Update existing jobs to parse their locations into primary and alternate locations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from main import parse_locations
from datetime import datetime

def update_existing_locations(limit=100, dry_run=True):
    """
    Find and update existing jobs that have locations that could be parsed into alternate locations
    
    Args:
        limit: Maximum number of jobs to process (for testing)
        dry_run: If True, only show what would be updated without making changes
    """
    app = create_app()
    
    with app.app_context():
        print("🔄 UPDATING EXISTING LOCATIONS")
        print("=" * 50)
        
        # Find jobs that have locations but no alternate_locations
        # Look for jobs with locations that contain common separators
        jobs_to_update = db.session.execute(db.text("""
            SELECT id, url, company, title, location, alternate_locations
            FROM jobs 
            WHERE location IS NOT NULL 
            AND location != '' 
            AND location != 'NULL'
            AND (alternate_locations IS NULL OR alternate_locations = '')
            AND (location LIKE '%;%' 
                 OR location LIKE '%|%' 
                 OR location LIKE '% and %' 
                 OR location LIKE '% or %' 
                 OR location LIKE '% • %' 
                 OR location LIKE '% / %')
            ORDER BY scraped_at DESC
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        print(f"📊 Found {len(jobs_to_update)} jobs with locations but no alternate locations")
        
        if dry_run:
            print(f"🧪 DRY RUN MODE - No changes will be made")
            print(f"📋 Jobs that would be updated:")
            
            for job in jobs_to_update[:20]:  # Show first 20
                # Test parsing the location
                primary, alternate = parse_locations(job.location)
                if alternate:  # Only show jobs that would benefit from parsing
                    print(f"   • {job.company}: {job.title}")
                    print(f"     Current: '{job.location}'")
                    print(f"     Would become: Primary='{primary}', Alternate='{alternate}'")
                    print()
            
            if len(jobs_to_update) > 20:
                print(f"   ... and {len(jobs_to_update) - 20} more")
            return
        
        # Start updating
        print(f"🚀 Starting location parsing process...")
        
        updated_count = 0
        skipped_count = 0
        
        for job in jobs_to_update:
            try:
                # Parse the existing location
                primary, alternate = parse_locations(job.location)
                
                if alternate:  # Only update if parsing would create alternate locations
                    # Update the job with parsed locations
                    db.session.execute(db.text("""
                        UPDATE jobs 
                        SET location = :primary_location, 
                            alternate_locations = :alternate_locations,
                            scraped_at = :scraped_at
                        WHERE id = :job_id
                    """), {
                        'primary_location': primary,
                        'alternate_locations': alternate,
                        'scraped_at': datetime.utcnow(),
                        'job_id': job.id
                    })
                    
                    print(f"   ✅ Updated: {job.company} - {job.title}")
                    print(f"      Primary: '{primary}'")
                    print(f"      Alternate: '{alternate}'")
                    updated_count += 1
                else:
                    print(f"   ⏭️  Skipped: {job.company} - {job.title} (no alternate locations found)")
                    skipped_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error updating {job.company} - {job.title}: {e}")
        
        # Commit all changes
        db.session.commit()
        
        # Summary
        print(f"\n📊 UPDATE SUMMARY")
        print("=" * 30)
        print(f"✅ Successfully updated: {updated_count}")
        print(f"⏭️  Skipped (no alternates): {skipped_count}")
        print(f"📊 Total processed: {updated_count + skipped_count}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update existing job locations to parse alternate locations')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of jobs to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    parser.add_argument('--execute', action='store_true', help='Actually perform the updates (overrides dry-run)')
    
    args = parser.parse_args()
    
    # If --execute is specified, override dry_run
    dry_run = args.dry_run and not args.execute
    
    update_existing_locations(limit=args.limit, dry_run=dry_run)
