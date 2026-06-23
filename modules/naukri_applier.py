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

from config.naukri_settings import (
    file_name, failed_file_name, click_gap, experience_years,
    enable_resume_matching, resume_match_threshold, resume_keywords, resume_raw_text,
    use_naukri_official_match, require_keyskills_match, require_experience_match, require_location_match
)
from modules.chrome_launcher import driver, wait, actions
from modules.utilities import print_lg, buffer

# Import default_resume_path from config.personal if available
try:
    from config.personal import default_resume_path
except ImportError:
    default_resume_path = ""

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
    if status == "Applied":
        applied_job_ids.add(job_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_csv = file_name if status == "Applied" else failed_file_name
    consolidated_csv = "all excels/naukri_all_applications_track.csv"
    
    try:
        with open(target_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([job_id, title, company, job_url, status, now])
    except Exception as e:
        print_lg(f"Error saving job to specific csv: {e}")

    try:
        import os
        write_header = not os.path.exists(consolidated_csv) or os.path.getsize(consolidated_csv) == 0
        with open(consolidated_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["Job ID", "Job Title", "Company", "Job URL", "Status", "Timestamp"])
            writer.writerow([job_id, title, company, job_url, status, now])
    except Exception as e:
        print_lg(f"Error saving job to consolidated csv: {e}")

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

def extract_text_from_pdf(pdf_path):
    """
    Extracts raw text content from a PDF file using pypdf or PyPDF2 if installed.
    """
    try:
        import os
        if not os.path.exists(pdf_path):
            return None
            
        # Try pypdf first (modern standard)
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            if text.strip():
                return text.strip()
        except ImportError:
            pass
            
        # Try PyPDF2 as fallback
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            if text.strip():
                return text.strip()
        except ImportError:
            pass
    except Exception as e:
        print_lg(f"Error reading PDF {pdf_path}: {e}")
    return None

cached_resume_text = None

def get_resume_text():
    """
    Retrieves the resume text. Attempts to parse the PDF file at default_resume_path first.
    Falls back to resume_raw_text configured in settings if PDF parsing fails or is unconfigured.
    """
    global cached_resume_text
    if cached_resume_text is not None:
        return cached_resume_text
        
    try:
        import os
        if default_resume_path and not default_resume_path.startswith("/path/to") and os.path.exists(default_resume_path):
            print_lg(f"Parsing PDF resume from path: {default_resume_path}")
            pdf_text = extract_text_from_pdf(default_resume_path)
            if pdf_text:
                print_lg("Successfully extracted text from PDF resume.")
                cached_resume_text = pdf_text
                return cached_resume_text
            else:
                print_lg("PDF extraction returned empty text. Falling back to raw resume text.")
    except Exception as e:
        print_lg(f"Could not parse PDF resume: {e}. Using raw resume text.")
        
    print_lg("Using raw resume text from config/naukri_settings.py.")
    cached_resume_text = resume_raw_text
    return cached_resume_text

def calculate_cosine_similarity(text1, text2):
    """
    Calculates term-frequency cosine similarity between two texts.
    Uses basic tokenization and removes standard English stop words.
    """
    stop_words = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
        'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
        'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
        'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
        'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
        'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
        "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
        'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
        'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
        'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"
    }

    def get_words(text):
        words = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]

    words1 = get_words(text1)
    words2 = get_words(text2)

    if not words1 or not words2:
        return 0.0

    freq1 = {}
    for w in words1:
        freq1[w] = freq1.get(w, 0) + 1

    freq2 = {}
    for w in words2:
        freq2[w] = freq2.get(w, 0) + 1

    vocab = set(freq1.keys()) | set(freq2.keys())

    dot_product = 0.0
    mag1 = 0.0
    mag2 = 0.0

    for w in vocab:
        val1 = freq1.get(w, 0)
        val2 = freq2.get(w, 0)
        dot_product += val1 * val2
        mag1 += val1 * val1
        mag2 += val2 * val2

    if mag1 == 0 or mag2 == 0:
        return 0.0

    import math
    return dot_product / (math.sqrt(mag1) * math.sqrt(mag2))

def calculate_keyword_match_ratio(jd_text, keywords):
    """
    Calculates the ratio of configured keywords found in the job description.
    """
    if not keywords:
        return None
        
    jd_lower = jd_text.lower()
    matched_count = 0
    for kw in keywords:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, jd_lower):
            matched_count += 1
    return matched_count / len(keywords)

