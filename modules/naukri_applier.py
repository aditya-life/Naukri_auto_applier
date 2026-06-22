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

import re

def get_today_applied_count():
    count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    status = row[4]
                    date_str = row[5]
                    if status == "Applied" and date_str.startswith(today_str):
                        count += 1
    except FileNotFoundError:
        pass
    return count

def is_experience_suitable(exp_text, user_exp=4):
    if not exp_text:
        return True
    numbers = [int(s) for s in re.findall(r'\d+', exp_text)]
    if len(numbers) == 2:
        min_exp, max_exp = numbers[0], numbers[1]
        if min_exp > user_exp:
            return False
    elif len(numbers) == 1:
        req_exp = numbers[0]
        if req_exp > user_exp:
            return False
    return True

def search_naukri_jobs(keyword: str, location: str) -> None:
    '''
    Navigates to Naukri search results using formatted query parameters sorted by date
    '''
    encoded_keyword = urllib.parse.quote(keyword)
    
    if location.strip():
        encoded_location = urllib.parse.quote(location.strip().lower())
        search_url = f"https://www.naukri.com/jobs-in-{encoded_location}?k={encoded_keyword}"
    else:
        search_url = f"https://www.naukri.com/jobs?k={encoded_keyword}"
        
    if experience_years > 0:
        search_url += f"&experience={experience_years}"
        
    # Sort by date (freshest jobs first)
    search_url += "&sort=dd"

    print_lg(f"\n>-> Searching Naukri for '{keyword}' in '{location}' (Exp: {experience_years} years) -> URL: {search_url}")
    driver.get(search_url)
    time.sleep(3)

def get_question_text(driver, element):
    elem_id = element.get_attribute("id")
    if elem_id:
        try:
            label = driver.find_element(By.XPATH, f"//label[@for='{elem_id}']")
            if label:
                return label.text.strip()
        except Exception:
            pass
            
    try:
        parent = element.find_element(By.XPATH, "./ancestor::*[contains(@class, 'form-group') or contains(@class, 'question') or contains(@class, 'field') or contains(@class, 'row')][1]")
        if parent:
            full_text = parent.text.strip()
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            if lines:
                return lines[0]
    except Exception:
        pass
        
    try:
        preceding = element.find_element(By.XPATH, "./preceding::*[1]")
        if preceding:
            return preceding.text.strip()
    except Exception:
        pass
        
    return ""

def get_answer_for_question(question_text):
    q = question_text.lower()
    
    # Notice Period
    if any(k in q for k in ["notice", "how soon", "joining time", "availability", "join in", "serving"]):
        return "immediate|15 days|0 days|serving"
        
    # Experience (Total / specific skills)
    if any(k in q for k in ["experience", "years of exp", "exp in", "how many years"]):
        if "active directory" in q:
            return "4"
        if "incident" in q:
            return "4"
        if "service desk" in q:
            return "4"
        if "windows server" in q:
            return "4"
        if "outlook" in q:
            return "4"
        if "l1" in q or "l2" in q:
            return "4"
        return "4"
        
    # Salary / CTC
    if "expected" in q and any(k in q for k in ["salary", "ctc", "lpa"]):
        return "500000|5 lakh|5 lpa"
    if "current" in q and any(k in q for k in ["salary", "ctc", "lpa"]):
        return "400000|4 lakh|4 lpa"
    if any(k in q for k in ["salary", "ctc", "lpa"]):
        return "500000|5 lakh|5 lpa"
        
    # Location & Relocation
    if "willing to relocate" in q or "relocate" in q:
        return "yes|agree|accept"
    if "current location" in q or "city" in q:
        return "noida"
    if "preferred location" in q:
        return "noida"
        
    # Education
    if "graduation" in q or "degree" in q or "education" in q:
        return "b.com|bachelor"
    if "university" in q:
        return "deen dayal upadhyaya university"
        
    # Gender
    if "gender" in q:
        return "male"
        
    # Diversity
    if "disability" in q:
        return "no|none"
    if "veteran" in q:
        return "no"
        
    # Yes/No default
    if q.startswith("are you") or q.startswith("do you") or "willing" in q or "confirm" in q:
        return "yes|agree|accept"
        
    return ""

