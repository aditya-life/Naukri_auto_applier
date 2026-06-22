"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

import os
import sys
import time

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

from config.naukri_settings import search_keywords, search_location
from modules.chrome_launcher import driver, wait, actions
from modules.utilities import print_lg, make_directories, initialize_logs_path
from modules.naukri_auth import is_logged_in_naukri, login_naukri, update_resume_on_naukri_profile
from modules.naukri_applier import search_naukri_jobs, run_naukri_loop

def main():
    initialize_logs_path()
    print_lg("\n==================================================")
    print_lg("Naukri Auto Applier started!")
    print_lg("==================================================\n")
    
    try:
        # Check authentication status and log in if necessary
        driver.get("https://www.naukri.com/nlogin/login")
        time.sleep(3)
        if not is_logged_in_naukri():
            print_lg("Not logged in. Starting auto-login flow...")
            login_naukri()
        else:
            print_lg("Already logged in to Naukri.com.")
            
        # Loop through configured job search keywords
        for idx, keyword in enumerate(search_keywords):
            print_lg(f"\n[{idx + 1}/{len(search_keywords)}] Processing search keyword: '{keyword}'...")
            
            # Navigate and search
            search_naukri_jobs(keyword, search_location)
            
            # Execute application loop for this keyword (default: up to 3 pages)
            result = run_naukri_loop(max_pages=3)
            if result == "LIMIT_REACHED":
                print_lg("Stopping main loop as the daily application limit of 50 is reached.")
                break
            
    except Exception as e:
        print_lg("A critical error occurred in main execution flow:", e)
    finally:
        print_lg("\nClosing browser session. Naukri Auto Applier run complete!")
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