def check_job_suitability(jd_text, resume_text, keywords, threshold):
    """
    Evaluates suitability by combining keyword-matching and term-frequency cosine similarity.
    Returns: (is_suitable, combined_score_percentage, keyword_score_percentage, cosine_score_percentage)
    """
    if not jd_text or not resume_text:
        return True, 100.0, 100.0, 100.0
        
    cosine_sim = calculate_cosine_similarity(resume_text, jd_text)
    # Calibrate cosine similarity: map 0.0 -> 0%, 0.40 -> 100%
    scaled_cosine = min(100.0, (cosine_sim / 0.40) * 100.0)
    
    kw_ratio = calculate_keyword_match_ratio(jd_text, keywords)
    
    if kw_ratio is None:
        combined_score = scaled_cosine
        kw_percentage = 0.0
    else:
        kw_percentage = kw_ratio * 100.0
        # Weighted score: 50% keyword matching, 50% overall content similarity
        combined_score = (0.5 * kw_percentage) + (0.5 * scaled_cosine)
        
    combined_score = round(combined_score, 2)
    kw_percentage = round(kw_percentage, 2)
    scaled_cosine = round(scaled_cosine, 2)
    
    is_suitable = combined_score >= threshold
    return is_suitable, combined_score, kw_percentage, scaled_cosine

def get_job_description_text(driver):
    """
    Extracts the job description text content from Naukri's job details page.
    Utilizes a robust variety of selectors and fallbacks to handle dynamic layout changes.
    """
    # 1. Broad set of standard CSS/class/XPath selectors
    selectors = [
        (By.XPATH, "//section[contains(@class, 'job-desc')]"),
        (By.XPATH, "//div[contains(@class, 'job-desc')]"),
        (By.XPATH, "//div[contains(@class, 'job-description')]"),
        (By.XPATH, "//div[contains(@class, 'jd-desc')]"),
        (By.XPATH, "//div[contains(@class, 'description')]"),
        (By.XPATH, "//*[contains(@class, 'styles_jd-description')]"),
        (By.XPATH, "//section[contains(@class, 'description')]"),
        (By.ID, "job-desc"),
        (By.CLASS_NAME, "job-desc")
    ]
    for by, val in selectors:
        try:
            element = driver.find_element(by, val)
            if element and element.is_displayed():
                text = element.text.strip()
                if len(text) > 100:
                    return text
        except Exception:
            pass

    # 2. Match based on typical section headings
    headings = [
        "//h2[contains(text(), 'Job description') or contains(text(), 'Job Description')]",
        "//h3[contains(text(), 'Job description') or contains(text(), 'Job Description')]",
        "//div[contains(text(), 'Job description') or contains(text(), 'Job Description')]",
        "//span[contains(text(), 'Job description') or contains(text(), 'Job Description')]"
    ]
    for h_xpath in headings:
        try:
            element = driver.find_element(By.XPATH, h_xpath)
            if element:
                parent = element.find_element(By.XPATH, "..")
                if parent:
                    text = parent.text.strip()
                    if len(text) > 100:
                        return text
        except Exception:
            pass

    # 3. Fallback: Parse body content via regex to isolate description block
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        jd_match = re.search(r'(?i)job\s+description(.*?)(about\s+company|education|key\s+skills|role|industry|functional\s+area|$)', body_text, re.DOTALL)
        if jd_match:
            text = jd_match.group(1).strip()
            if len(text) > 100:
                return text
        if len(body_text) > 200:
            return body_text[:5000]
    except Exception:
        pass

    return ""

def extract_naukri_match_scorecard(driver):
    """
    Parses Naukri's official match score widget.
    Returns: dict with match statuses: e.g. {'keyskills': True, 'location': False, 'experience': True}
    """
    scorecard = {
        'keyskills': False,
        'location': False,
        'experience': False
    }
    
    try:
        # Locate the match score container
        containers = driver.find_elements(By.XPATH, "//*[contains(@class, 'match-score') or contains(@class, 'MatchScore') or contains(@class, 'styles_JDC__match-score')]")
        if not containers:
            return None # Indicator that widget was not found
            
        container = containers[0]
        # Find all detail blocks
        items = container.find_elements(By.XPATH, ".//div[contains(@class, 'details') or contains(@class, 'styles_MS__details')]")
        
        for item in items:
            text = item.text.strip().lower()
            # Check if this item has the check circle icon
            has_check = False
            try:
                # Look for the <i> tag with class containing check_circle or check
                icons = item.find_elements(By.XPATH, ".//i[contains(@class, 'check') or contains(@class, 'circle')]")
                if icons:
                    has_check = True
            except Exception:
                pass
                
            if "keyskill" in text:
                scorecard['keyskills'] = has_check
            elif "location" in text:
                scorecard['location'] = has_check
            elif "experience" in text:
                scorecard['experience'] = has_check
                
        return scorecard
    except Exception as e:
        print_lg(f"Error parsing Naukri scorecard: {e}")
        return None

