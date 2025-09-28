#!/usr/bin/env python3
"""
Comprehensive data quality audit to identify all data gaps by company
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from sqlalchemy import func

def analyze_comprehensive_data_gaps():
    """Analyze comprehensive data quality gaps by company"""
    app = create_app()
    
    with app.app_context():
        print("🔍 COMPREHENSIVE DATA QUALITY AUDIT")
        print("=" * 60)
        
        # Get total job count
        total_jobs = db.session.execute(db.text("SELECT COUNT(*) FROM jobs")).scalar()
        print(f"📊 Total jobs in database: {total_jobs:,}")
        
        if total_jobs == 0:
            print("❌ No jobs found in database")
            return
        
        # 1. Overall Data Gaps
        print(f"\n📈 OVERALL DATA GAPS")
        print("-" * 30)
        
        # Location gaps
        missing_location = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE location IS NULL OR location = '' OR location = 'NULL'
        """)).scalar()
        loc_percentage = (missing_location / total_jobs) * 100
        
        
        # Salary gaps
        missing_salary = db.session.execute(db.text("""
            SELECT COUNT(*) FROM jobs 
            WHERE salary_range IS NULL OR salary_range = '' OR salary_range = 'NULL'
        """)).scalar()
        salary_percentage = (missing_salary / total_jobs) * 100
        
        print(f"   Location: {missing_location:,}/{total_jobs:,} missing ({loc_percentage:.1f}%)")
        print(f"   Salary: {missing_salary:,}/{total_jobs:,} missing ({salary_percentage:.1f}%)")
        
        # 2. Company-specific Analysis
        print(f"\n🏢 COMPANY-SPECIFIC DATA GAPS")
        print("-" * 40)
        
        # Get top companies with job counts
        top_companies = db.session.execute(db.text("""
            SELECT company, COUNT(*) as total_jobs
            FROM jobs 
            WHERE company IS NOT NULL 
            AND company != '' 
            AND company != 'NULL' 
            AND company != 'Unknown Company'
            GROUP BY company 
            ORDER BY COUNT(*) DESC 
            LIMIT 15
        """)).fetchall()
        
        company_stats = []
        
        for company, total in top_companies:
            if total >= 50:  # Only analyze companies with 50+ jobs
                # Count missing data for this company
                missing_loc = db.session.execute(db.text("""
                    SELECT COUNT(*) FROM jobs 
                    WHERE company = :company 
                    AND (location IS NULL OR location = '' OR location = 'NULL')
                """), {'company': company}).scalar()
                
                
                missing_sal = db.session.execute(db.text("""
                    SELECT COUNT(*) FROM jobs 
                    WHERE company = :company 
                    AND (salary_range IS NULL OR salary_range = '' OR salary_range = 'NULL')
                """), {'company': company}).scalar()
                
                loc_percentage = (missing_loc / total) * 100 if total > 0 else 0
                sal_percentage = (missing_sal / total) * 100 if total > 0 else 0
                
                company_stats.append({
                    'company': company,
                    'total': total,
                    'missing_location': missing_loc,
                    'missing_salary': missing_sal,
                    'loc_percentage': loc_percentage,
                    'sal_percentage': sal_percentage
                })
        
        # Sort by total jobs for display
        company_stats.sort(key=lambda x: x['total'], reverse=True)
        
        for stats in company_stats:
            company = stats['company']
            total = stats['total']
            missing_loc = stats['missing_location']
            missing_sal = stats['missing_salary']
            loc_pct = stats['loc_percentage']
            sal_pct = stats['sal_percentage']
            
            print(f"\n   {company}: {total:,} jobs")
            print(f"      Location: {missing_loc:,}/{total:,} missing ({loc_pct:.1f}%)")
            print(f"      Salary: {missing_sal:,}/{total:,} missing ({sal_pct:.1f}%)")
        
        # 3. Critical Issues by Category
        print(f"\n🚨 CRITICAL ISSUES BY CATEGORY")
        print("-" * 40)
        
        # Location extraction failures
        print(f"\n📍 LOCATION EXTRACTION FAILURES:")
        loc_failures = [s for s in company_stats if s['loc_percentage'] > 90]
        loc_failures.sort(key=lambda x: x['missing_location'], reverse=True)
        
        for stats in loc_failures[:10]:  # Top 10 worst
            print(f"   {stats['company']}: {stats['missing_location']:,}/{stats['total']:,} missing ({stats['loc_percentage']:.1f}%)")
        
        
        # Salary extraction failures
        print(f"\n💰 SALARY EXTRACTION FAILURES:")
        sal_failures = [s for s in company_stats if s['sal_percentage'] > 90]
        sal_failures.sort(key=lambda x: x['missing_salary'], reverse=True)
        
        for stats in sal_failures[:10]:  # Top 10 worst
            print(f"   {stats['company']}: {stats['missing_salary']:,}/{stats['total']:,} missing ({stats['sal_percentage']:.1f}%)")
        
        # 4. Working Well
        print(f"\n✅ WORKING WELL:")
        print("-" * 20)
        
        # Good location extraction
        good_loc = [s for s in company_stats if s['loc_percentage'] < 5 and s['total'] >= 100]
        if good_loc:
            print(f"   Good Location Extraction:")
            for stats in good_loc:
                print(f"      {stats['company']}: {stats['missing_location']:,}/{stats['total']:,} missing ({stats['loc_percentage']:.1f}%)")
        
        
        # Good salary extraction
        good_sal = [s for s in company_stats if s['sal_percentage'] < 20 and s['total'] >= 100]
        if good_sal:
            print(f"   Good Salary Extraction:")
            for stats in good_sal:
                print(f"      {stats['company']}: {stats['missing_salary']:,}/{stats['total']:,} missing ({stats['sal_percentage']:.1f}%)")
        
        # 5. Priority Recommendations
        print(f"\n🎯 PRIORITY FIXES NEEDED:")
        print("-" * 30)
        
        # Calculate impact scores
        for stats in company_stats:
            # Impact score = (missing_count * company_size_weight) / 1000
            company_weight = min(stats['total'] / 100, 5)  # Cap at 5x weight for large companies
            stats['loc_impact'] = (stats['missing_location'] * company_weight) / 1000
            stats['sal_impact'] = (stats['missing_salary'] * company_weight) / 1000
        
        # Top location issues by impact
        top_loc_issues = sorted([s for s in company_stats if s['loc_percentage'] > 50], 
                              key=lambda x: x['loc_impact'], reverse=True)[:5]
        if top_loc_issues:
            print(f"   1. Location extraction for:")
            for stats in top_loc_issues:
                print(f"      • {stats['company']}: {stats['missing_location']:,} jobs affected")
        
        
        # Top salary issues by impact
        top_sal_issues = sorted([s for s in company_stats if s['sal_percentage'] > 50], 
                              key=lambda x: x['sal_impact'], reverse=True)[:5]
        if top_sal_issues:
            print(f"   2. Salary extraction for:")
            for stats in top_sal_issues:
                print(f"      • {stats['company']}: {stats['missing_salary']:,} jobs affected")
        
        return {
            'total_jobs': total_jobs,
            'overall_gaps': {
                'location': {'missing': missing_location, 'percentage': loc_percentage},
                'salary': {'missing': missing_salary, 'percentage': salary_percentage}
            },
            'company_stats': company_stats
        }

if __name__ == "__main__":
    analyze_comprehensive_data_gaps()