def fill_naukri_questions(driver):
    '''
    Detects and fills dynamic screening forms or chatbot questions on Naukri
    '''
    max_steps = 10
    step = 0
    time.sleep(2) # Wait for potential popup/modal to render
    
    while step < max_steps:
        options_clicked = False
        try:
            choice_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'chat') or contains(@class, 'drawer') or contains(@class, 'modal') or contains(@class, 'Overlay') or contains(@id, 'chat') or contains(@id, 'Overlay')]//*[self::button or self::span or self::label or self::li or self::div[contains(@class, 'option') or contains(@class, 'value') or contains(@class, 'item')]]")
            visible_choices = [el for el in choice_elements if el.is_displayed() and el.is_enabled() and el.text.strip()]
            
            if visible_choices:
                question_text = ""
                try:
                    chat_bubbles = driver.find_elements(By.XPATH, "//div[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'text') or contains(@class, 'question')]")
                    if chat_bubbles:
                        question_text = chat_bubbles[-1].text.strip()
                except Exception:
                    pass
                
                expected_answer = get_answer_for_question(question_text)
                print_lg(f"Chatbot Question: '{question_text}' -> Expected: '{expected_answer}'")
                
                expected_parts = [p.strip().lower() for p in expected_answer.split('|') if p.strip()]
                clicked_choice = None
                for choice in visible_choices:
                    choice_txt = choice.text.strip().lower()
                    if not choice_txt:
                        continue
                    
                    matched = False
                    for part in expected_parts:
                        if part in choice_txt:
                            matched = True
                            break
                            
                    if matched:
                        print_lg(f"Found matching option: '{choice.text}'")
                        driver.execute_script("arguments[0].click();", choice)
                        clicked_choice = choice
                        break
                        
                if not clicked_choice:
                    if len(visible_choices) == 1 or "confirm" in question_text.lower() or "apply" in question_text.lower():
                        driver.execute_script("arguments[0].click();", visible_choices[0])
                        clicked_choice = visible_choices[0]
                        
                if clicked_choice:
                    print_lg(f"Clicked option button: '{clicked_choice.text}'")
                    options_clicked = True
                    time.sleep(2.5)
                    step += 1
                    continue
        except Exception as e:
            print_lg("Error handling chatbot choice buttons:", e)

        inputs_filled = False
        try:
            input_elements = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number' or not(@type)] | //textarea")
            visible_inputs = [el for el in input_elements if el.is_displayed() and el.is_enabled() and el.get_attribute("type") not in ["submit", "button", "hidden", "radio", "checkbox"]]
            
            for inp in visible_inputs:
                question_txt = get_question_text(driver, inp)
                expected_ans = get_answer_for_question(question_txt)
                
                if "ctc" in question_txt.lower() or "salary" in question_txt.lower():
                    if any(k in question_txt.lower() for k in ["lakh", "lpa", "lacs"]):
                        expected_ans = "5" if "expected" in question_txt.lower() else "4"
                
                print_lg(f"Form Question: '{question_txt}' -> Answer: '{expected_ans}'")
                if expected_ans:
                    try:
                        inp.click()
                    except Exception:
                        pass
                    inp.clear()
                    inp.send_keys(expected_ans)
                    inputs_filled = True
                    
            select_elements = driver.find_elements(By.XPATH, "//select")
            visible_selects = [el for el in select_elements if el.is_displayed() and el.is_enabled()]
            for sel in visible_selects:
                question_txt = get_question_text(driver, sel)
                expected_ans = get_answer_for_question(question_txt)
                
                from selenium.webdriver.support.ui import Select
                select = Select(sel)
                best_option = None
                for opt in select.options:
                    if expected_ans.lower() in opt.text.lower():
                        best_option = opt
                        break
                if best_option:
                    select.select_by_visible_text(best_option.text)
                    inputs_filled = True
                    print_lg(f"Selected dropdown option: '{best_option.text}' for '{question_txt}'")
                    
        except Exception as e:
            print_lg("Error handling form inputs:", e)
            
        if inputs_filled or options_clicked:
            try:
                submit_selectors = [
                    (By.XPATH, "//*[contains(@class, 'chat') or contains(@class, 'drawer') or contains(@class, 'modal') or contains(@class, 'Overlay') or contains(@id, 'chat')]//button[contains(normalize-space(.), 'Save') or contains(normalize-space(.), 'Submit') or contains(normalize-space(.), 'Continue') or contains(normalize-space(.), 'Send') or contains(normalize-space(.), 'Apply')]"),
                    (By.XPATH, "//button[contains(@class, 'submit') or contains(@class, 'continue') or contains(text(), 'Submit') or contains(text(), 'Continue') or contains(text(), 'Apply') or contains(text(), 'Save')]"),
                    (By.XPATH, "//input[@type='submit' or @value='Submit' or @value='Continue']"),
                    (By.XPATH, "//button[contains(., 'Send') or contains(., 'Submit') or contains(., 'Apply')]")
                ]
                submit_btn = None
                for by, val in submit_selectors:
                    try:
                        elements = driver.find_elements(by, val)
                        for el in elements:
                            if el.is_displayed() and el.is_enabled():
                                submit_btn = el
                                break
                        if submit_btn:
                            break
                    except Exception:
                        pass
                if submit_btn:
                    print_lg(f"Clicking form submit/continue button: '{submit_btn.text}'")
                    driver.execute_script("arguments[0].click();", submit_btn)
                    time.sleep(3)
                    step += 1
                    continue
            except Exception as e:
                print_lg("Error clicking submit button:", e)
                
        break

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
        
        # Check if screening questions/form/chatbot appears (if URL didn't change to success or no success text)
        current_url = driver.current_url.lower()
        success_indicators = ["apply-success", "success"]
        page_text = driver.page_source.lower()
        
        has_immediate_success = any(ind in current_url for ind in success_indicators) or any(ind in page_text for ind in ["applied successfully", "application sent"])
        
        if not has_immediate_success:
            print_lg("Checking for screening questions or chatbot form...")
            fill_naukri_questions(driver)
            
        # Re-check success status after form submission
        time.sleep(2)
        current_url = driver.current_url.lower()
        page_text = driver.page_source.lower()
        
        if any(ind in current_url for ind in success_indicators) or any(ind in page_text for ind in ["applied successfully", "application sent", "success"]):
            print_lg(f"Direct Apply Success for: {title} | {company}")
            save_applied_job(job_id, title, company, job_url, "Applied")
        else:
            print_lg(f"Applied clicked and form processed for {title}, logged as Applied.")
            save_applied_job(job_id, title, company, job_url, "Applied")
                
    except Exception as e:
        print_lg(f"Error applying to job {title}: {e}")
        save_applied_job(job_id, title, company, job_url, "Failed")