def search_naukri_jobs(keyword: str, location: str) -> None:
    '''
    Navigates to Naukri search results using formatted query parameters sorted by date
    '''
    import re
    def get_seo_slug(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text)
        return text.strip('-')

    keyword_slug = get_seo_slug(keyword)
    location_str = location.strip().lower()
    if location_str == "india":
        location_str = ""
    
    if location_str:
        location_slug = get_seo_slug(location)
        search_url = f"https://www.naukri.com/{keyword_slug}-jobs-in-{location_slug}"
    else:
        search_url = f"https://www.naukri.com/{keyword_slug}-jobs"
        
    params = []
    if experience_years > 0:
        params.append(f"experience={experience_years}")
        
    # Sort by date (freshest jobs first)
    params.append("sort=dd")
    
    if params:
        search_url += "?" + "&".join(params)

    # For multiple keywords containing commas, we bypass SEO page and go directly to search input typing
    # because Naukri doesn't have an SEO page for multiple combined designation names.
    if "," in keyword:
        print_lg(f"\nMultiple designations detected in keyword: '{keyword}'. Skipping SEO URL and using UI typing...")
        is_invalid_page = True
        job_tuples = []
    else:
        print_lg(f"\n>-> Searching Naukri for '{keyword}' in '{location}' (Exp: {experience_years} years) -> URL: {search_url}")
        driver.get(search_url)
        time.sleep(3)

        # Check if page loaded successfully, otherwise fall back to generic query URL
        page_content = driver.page_source.lower()
        is_invalid_page = "something went wrong" in page_content or "page not found" in page_content or "404" in page_content
        
        # Check if there are any job card elements
        job_tuples = []
        try:
            job_tuples = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-job-tuple') or contains(@class, 'srp-jobtuple-wrapper') or contains(@class, 'cust-job-tuple') or contains(@class, 'custTuple')]")
        except Exception:
            pass

    if is_invalid_page or not job_tuples:
        print_lg(f"SEO URL failed or bypassed. Typing search keyword '{keyword}' directly in search UI to bypass space/comma encoding bugs...")
        
        # Navigate to a clean base page without query parameters to avoid Cloudflare/bot block
        if location.strip() and location.strip().lower() != "india":
            location_slug = get_seo_slug(location)
            base_url = f"https://www.naukri.com/jobs-in-{location_slug}"
        else:
            base_url = "https://www.naukri.com/jobs"
        
        print_lg(f"Navigating to clean base search URL: {base_url}")
        driver.get(base_url)
        time.sleep(5)
        
        # Locate search input box, clear it, type the keyword and submit
        try:
            search_input = wait.until(EC.presence_of_element_located((
                By.XPATH, "//input[contains(@class, 'suggestor-input') or contains(@placeholder, 'keyword') or contains(@placeholder, 'skills')]"
            )))
            # Focus and click via Javascript to prevent element click interception
            driver.execute_script("arguments[0].focus();", search_input)
            driver.execute_script("arguments[0].click();", search_input)
            time.sleep(0.5)
            
            from selenium.webdriver.common.keys import Keys
            import sys
            search_input.send_keys(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL, 'a')
            search_input.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            # Type keyword (keeps spaces and commas literal, preventing %20 and %2C bugs)
            search_input.send_keys(keyword)
            time.sleep(1)
            
            # Locate search button
            search_button = None
            search_btn_selectors = [
                (By.XPATH, "//button[contains(@class, 'qsbSubmit') or contains(text(), 'Search')]"),
                (By.XPATH, "//span[contains(@class, 'qsbSubmit') or contains(text(), 'Search')]"),
                (By.XPATH, "//div[contains(@class, 'qsbSubmit') or contains(text(), 'Search')]"),
                (By.CLASS_NAME, "qsbSubmit")
            ]
            for by, val in search_btn_selectors:
                try:
                    btn = driver.find_element(by, val)
                    if btn.is_displayed() and btn.is_enabled():
                        search_button = btn
                        break
                except Exception:
                    pass
            
            if search_button:
                search_button.click()
            else:
                search_input.send_keys(Keys.ENTER)
                
            print_lg("Search submitted successfully via UI input.")
            time.sleep(5)
        except Exception as se:
            print_lg(f"Error typing search keyword via UI: {se}. Trying URL parameter fallback (with '+' for spaces).")
            # If UI typing fails, we fall back to URL parameter with + replacing space
            encoded_keyword = urllib.parse.quote_plus(keyword)
            if location.strip() and location.strip().lower() != "india":
                encoded_location = urllib.parse.quote_plus(location.strip().lower())
                search_url = f"https://www.naukri.com/jobs-in-{encoded_location}?k={encoded_keyword}"
            else:
                search_url = f"https://www.naukri.com/jobs?k={encoded_keyword}"
                
            if experience_years > 0:
                search_url += f"&experience={experience_years}"
            search_url += "&sort=dd"
            
            print_lg(f"Navigating to URL Fallback: {search_url}")
            driver.get(search_url)
            time.sleep(3)

    # Try to apply sort by date in the UI to ensure it is sorted by Date
    try:
        print_lg("Attempting to apply Sort by Date filter via UI...")
        time.sleep(2)
        
        # Click the sort dropdown container
        sort_dropdown = None
        sort_selectors = [
            (By.XPATH, "//div[contains(@class, 'sort-dropdown') or contains(@class, 'sort-container') or contains(@class, 'dropdown')][.//*[contains(text(), 'Sort by') or contains(text(), 'Recommended') or contains(text(), 'Date')]]"),
            (By.XPATH, "//*[contains(text(), 'Sort by') or contains(text(), 'Recommended')]"),
            (By.XPATH, "//div[contains(@class, 'sort-grid')]"),
            (By.XPATH, "//span[contains(text(), 'Sort by')]")
        ]
        for by, val in sort_selectors:
            try:
                elements = driver.find_elements(by, val)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        sort_dropdown = el
                        break
                if sort_dropdown:
                    break
            except Exception:
                pass

        if sort_dropdown:
            print_lg(f"Found sort dropdown element: {sort_dropdown.text}. Clicking it...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_dropdown)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", sort_dropdown)
            time.sleep(1.5)
            
            # Click the 'Date' option inside the opened dropdown menu
            date_option = None
            date_selectors = [
                (By.XPATH, "//ul[contains(@class, 'dropdown') or contains(@class, 'list') or contains(@class, 'options')]//li[contains(text(), 'Date') or contains(text(), 'Freshness')]"),
                (By.XPATH, "//span[text()='Date' or text()='Freshness']"),
                (By.XPATH, "//li[text()='Date' or text()='Freshness' or contains(text(), 'Date')]"),
                (By.XPATH, "//*[contains(text(), 'Date') and not(self::span[contains(@class, 'exp')])]"),
            ]
            for by, val in date_selectors:
                try:
                    elements = driver.find_elements(by, val)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            date_option = el
                            break
                    if date_option:
                        break
                except Exception:
                    pass
            
            if date_option:
                print_lg(f"Found date sort option: '{date_option.text}'. Clicking it...")
                driver.execute_script("arguments[0].click();", date_option)
                time.sleep(3)
                print_lg("Sorting by Date applied successfully.")
            else:
                print_lg("Could not locate 'Date' option in expanded sort dropdown.")
        else:
            print_lg("Could not locate Sort by dropdown container on page.")
    except Exception as e:
        print_lg(f"Error applying Sort by Date filter: {e}")

