"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

import sys
import time
from config.naukri_settings import click_gap
from modules.utilities import buffer, print_lg, sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

# Click Functions
def wait_span_click(driver: WebDriver, text: str, time_val: float=5.0, click: bool=True, scroll: bool=True, scrollTop: bool=False) -> WebElement | bool:
    if text:
        try:
            button = WebDriverWait(driver, time_val).until(EC.presence_of_element_located((By.XPATH, './/span[normalize-space(.)="'+text+'"]')))
            if scroll:  scroll_to_view(driver, button, scrollTop)
            if click:
                button.click()
                buffer(click_gap)
            return button
        except Exception:
            print_lg("Click Failed! Didn't find '"+text+"'")
            return False

# Scroll functions
def scroll_to_view(driver: WebDriver, element: WebElement, top: bool = False) -> None:
    if top:
        return driver.execute_script('arguments[0].scrollIntoView();', element)
    return driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "instant" });', element)

# Enter input text functions
def text_input_by_ID(driver: WebDriver, id: str, value: str, time_limit: float=5.0) -> None:
    '''
    Enters `value` into the input field with the given `id` (or fallback robust visible selectors) if found.
    '''
    # Map of ID to visible selectors
    selectors = [(By.ID, id)]
    if id in ["username", "email", "emailId"]:
        selectors.extend([
            (By.XPATH, "//input[@type='text' and (contains(@placeholder, 'Email') or contains(@placeholder, 'Username'))]"),
            (By.XPATH, "//input[@type='email']"),
            (By.XPATH, "//input[@autocomplete='username']"),
            (By.XPATH, "//input[contains(@id, 'username') or contains(@id, 'email') or contains(@name, 'email') or contains(@placeholder, 'email')]")
        ])
    elif id == "password":
        selectors.extend([
            (By.XPATH, "//input[@type='password']"),
            (By.XPATH, "//input[@autocomplete='current-password']"),
            (By.XPATH, "//input[contains(@id, 'password') or contains(@name, 'password') or contains(@placeholder, 'password')]")
        ])

    # Find the visible element
    start_time = time.time()
    field = None
    while time.time() - start_time < time_limit:
        for by, val in selectors:
            try:
                elements = driver.find_elements(by, val)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        field = el
                        break
                if field:
                    break
            except Exception:
                pass
        if field:
            break
        time.sleep(0.2)
        
    if not field:
        # Final fallback
        for by, val in selectors:
            try:
                elements = driver.find_elements(by, val)
                if elements:
                    field = elements[0]
                    break
            except Exception:
                pass

    if not field:
        raise NoSuchElementException(f"Could not find input field with ID or fallback: {id}")
        
    # Input the value
    # Clear existing text using Control+a or Command+a
    select_all_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
    try:
        field.send_keys(select_all_key + "a")
        field.send_keys(Keys.BACKSPACE)
    except Exception:
        try:
            field.clear()
        except Exception:
            pass
            
    field.send_keys(value)

def try_xp(driver: WebDriver, xpath: str, click: bool=True) -> WebElement | bool:
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click()
            return True
        else:
            return driver.find_element(By.XPATH, xpath)
    except Exception: 
        return False

def try_linkText(driver: WebDriver, linkText: str) -> WebElement | bool:
    try:    
        return driver.find_element(By.LINK_TEXT, linkText)
    except Exception:  
        return False
