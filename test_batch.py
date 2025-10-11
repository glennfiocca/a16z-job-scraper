#!/usr/bin/env python3
"""
Test script for batch processing functionality
"""

import subprocess
import sys
import os

def test_batch_processing():
    """Test the batch processing with different configurations"""
    
    print("🧪 Testing A16Z Jobs Scraper Batch Processing")
    print("=" * 50)
    
    # Test configurations
    test_configs = [
        {"batch_size": 5, "resume": True, "description": "Small batch, resume enabled"},
        {"batch_size": 10, "resume": False, "description": "Medium batch, fresh start"},
        {"batch_size": 3, "resume": True, "description": "Very small batch, resume enabled"},
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n🔬 Test {i}: {config['description']}")
        print(f"   Batch size: {config['batch_size']}")
        print(f"   Resume: {config['resume']}")
        print("-" * 30)
        
        try:
            # Run the scraper with test configuration
            cmd = [
                sys.executable, "main.py", 
                str(config['batch_size']), 
                str(config['resume']).lower()
            ]
            
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Test completed successfully")
                print("Output preview:")
                # Show last few lines of output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-5:]:
                    print(f"   {line}")
            else:
                print("❌ Test failed")
                print("Error output:")
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out (5 minutes)")
        except Exception as e:
            print(f"❌ Test error: {e}")
        
        print()
    
    print("🎯 Batch processing tests completed!")
    print("\nTo run the scraper manually:")
    print("  python main.py [batch_size] [resume]")
    print("\nExamples:")
    print("  python main.py 20 true    # Process 20 companies, resume from last position")
    print("  python main.py 10 false   # Process 10 companies, start from beginning")
    print("  python main.py            # Use default settings (20 companies, resume enabled)")

if __name__ == "__main__":
    test_batch_processing()