def get_question_text(driver, element):
    # Check if inside chatbot overlay or container
    try:
        is_chat = False
        curr = element
        for _ in range(5):
            if curr:
                cls = curr.get_attribute("class") or ""
                id_val = curr.get_attribute("id") or ""
                if "chat" in cls.lower() or "chat" in id_val.lower():
                    is_chat = True
                    break
                curr = curr.find_element(By.XPATH, "./parent::*")
            else:
                break
        if is_chat:
            chat_bubbles = driver.find_elements(By.XPATH, "//div[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')] | //span[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')]")
            if chat_bubbles:
                return chat_bubbles[-1].text.strip()
    except Exception:
        pass

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

def is_chatbot_active(driver) -> bool:
    try:
        container = driver.find_element(By.ID, "chatbot-container")
        if container.is_displayed() and container.find_elements(By.XPATH, ".//*"):
            return True
    except Exception:
        pass
    
    overlay_selectors = [
        "//div[contains(@class, 'chatbot_Overlay')]",
        "//div[contains(@class, 'chatbot-container')]",
        "//div[contains(@id, 'chatbot')]",
        "//div[contains(@class, 'modal') or contains(@class, 'drawer') or contains(@class, 'form') or contains(@class, 'overlay')]",
        "//div[contains(@class, 'Overlay') and not(contains(@id, 'save')) and not(contains(@class, 'save'))]",
        "//form[contains(@class, 'apply') or contains(@class, 'question') or contains(@class, 'screening')]"
    ]
    for sel in overlay_selectors:
        try:
            elements = driver.find_elements(By.XPATH, sel)
            for el in elements:
                if el.is_displayed():
                    cls = el.get_attribute("class") or ""
                    id_val = el.get_attribute("id") or ""
                    if "header" not in cls.lower() and "header" not in id_val.lower():
                        return True
        except Exception:
            pass
            
    # Check if there are visible input/textarea/select/checkbox/radio elements (potential screening questions)
    try:
        all_elements = driver.find_elements(By.XPATH, "//input[not(@type='hidden') and not(contains(@class, 'header'))] | //textarea | //select")
        visible_interactive = []
        for el in all_elements:
            try:
                if el.is_displayed() and el.is_enabled():
                    name = el.get_attribute("name") or ""
                    id_val = el.get_attribute("id") or ""
                    placeholder = el.get_attribute("placeholder") or ""
                    cls = el.get_attribute("class") or ""
                    
                    if any(k in name.lower() or k in id_val.lower() or k in placeholder.lower() or k in cls.lower() for k in ["search", "header", "qsb"]):
                        continue
                        
                    typ = el.get_attribute("type") or ""
                    if typ in ["submit", "button"] and not any(k in name.lower() or k in id_val.lower() for k in ["choice", "option", "answer"]):
                        continue
                        
                    visible_interactive.append(el)
            except Exception:
                pass
                
        if visible_interactive:
            return True
    except Exception:
        pass
        
    # Check if there is any visible form tag (excluding header/search forms)
    try:
        forms = driver.find_elements(By.XPATH, "//form[not(contains(@class, 'search')) and not(contains(@class, 'header'))]")
        for f in forms:
            if f.is_displayed():
                return True
    except Exception:
        pass
        
    return False

