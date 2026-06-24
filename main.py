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

from selenium.webdriver.common.by import By
from config.naukri_settings import search_keywords, search_location, application_mode
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
            
        if application_mode == "recommendation":
            print_lg("\n==================================================")
            print_lg("Running in Recommendation Mode: Applying to home page recommended jobs...")
            print_lg("==================================================\n")
            
            # Navigate to homepage first to ensure logged in
            driver.get("https://www.naukri.com/mnjuser/homepage")
            time.sleep(5)
            
            # Click "View all" to navigate to recommended jobs page
            view_all_element = None
            selectors = [
                "//span[contains(text(), 'Recommended jobs')]/following-sibling::a",
                "//div[contains(@class, 'recommended')]//a[contains(text(), 'View all')]",
                "//a[contains(@href, 'recommend') or contains(@href, 'rec')]",
                "//a[text()='View all']",
                "//span[text()='Recommended jobs for you']/parent::div//a"
            ]
            
            for xpath in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            text = el.text.strip()
                            href = el.get_attribute("href")
                            if "view all" in text.lower() or "recommend" in href.lower() or "rec" in href.lower():
                                view_all_element = el
                                break
                    if view_all_element:
                        break
                except Exception:
                    pass
            
            if view_all_element:
                print_lg(f"Navigating to recommended jobs page via: {view_all_element.get_attribute('href')}...")
                driver.execute_script("arguments[0].click();", view_all_element)
                time.sleep(5)
            else:
                print_lg("Could not find 'View all' link. Navigating directly to recommendedjobs...")
                driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
                time.sleep(5)
            
            # Execute application loop (max_pages=1 handles all visible recommended jobs)
            run_naukri_loop(max_pages=1)
            
        else:
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
