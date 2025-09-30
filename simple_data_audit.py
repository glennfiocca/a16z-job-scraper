#!/usr/bin/env python3
"""
Simple data quality audit to identify massive data gaps
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from sqlalchemy import func

def analyze_data_gaps():
    """Analyze data quality across different dimensions"""
    app = create_app()
    
    with app.app_context():
        print("🔍 DATA QUALITY AUDIT")
        print("=" * 50)
        
        # Get total job count using raw SQL to avoid schema issues
        total_jobs = db.session.execute(db.text("SELECT COUNT(*) FROM jobs")).scalar()
        print(f"📊 Total jobs in database: {total_jobs:,}")
        
        if total_jobs == 0:
            print("❌ No jobs found in database")
            return
        
        # 1. ATS Platform Analysis
        print(f"\n🏢 ATS PLATFORM ANALYSIS")
        print("-" * 40)
        
        ats_platforms = {
            'Greenhouse': db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE url LIKE '%greenhouse%'")).scalar(),
            'Lever': db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE url LIKE '%lever%'")).scalar(),
            'Workday': db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE url LIKE '%workday%'")).scalar(),
            'Ashby': db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE url LIKE '%ashby%'")).scalar(),
            'Stripe': db.session.execute(db.text("SELECT COUNT(*) FROM jobs WHERE url LIKE '%stripe%'")).scalar(),
        }
        
        for platform, count in ats_platforms.items():
            if count > 0:
                percentage = (count / total_jobs) * 100
                print(f"   {platform}: {count:,} jobs ({percentage:.1f}%)")
        
        # 2. Missing Location Analysis by ATS
        print(f"\n📍 MISSING LOCATION ANALYSIS BY ATS")
        print("-" * 50)
        
        for platform, platform_filter in [
            ('Greenhouse', "url LIKE '%greenhouse%'"),
            ('Lever', "url LIKE '%lever%'"),
            ('Workday', "url LIKE '%workday%'"),
            ('Ashby', "url LIKE '%ashby%'"),
            ('Stripe', "url LIKE '%stripe%'")
        ]:
            platform_jobs = db.session.execute(db.text(f"SELECT COUNT(*) FROM jobs WHERE {platform_filter}")).scalar()
            if platform_jobs > 0:
                null_location = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM jobs 
                    WHERE {platform_filter} 
                    AND (location IS NULL OR location = '' OR location = 'NULL')
                """)).scalar()
                
                null_percentage = (null_location / platform_jobs) * 100
                status = "🔴 CRITICAL" if null_percentage > 50 else "🟡 WARNING" if null_percentage > 20 else "✅ GOOD"
                
                print(f"   {platform}: {null_location:,}/{platform_jobs:,} missing ({null_percentage:.1f}%) {status}")
        
        # 3. Missing Company Analysis
        print(f"\n🏢 MISSING COMPANY ANALYSIS")
        print("-" * 40)
        
        null_company = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE company IS NULL OR company = '' OR company = 'NULL' OR company = 'Unknown Company'
        """)).scalar()
        
        null_company_percentage = (null_company / total_jobs) * 100
        print(f"   Missing company: {null_company:,}/{total_jobs:,} ({null_company_percentage:.1f}%)")
        
        # 4. Missing Employment Type Analysis
        print(f"\n⏰ MISSING EMPLOYMENT TYPE ANALYSIS")
        print("-" * 45)
        
        null_employment_type = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE employment_type IS NULL OR employment_type = '' OR employment_type = 'NULL'
        """)).scalar()
        
        null_employment_percentage = (null_employment_type / total_jobs) * 100
        print(f"   Missing employment type: {null_employment_type:,}/{total_jobs:,} ({null_employment_percentage:.1f}%)")
        
        # 5. Missing Description Analysis
        print(f"\n📝 MISSING DESCRIPTION ANALYSIS")
        print("-" * 40)
        
        null_description = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE description IS NULL OR description = '' OR description = 'NULL'
        """)).scalar()
        
        short_description = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE description IS NOT NULL 
            AND description != '' 
            AND description != 'NULL'
            AND LENGTH(description) < 200
        """)).scalar()
        
        null_desc_percentage = (null_description / total_jobs) * 100
        short_desc_percentage = (short_description / total_jobs) * 100
        
        print(f"   Missing description: {null_description:,}/{total_jobs:,} ({null_desc_percentage:.1f}%)")
        print(f"   Short description (<200 chars): {short_description:,}/{total_jobs:,} ({short_desc_percentage:.1f}%)")
        
        # 6. Missing Salary Analysis
        print(f"\n💰 MISSING SALARY ANALYSIS")
        print("-" * 35)
        
        null_salary = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE salary_range IS NULL OR salary_range = '' OR salary_range = 'NULL'
        """)).scalar()
        
        null_salary_percentage = (null_salary / total_jobs) * 100
        print(f"   Missing salary: {null_salary:,}/{total_jobs:,} ({null_salary_percentage:.1f}%)")
        
        # 7. Critical Issues Summary
        print(f"\n🚨 CRITICAL ISSUES SUMMARY")
        print("-" * 35)
        
        critical_issues = []
        
        # Check for ATS platforms with >50% missing location
        for platform, platform_filter in [
            ('Greenhouse', "url LIKE '%greenhouse%'"),
            ('Lever', "url LIKE '%lever%'"),
            ('Workday', "url LIKE '%workday%'"),
            ('Ashby', "url LIKE '%ashby%'"),
            ('Stripe', "url LIKE '%stripe%'")
        ]:
            platform_jobs = db.session.execute(db.text(f"SELECT COUNT(*) FROM jobs WHERE {platform_filter}")).scalar()
            if platform_jobs > 100:  # Only check platforms with significant data
                null_location = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM jobs 
                    WHERE {platform_filter} 
                    AND (location IS NULL OR location = '' OR location = 'NULL')
                """)).scalar()
                
                if null_location > 0:
                    null_percentage = (null_location / platform_jobs) * 100
                    if null_percentage > 50:
                        critical_issues.append(f"🔴 {platform}: {null_percentage:.1f}% missing locations ({null_location:,}/{platform_jobs:,})")
                    elif null_percentage > 20:
                        critical_issues.append(f"🟡 {platform}: {null_percentage:.1f}% missing locations ({null_location:,}/{platform_jobs:,})")
        
        if critical_issues:
            for issue in critical_issues:
                print(f"   {issue}")
        else:
            print("   ✅ No critical data quality issues found!")
        
        # 8. Top Companies Analysis
        print(f"\n🏢 TOP COMPANIES - DATA QUALITY")
        print("-" * 40)
        
        top_companies = db.session.execute(db.text("""
            SELECT company, COUNT(*) as total_jobs
            FROM jobs 
            WHERE company IS NOT NULL 
            AND company != '' 
            AND company != 'NULL' 
            AND company != 'Unknown Company'
            GROUP BY company 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        """)).fetchall()
        
        for company, total in top_companies:
            if total > 50:  # Only show companies with significant job counts
                # Count missing data for this company
                missing_loc = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM jobs 
                    WHERE company = :company 
                    AND (location IS NULL OR location = '' OR location = 'NULL')
                """), {'company': company}).scalar()
                
                missing_emp = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM jobs 
                    WHERE company = :company 
                    AND (employment_type IS NULL OR employment_type = '' OR employment_type = 'NULL')
                """), {'company': company}).scalar()
                
                loc_percentage = (missing_loc / total) * 100 if total > 0 else 0
                emp_percentage = (missing_emp / total) * 100 if total > 0 else 0
                
                print(f"   {company}: {total:,} jobs")
                print(f"      Missing location: {missing_loc:,}/{total:,} ({loc_percentage:.1f}%)")
                print(f"      Missing employment type: {missing_emp:,}/{total:,} ({emp_percentage:.1f}%)")
        
        print(f"\n📋 RECOMMENDATIONS")
        print("-" * 25)
        
        if null_company_percentage > 10:
            print("   • Fix company extraction logic")
        if null_employment_percentage > 30:
            print("   • Improve employment type detection")
        if null_desc_percentage > 20:
            print("   • Enhance job description extraction")
        if null_salary_percentage > 80:
            print("   • Implement salary extraction (already in progress)")
        
        return {
            'total_jobs': total_jobs,
            'ats_platforms': ats_platforms,
            'critical_issues': critical_issues
        }

if __name__ == "__main__":
    analyze_data_gaps()


