#!/usr/bin/env python3
"""
Comprehensive data quality audit to identify massive data gaps
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from sqlalchemy import func, case

def analyze_data_gaps():
    """Analyze data quality across different dimensions"""
    app = create_app()
    
    with app.app_context():
        print("🔍 COMPREHENSIVE DATA QUALITY AUDIT")
        print("=" * 60)
        
        # Get total job count
        total_jobs = Job.query.count()
        print(f"📊 Total jobs in database: {total_jobs:,}")
        
        if total_jobs == 0:
            print("❌ No jobs found in database")
            return
        
        # 1. ATS Platform Analysis
        print(f"\n🏢 ATS PLATFORM ANALYSIS")
        print("-" * 40)
        
        ats_platforms = {
            'Greenhouse': Job.query.filter(Job.url.like('%greenhouse%')).count(),
            'Lever': Job.query.filter(Job.url.like('%lever%')).count(),
            'Workday': Job.query.filter(Job.url.like('%workday%')).count(),
            'Ashby': Job.query.filter(Job.url.like('%ashby%')).count(),
            'Stripe': Job.query.filter(Job.url.like('%stripe%')).count(),
            'Other': Job.query.filter(
                ~Job.url.like('%greenhouse%') & 
                ~Job.url.like('%lever%') & 
                ~Job.url.like('%workday%') & 
                ~Job.url.like('%ashby%') & 
                ~Job.url.like('%stripe%')
            ).count()
        }
        
        for platform, count in ats_platforms.items():
            if count > 0:
                percentage = (count / total_jobs) * 100
                print(f"   {platform}: {count:,} jobs ({percentage:.1f}%)")
        
        # 2. Missing Location Analysis by ATS
        print(f"\n📍 MISSING LOCATION ANALYSIS BY ATS")
        print("-" * 50)
        
        for platform, platform_filter in [
            ('Greenhouse', Job.url.like('%greenhouse%')),
            ('Lever', Job.url.like('%lever%')),
            ('Workday', Job.url.like('%workday%')),
            ('Ashby', Job.url.like('%ashby%')),
            ('Stripe', Job.url.like('%stripe%'))
        ]:
            platform_jobs = Job.query.filter(platform_filter).count()
            if platform_jobs > 0:
                null_location = Job.query.filter(
                    platform_filter & 
                    (Job.location.is_(None) | (Job.location == '') | (Job.location == 'NULL'))
                ).count()
                
                null_percentage = (null_location / platform_jobs) * 100
                status = "🔴 CRITICAL" if null_percentage > 50 else "🟡 WARNING" if null_percentage > 20 else "✅ GOOD"
                
                print(f"   {platform}: {null_location:,}/{platform_jobs:,} missing ({null_percentage:.1f}%) {status}")
        
        # 3. Missing Company Analysis
        print(f"\n🏢 MISSING COMPANY ANALYSIS")
        print("-" * 40)
        
        null_company = Job.query.filter(
            Job.company.is_(None) | (Job.company == '') | (Job.company == 'NULL') | (Job.company == 'Unknown Company')
        ).count()
        
        null_company_percentage = (null_company / total_jobs) * 100
        print(f"   Missing company: {null_company:,}/{total_jobs:,} ({null_company_percentage:.1f}%)")
        
        # 4. Missing Employment Type Analysis
        print(f"\n⏰ MISSING EMPLOYMENT TYPE ANALYSIS")
        print("-" * 45)
        
        null_employment_type = Job.query.filter(
            Job.employment_type.is_(None) | (Job.employment_type == '') | (Job.employment_type == 'NULL')
        ).count()
        
        null_employment_percentage = (null_employment_type / total_jobs) * 100
        print(f"   Missing employment type: {null_employment_type:,}/{total_jobs:,} ({null_employment_percentage:.1f}%)")
        
        # 5. Missing Description Analysis
        print(f"\n📝 MISSING DESCRIPTION ANALYSIS")
        print("-" * 40)
        
        null_description = Job.query.filter(
            Job.description.is_(None) | (Job.description == '') | (Job.description == 'NULL')
        ).count()
        
        short_description = Job.query.filter(
            Job.description.isnot(None) & 
            (Job.description != '') & 
            (Job.description != 'NULL') &
            (func.length(Job.description) < 200)
        ).count()
        
        null_desc_percentage = (null_description / total_jobs) * 100
        short_desc_percentage = (short_description / total_jobs) * 100
        
        print(f"   Missing description: {null_description:,}/{total_jobs:,} ({null_desc_percentage:.1f}%)")
        print(f"   Short description (<200 chars): {short_description:,}/{total_jobs:,} ({short_desc_percentage:.1f}%)")
        
        # 6. Missing Salary Analysis
        print(f"\n💰 MISSING SALARY ANALYSIS")
        print("-" * 35)
        
        null_salary = Job.query.filter(
            Job.salary_range.is_(None) | (Job.salary_range == '') | (Job.salary_range == 'NULL')
        ).count()
        
        null_salary_percentage = (null_salary / total_jobs) * 100
        print(f"   Missing salary: {null_salary:,}/{total_jobs:,} ({null_salary_percentage:.1f}%)")
        
        # 7. Company-specific Analysis
        print(f"\n🏢 TOP COMPANIES - DATA QUALITY")
        print("-" * 40)
        
        # Get top companies by job count
        top_companies = db.session.query(Job.company, func.count(Job.id).label('total_jobs')).filter(
            Job.company.isnot(None) & 
            (Job.company != '') & 
            (Job.company != 'NULL') & 
            (Job.company != 'Unknown Company')
        ).group_by(Job.company).order_by(func.count(Job.id).desc()).limit(10).all()
        
        for company, total in top_companies:
            if total > 50:  # Only show companies with significant job counts
                # Count missing data for this company
                company_jobs = Job.query.filter(Job.company == company)
                
                missing_loc = company_jobs.filter(
                    Job.location.is_(None) | (Job.location == '') | (Job.location == 'NULL')
                ).count()
                
                missing_emp = company_jobs.filter(
                    Job.employment_type.is_(None) | (Job.employment_type == '') | (Job.employment_type == 'NULL')
                ).count()
                
                loc_percentage = (missing_loc / total) * 100 if total > 0 else 0
                emp_percentage = (missing_emp / total) * 100 if total > 0 else 0
                
                print(f"   {company}: {total:,} jobs")
                print(f"      Missing location: {missing_loc:,}/{total:,} ({loc_percentage:.1f}%)")
                print(f"      Missing employment type: {missing_emp:,}/{total:,} ({emp_percentage:.1f}%)")
        
        # 8. Critical Issues Summary
        print(f"\n🚨 CRITICAL ISSUES SUMMARY")
        print("-" * 35)
        
        critical_issues = []
        
        # Check for ATS platforms with >50% missing location
        for platform, platform_filter in [
            ('Greenhouse', Job.url.like('%greenhouse%')),
            ('Lever', Job.url.like('%lever%')),
            ('Workday', Job.url.like('%workday%')),
            ('Ashby', Job.url.like('%ashby%')),
            ('Stripe', Job.url.like('%stripe%'))
        ]:
            platform_jobs = Job.query.filter(platform_filter).count()
            if platform_jobs > 100:  # Only check platforms with significant data
                null_location = Job.query.filter(
                    platform_filter & 
                    (Job.location.is_(None) | (Job.location == '') | (Job.location == 'NULL'))
                ).count()
                
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
