"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

import time
import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

from config.auth import username, password
from modules.chrome_launcher import driver, wait, actions
from modules.element_interaction import text_input_by_ID, try_xp
from modules.utilities import print_lg, manual_login_retry

def is_logged_in_naukri() -> bool:
    '''
    Checks if the user is currently logged in on Naukri.com
    '''
    current_url = driver.current_url.lower()
    
    # If the URL contains dashboard, homepage, mn-home, or profile, user is logged in
    if any(keyword in current_url for keyword in ["dashboard", "homepage", "mn-home", "profile", "recommendation"]):
        return True

    # Check if there are any visible login elements on the page
    for selector in [
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "//input[@type='password']"),
        (By.XPATH, "//button[text()='Login']"),
        (By.XPATH, "//button[contains(., 'Login')]")
    ]:
        try:
            elements = driver.find_elements(*selector)
            for el in elements:
                if el.is_displayed():
                    return False
        except Exception:
            pass
            
    print_lg("Assuming user is logged in as no login fields were found.")
    return True

def login_naukri() -> None:
    '''
    Logs in to Naukri.com using the username and password in config/auth.py
    '''
    driver.get("https://www.naukri.com/nlogin/login")
    time.sleep(2)
    
    if username == "username@example.com" or not password:
        pyautogui.alert("Please configure your credentials in config/auth.py, or log in manually now.", "Login Required")
        manual_login_retry(is_logged_in_naukri, 2)
        return

    try:
        # Wait for the login form to load
        WebDriverWait(driver, 10).until(
            lambda d: any(
                el.is_displayed() for sel in [
                    (By.XPATH, "//input[@type='email']"),
                    (By.XPATH, "//input[@type='password']")
                ] for el in d.find_elements(*sel)
            )
        )
        
        # Input username and password using our robust selector method
        try:
            text_input_by_ID(driver, "usernameField", username, 5)
        except Exception as e:
            print_lg("Failed to auto-fill username field:", e)
            
        try:
            text_input_by_ID(driver, "passwordField", password, 5)
        except Exception as e:
            print_lg("Failed to auto-fill password field:", e)

        # Click the Login button
        login_btn = None
        login_selectors = [
            (By.XPATH, "//button[@type='submit' and text()='Login']"),
            (By.XPATH, "//button[normalize-space(.)='Login']"),
            (By.XPATH, "//button[contains(@class, 'login-button') or contains(@class, 'btn-primary')]")
        ]
        for by, val in login_selectors:
            try:
                elements = driver.find_elements(by, val)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        login_btn = el
                        break
                if login_btn:
                    break
            except Exception:
                pass
                
        if login_btn:
            login_btn.click()
            print_lg("Clicked Naukri login button.")
        else:
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
    except Exception as e:
        print_lg("Auto login attempt failed:", e)

    # Wait for authentication redirect
    time.sleep(3)
    try:
        WebDriverWait(driver, 10).until(lambda d: is_logged_in_naukri())
        print_lg("Naukri login successful!")
    except Exception:
        print_lg("Naukri auto login verification failed. Requesting manual login...")
        manual_login_retry(is_logged_in_naukri, 2)