def run_naukri_loop(max_pages=5):
    '''
    Iterates through Naukri search result pages and applies to direct jobs
    '''
    load_applied_history()
    
    # Check daily limit at the start
    today_applied = get_today_applied_count()
    if today_applied >= 50:
        print_lg(f"Daily application limit (50 applications) reached. Current count: {today_applied}. Stopping auto-applier.")
        return "LIMIT_REACHED"
        
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
            # Check daily limit inside loop
            today_applied = get_today_applied_count()
            if today_applied >= 50:
                print_lg(f"Daily application limit (50 applications) reached during loop. Current count: {today_applied}. Stopping auto-applier.")
                return "LIMIT_REACHED"
                
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
                    
                # Extract and validate Experience Required
                exp_text = ""
                for selector in [
                    (By.XPATH, ".//span[contains(@class, 'exp')]"),
                    (By.XPATH, ".//li[contains(@class, 'exp')]"),
                    (By.XPATH, ".//span[contains(@class, 'experience')]"),
                    (By.XPATH, ".//li[contains(@class, 'experience')]")
                ]:
                    try:
                        exp_el = card.find_element(*selector)
                        if exp_el:
                            exp_text = exp_el.text.strip()
                            break
                    except Exception:
                        pass
                        
                if exp_text:
                    if not is_experience_suitable(exp_text, experience_years):
                        print_lg(f"Job [{idx}]: Skipping '{title}' at '{company}' (Exp Req: {exp_text}) because it exceeds your profile ({experience_years} years).")
                        continue
                    
                print_lg(f"\nJob [{idx}]: Opening details for '{title}' at '{company}' (Exp Req: {exp_text})...")
                
                # Open in a new tab using Selenium 4 native new_window to bypass popup blockers
                handles_before = driver.window_handles
                driver.switch_to.new_window('tab')
                time.sleep(1)
                
                # Explicitly switch to the new window handle to guarantee focus
                handles_after = driver.window_handles
                new_handles = [h for h in handles_after if h not in handles_before]
                if new_handles:
                    driver.switch_to.window(new_handles[0])
                else:
                    try:
                        driver.switch_to.window(driver.window_handles[-1])
                    except Exception:
                        pass
                
                driver.get(job_url)
                time.sleep(3) # Wait for job page to load
                
                # Try applying
                apply_to_current_job(job_id, title, company, job_url)
                
                # Close the job tab and switch back, ensuring we never close original_window
                try:
                    if driver.current_window_handle != original_window:
                        driver.close()
                except Exception:
                    pass
                try:
                    driver.switch_to.window(original_window)
                except Exception:
                    pass
                time.sleep(click_gap)
                
            except Exception as e:
                print_lg(f"Skipping job card {idx} due to error: {e}")
                try:
                    # Switch back to original window first to restore valid active focus
                    driver.switch_to.window(original_window)
                except Exception:
                    pass
                try:
                    # Make sure we close any open secondary tabs
                    for w in driver.window_handles:
                        if w != original_window:
                            driver.switch_to.window(w)
                            driver.close()
                except Exception:
                    pass
                try:
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