def fill_naukri_questions(driver):
    '''
    Detects and fills dynamic screening forms or chatbot questions on Naukri
    '''
    # Check if chatbot is active. If on job detail page and no chatbot is active, do not run!
    current_url = driver.current_url.lower()
    if "job-listings" in current_url and not is_chatbot_active(driver):
        return

    max_steps = 10
    step = 0
    time.sleep(2) # Wait for potential popup/modal to render
    
    while step < max_steps:
        # Find active overlay container
        overlay = None
        overlay_selectors = [
            "//div[contains(@class, 'chatbot_Overlay')]",
            "//div[contains(@class, 'chatbot-container')]",
            "//div[contains(@id, 'chatbot')]",
            "//div[contains(@class, 'modal')]",
            "//div[contains(@class, 'drawer')]",
            "//div[contains(@class, 'Overlay') and not(contains(@id, 'save')) and not(contains(@class, 'save'))]"
        ]
        for sel in overlay_selectors:
            try:
                elements = driver.find_elements(By.XPATH, sel)
                for el in elements:
                    if el.is_displayed():
                        overlay = el
                        break
                if overlay:
                    break
            except Exception:
                pass

        if not overlay:
            # Check if there is any visible form/chat element on the page
            try:
                inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number' or not(@type)] | //textarea")
                visible_inputs = [el for el in inputs if el.is_displayed() and el.is_enabled() and el.get_attribute("type") not in ["submit", "button", "hidden", "radio", "checkbox"]]
                if not visible_inputs:
                    break
            except Exception:
                break

        options_clicked = False
        try:
            # Locate options/choices inside the overlay or on the page
            if overlay:
                choice_elements = overlay.find_elements(By.XPATH, ".//button | .//span | .//label | .//li | .//div[contains(@class, 'option') or contains(@class, 'value') or contains(@class, 'item')]")
            else:
                choice_elements = driver.find_elements(By.XPATH, "//form//*[self::button or self::span or self::label or self::li or self::div[contains(@class, 'option') or contains(@class, 'value') or contains(@class, 'item')]]")
                
            visible_choices = [el for el in choice_elements if el.is_displayed() and el.is_enabled() and el.text.strip()]
            
            # Filter out choices that match navigation or unrelated actions
            filtered_choices = []
            for el in visible_choices:
                txt = el.text.strip().lower()
                if txt in ["save", "save job", "report", "similar jobs", "share"]:
                    continue
                filtered_choices.append(el)
                
            if filtered_choices:
                question_text = ""
                try:
                    if overlay:
                        chat_bubbles = overlay.find_elements(By.XPATH, ".//div[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')] | .//span[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')]")
                    else:
                        chat_bubbles = driver.find_elements(By.XPATH, "//div[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')] | //span[contains(@class, 'msg') or contains(@class, 'bubble') or contains(@class, 'chat') or contains(@class, 'question')]")
                    if chat_bubbles:
                        question_text = chat_bubbles[-1].text.strip()
                except Exception:
                    pass
                
                expected_answer = get_answer_for_question(question_text)
                print_lg(f"Chatbot Question: '{question_text}' -> Expected: '{expected_answer}'")
                
                expected_parts = [p.strip().lower() for p in expected_answer.split('|') if p.strip()]
                clicked_choice = None
                
                if expected_parts:
                    for choice in filtered_choices:
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
                    for choice in filtered_choices:
                        choice_txt = choice.text.strip().lower()
                        if any(k in choice_txt for k in ["confirm", "apply", "yes", "agree", "accept", "submit"]):
                            print_lg(f"Found fallback confirmation option: '{choice.text}'")
                            driver.execute_script("arguments[0].click();", choice)
                            clicked_choice = choice
                            break
                        
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
            if overlay:
                input_elements = overlay.find_elements(By.XPATH, ".//input[@type='text' or @type='number' or not(@type)] | .//textarea")
            else:
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
                    
            if overlay:
                select_elements = overlay.find_elements(By.XPATH, ".//select")
            else:
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
            
        # Handle Radio buttons and Checkboxes
        try:
            if overlay:
                radio_checkboxes = overlay.find_elements(By.XPATH, ".//input[@type='radio' or @type='checkbox']")
            else:
                radio_checkboxes = driver.find_elements(By.XPATH, "//input[@type='radio' or @type='checkbox']")
                
            visible_radios = [el for el in radio_checkboxes if el.is_displayed() and el.is_enabled()]
            for rc in visible_radios:
                rc_id = rc.get_attribute("id") or ""
                rc_value = rc.get_attribute("value") or ""
                label_text = ""
                
                # Check for sibling label with matching 'for'
                if rc_id:
                    try:
                        labels = driver.find_elements(By.XPATH, f"//label[@for='{rc_id}']")
                        if labels:
                            label_text = labels[0].text.strip()
                    except Exception:
                        pass
                
                # Fallback to parent text
                if not label_text:
                    try:
                        parent = rc.find_element(By.XPATH, "..")
                        label_text = parent.text.strip()
                    except Exception:
                        pass
                        
                if not label_text:
                    label_text = rc_value
                    
                question_text = get_question_text(driver, rc)
                expected_ans = get_answer_for_question(question_text)
                
                print_lg(f"Radio/Checkbox Option: '{label_text}' for question '{question_text}' -> Expected Match: '{expected_ans}'")
                
                # Check if label/value matches expected answer
                expected_parts = [p.strip().lower() for p in expected_ans.split('|') if p.strip()]
                matched = False
                for part in expected_parts:
                    if part in label_text.lower() or part in rc_value.lower():
                        matched = True
                        break
                        
                if matched:
                    if not rc.is_selected():
                        print_lg(f"Selecting radio/checkbox option: '{label_text}'")
                        driver.execute_script("arguments[0].click();", rc)
                        options_clicked = True
        except Exception as e:
            print_lg("Error handling radio/checkbox elements:", e)
            
        # Locate and click submit/continue/save button
        submit_btn = None
        try:
            submit_selectors = []
            if overlay:
                submit_selectors.append((By.XPATH, ".//button[contains(normalize-space(.), 'Save') or contains(normalize-space(.), 'Submit') or contains(normalize-space(.), 'Continue') or contains(normalize-space(.), 'Send') or contains(normalize-space(.), 'Apply')]"))
            else:
                submit_selectors.extend([
                    (By.XPATH, "//button[contains(@class, 'submit') or contains(@class, 'continue') or contains(text(), 'Submit') or contains(text(), 'Continue') or contains(text(), 'Apply') or contains(text(), 'Save')]"),
                    (By.XPATH, "//input[@type='submit' or @value='Submit' or @value='Continue']"),
                    (By.XPATH, "//button[contains(., 'Send') or contains(., 'Submit') or contains(., 'Apply')]")
                ])
            
            for by, val in submit_selectors:
                try:
                    elements = overlay.find_elements(by, val) if overlay else driver.find_elements(by, val)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            submit_btn = el
                            break
                    if submit_btn:
                        break
                except Exception:
                    pass
        except Exception:
            pass
            
        if inputs_filled or options_clicked or submit_btn:
            if submit_btn:
                try:
                    print_lg(f"Clicking form submit/continue button: '{submit_btn.text}'")
                    driver.execute_script("arguments[0].click();", submit_btn)
                    time.sleep(3)
                    step += 1
                    continue
                except Exception as e:
                    print_lg("Error clicking submit button:", e)
            else:
                time.sleep(2)
                step += 1
                continue
        else:
            break

