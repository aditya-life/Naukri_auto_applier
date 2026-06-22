"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

import csv
import time
import urllib.parse
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException

from config.naukri_settings import file_name, failed_file_name, click_gap, experience_years
from modules.chrome_launcher import driver, wait, actions
from modules.utilities import print_lg, buffer

# In-memory set of applied job IDs to avoid duplicates
applied_job_ids = set()

def load_applied_history():
    global applied_job_ids
    applied_job_ids.clear()
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    applied_job_ids.add(row[0])
    except FileNotFoundError:
        pass

def save_applied_job(job_id, title, company, job_url, status):
    global applied_job_ids
    applied_job_ids.add(job_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_csv = file_name if status == "Applied" else failed_file_name
    
    try:
        with open(target_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([job_id, title, company, job_url, status, now])
    except Exception as e:
        print_lg(f"Error saving job to csv: {e}")

def search_naukri_jobs(keyword: str, location: str) -> None:
    '''
    Navigates to Naukri search results using formatted query parameters
    '''
    encoded_keyword = urllib.parse.quote(keyword)
    
    if location.strip():
        encoded_location = urllib.parse.quote(location.strip().lower())
        search_url = f"https://www.naukri.com/jobs-in-{encoded_location}?k={encoded_keyword}"
    else:
        search_url = f"https://www.naukri.com/jobs?k={encoded_keyword}"
        
    if experience_years > 0:
        search_url += f"&experience={experience_years}"

    print_lg(f"\n>-> Searching Naukri for '{keyword}' in '{location}' (Exp: {experience_years} years) -> URL: {search_url}")
    driver.get(search_url)
    time.sleep(3)

def apply_to_current_job(job_id, title, company, job_url):
    '''
    Handles direct application inside a job detail page
    '''
    try:
        # Check if the page contains a direct Apply button
        apply_btn = None
        apply_selectors = [
            (By.XPATH, "//button[contains(@class, 'apply') and contains(text(), 'Apply')]"),
            (By.XPATH, "//button[text()='Apply']"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Apply')]"),
            (By.XPATH, "//button[contains(@class, 'btn') and contains(text(), 'Apply')]")
        ]
        
        for by, val in apply_selectors:
            try:
                elements = driver.find_elements(by, val)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        apply_btn = el
                        break
                if apply_btn:
                    break
            except Exception:
                pass
                
        if not apply_btn:
            print_lg(f"No direct Apply button found for: {title}. Skipping or might be external.")
            save_applied_job(job_id, title, company, job_url, "Skipped/External")
            return
            
        btn_text = apply_btn.text.lower()
        if "apply on company" in btn_text or "redirect" in btn_text:
            print_lg(f"External apply link found for: {title}. Skipping external submission.")
            save_applied_job(job_id, title, company, job_url, "External Link")
            return
            
        # Click apply
        apply_btn.click()
        time.sleep(2)
        
        # Check for success indicators or forms
        current_url = driver.current_url.lower()
        if "apply-success" in current_url or "success" in current_url:
            print_lg(f"Direct Apply Success for: {title} | {company}")
            save_applied_job(job_id, title, company, job_url, "Applied")
        else:
            # Check if there is an on-page success message
            success_indicators = [
                "applied successfully",
                "application sent",
                "success"
            ]
            page_text = driver.page_source.lower()
            if any(ind in page_text for ind in success_indicators):
                print_lg(f"Direct Apply Success (text matched) for: {title} | {company}")
                save_applied_job(job_id, title, company, job_url, "Applied")
            else:
                print_lg(f"Applied clicked for {title}, logged as Applied.")
                save_applied_job(job_id, title, company, job_url, "Applied")
                
    except Exception as e:
        print_lg(f"Error applying to job {title}: {e}")
        save_applied_job(job_id, title, company, job_url, "Failed")

def run_naukri_loop(max_pages=5):
    '''
    Iterates through Naukri search result pages and applies to direct jobs
    '''
    load_applied_history()
    original_window = driver.current_window_handle
    
    for page in range(1, max_pages + 1):
        print_lg(f"\n====== Processing Naukri Search Results Page {page} ======")
        time.sleep(2)
        
        # Locate job card elements (using multiple common class names or article tags)
        job_cards = []
        card_selectors = [
            (By.XPATH, "//div[contains(@class, 'srp-job-tuple') or contains(@class, 'srp-jobtuple-wrapper') or contains(@class, 'cust-job-tuple') or contains(@class, 'custTuple')]"),
            (By.XPATH, "//article[contains(@class, 'jobTuple') or contains(@class, 'job-tuple') or contains(@class, 'srp-jobtuple-wrapper')]"),
            (By.XPATH, "//article"),
            (By.XPATH, "//div[contains(@class, 'jobTuple') or contains(@class, 'custTuple')]")
        ]
        
        for by, val in card_selectors:
            try:
                elements = driver.find_elements(by, val)
                if len(elements) > 0:
                    job_cards = elements
                    break
            except Exception:
                pass
                
        print_lg(f"Found {len(job_cards)} job cards on this page.")
        if len(job_cards) == 0:
            print_lg("No job listings found on this page. Stopping search keyword loop.")
            break
            
        # Iterate over cards
        for idx, card in enumerate(job_cards):
            try:
                # Extract Title & Link (with robust fallbacks)
                title_el = None
                for selector in [
                    (By.XPATH, ".//a[contains(@class, 'title') or contains(@class, 'job-title') or contains(@class, 'jobTupleTitle')]"),
                    (By.XPATH, ".//a[contains(@href, '/job-listings')]"),
                    (By.XPATH, ".//a")
                ]:
                    try:
                        title_el = card.find_element(*selector)
                        if title_el:
                            break
                    except Exception:
                        pass
                
                if not title_el:
                    print_lg(f"Could not extract title for card {idx}. Skipping.")
                    continue
                    
                title = title_el.text.strip()
                job_url = title_el.get_attribute("href")
                
                # Extract Company (with robust fallbacks)
                company = "Unknown Company"
                comp_selectors = [
                    (By.XPATH, ".//a[contains(@class, 'comp-name') or contains(@class, 'companyName') or contains(@class, 'compName')]"),
                    (By.XPATH, ".//div[contains(@class, 'comp-name') or contains(@class, 'companyName') or contains(@class, 'compName')]"),
                    (By.XPATH, ".//span[contains(@class, 'companyName')]")
                ]
                for selector in comp_selectors:
                    try:
                        comp_el = card.find_element(*selector)
                        if comp_el:
                            company = comp_el.text.strip()
                            break
                    except Exception:
                        pass
                
                # Derive Unique Job ID from URL
                job_id = None
                if job_url:
                    parts = job_url.split("-")
                    for p in reversed(parts):
                        if p.isdigit():
                            job_id = p
                            break
                    if not job_id:
                        # Fallback to hashing URL
                        job_id = str(hash(job_url) & 0xffffffff)
                else:
                    continue
                    
                if job_id in applied_job_ids:
                    print_lg(f"Job [{idx}]: {title} at {company} (ID: {job_id}) already applied. Skipping.")
                    continue
                    
                print_lg(f"\nJob [{idx}]: Opening details for '{title}' at '{company}'...")
                
                # Open in a new tab to inspect/apply
                driver.execute_script("window.open(arguments[0]);", job_url)
                time.sleep(1)
                
                # Switch to the new tab
                new_window = [w for w in driver.window_handles if w != original_window][0]
                driver.switch_to.window(new_window)
                time.sleep(3) # Wait for job page to load
                
                # Try applying
                apply_to_current_job(job_id, title, company, job_url)
                
                # Close the job tab and switch back
                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(click_gap)
                
            except Exception as e:
                print_lg(f"Skipping job card {idx} due to error: {e}")
                try:
                    # Make sure we close any open secondary tabs
                    for w in driver.window_handles:
                        if w != original_window:
                            driver.switch_to.window(w)
                            driver.close()
                    driver.switch_to.window(original_window)
                except Exception:
                    pass
                    
        # Navigate to Next Page
        try:
            print_lg("Searching for pagination 'Next' button...")
            next_btn = None
            next_selectors = [
                (By.XPATH, "//a[contains(@class, 'next') or contains(text(), 'Next')]"),
                (By.XPATH, "//span[contains(text(), 'Next')]"),
                (By.XPATH, "//button[contains(., 'Next')]")
            ]
            for by, val in next_selectors:
                try:
                    btn = driver.find_element(by, val)
                    if btn.is_displayed() and btn.is_enabled():
                        next_btn = btn
                        break
                except Exception:
                    pass
                    
            if next_btn:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(1)
                next_btn.click()
                print_lg("Successfully clicked Next page button.")
                time.sleep(3)
            else:
                print_lg("Could not locate active 'Next' button. Pagination ended.")
                break
        except Exception as e:
            print_lg(f"Error navigating to next page: {e}")
            break