def apply_to_current_job(job_id, title, company, job_url):
    '''
    Handles direct application inside a job detail page
    '''
    try:
        # Check resume matching suitability before applying
        if enable_resume_matching:
            print_lg(f"Analyzing job description suitability for: {title} at {company}...")
            
            # Try using Naukri's official match scorecard first if enabled
            use_official = False
            try:
                use_official = use_naukri_official_match
            except Exception:
                use_official = False
                
            if use_official:
                print_lg("Using Naukri's official match scorecard for verification...")
                scorecard = extract_naukri_match_scorecard(driver)
                if scorecard is None:
                    print_lg("Naukri official match scorecard widget not found on page. Falling back to local resume matching.")
                    use_official = False # Fall back to local TF-IDF match
                else:
                    print_lg(f"Naukri Scorecard: Keyskills Match={scorecard['keyskills']}, Location Match={scorecard['location']}, Experience Match={scorecard['experience']}")
                    
                    # Verify requirements
                    fail_reasons = []
                    if require_keyskills_match and not scorecard['keyskills']:
                        fail_reasons.append("Keyskills mismatch")
                    if require_experience_match and not scorecard['experience']:
                        fail_reasons.append("Experience mismatch")
                    if require_location_match and not scorecard['location']:
                        fail_reasons.append("Location mismatch")
                        
                    if fail_reasons:
                        reason_str = ", ".join(fail_reasons)
                        print_lg(f"Skipping job: Failed Naukri official match requirements ({reason_str}).")
                        save_applied_job(job_id, title, company, job_url, f"Skipped (Naukri Match: {reason_str})")
                        return
                    else:
                        print_lg("Naukri official match requirements satisfied! Proceeding to apply.")
                        
            # If not using official match, or if official match fallback was triggered
            if not use_official:
                jd_text = get_job_description_text(driver)
                if not jd_text:
                    print_lg("Could not extract job description from page. Skipping match calculation and proceeding to apply by default.")
                else:
                    resume_text = get_resume_text()
                    is_suitable, score, kw_score, cos_score = check_job_suitability(
                        jd_text, resume_text, resume_keywords, resume_match_threshold
                    )
                    print_lg(f"Resume Match Score: {score}% (Threshold: {resume_match_threshold}%)")
                    print_lg(f"  - Keyword match: {kw_score}%")
                    print_lg(f"  - Semantic match: {cos_score}%")
                    
                    if not is_suitable:
                        print_lg(f"Skipping job: match score {score}% is below threshold {resume_match_threshold}%.")
                        save_applied_job(job_id, title, company, job_url, f"Skipped (Low Match: {score}%)")
                        return
                    print_lg(f"Suitable job! Match score {score}% is at or above threshold {resume_match_threshold}%. Proceeding to apply.")
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
