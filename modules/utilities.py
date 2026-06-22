"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

import os
import sys
import json
import pathlib
from time import sleep
from random import randint
from datetime import datetime, timedelta
from pyautogui import alert
from pprint import pprint

from config.naukri_settings import logs_folder_path

# Directories related
def make_directories(paths: list[str]) -> None:
    for path in paths:
        path = os.path.expanduser(path)
        path = path.replace("//","/")
        if '.' in os.path.basename(path):
            path = os.path.dirname(path)
        if not path:
            continue
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        except Exception as e:
            print(f'Error while creating directory "{path}": ', e)

def get_default_temp_profile() -> str:
    home = pathlib.Path.home()
    if sys.platform.startswith('win'):
        return "C:\\temp\\naukri-job-apply-profile"
    elif sys.platform.startswith('linux'):
        return str(home / ".naukri-job-apply-profile")
    return str(home / "Library" / "Application Support" / "Google" / "Chrome" / "naukri-job-apply-profile")

def find_default_profile_directory() -> str | None:
    home = pathlib.Path.home()
    if sys.platform.startswith('win'):
        paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data")
        ]
    elif sys.platform.startswith('linux'):
        paths = [
            str(home / ".config" / "google-chrome")
        ]
    elif sys.platform == 'darwin':
        paths = [
            str(home / "Library" / "Application Support" / "Google" / "Chrome")
        ]
    else:
        return None

    for path_str in paths:
        if os.path.exists(path_str):
            return path_str
    return None

# Logging related
def critical_error_log(possible_reason: str, stack_trace: Exception) -> None:
    print_lg(possible_reason, stack_trace, datetime.now(), from_critical=True)

def get_log_path():
    try:
        path = logs_folder_path + "/log.txt"
        return path.replace("//","/")
    except Exception:
        return "logs/log.txt"

__logs_file_path = "logs/log.txt"

def initialize_logs_path():
    global __logs_file_path
    __logs_file_path = get_log_path()

def print_lg(*msgs: str | dict, end: str = "\n", pretty: bool = False, flush: bool = False, from_critical: bool = False) -> None:
    try:
        for message in msgs:
            pprint(message) if pretty else print(message, end=end, flush=flush)
            with open(__logs_file_path, 'a+', encoding="utf-8") as file:
                file.write(str(message) + end)
    except Exception as e:
        trail = f'Skipped saving this message: "{message}" to log.txt!' if from_critical else "We'll try one more time to log..."
        print(f"Error writing to logs: {e}. {trail}")

def buffer(speed: int=0) -> None:
    if speed <= 0:
        return
    elif speed <= 1:
        sleep(randint(6,10)*0.1)
    elif speed <= 2:
        sleep(randint(10,18)*0.1)
    else:
        sleep(randint(18,round(speed)*10)*0.1)

def manual_login_retry(is_logged_in: callable, limit: int = 2) -> None:
    count = 0
    while not is_logged_in():
        print_lg("Seems like you're not logged in to Naukri!")
        button = "Confirm Login"
        message = 'After you successfully Log In, please click "{}" button below.'.format(button)
        if count > limit:
            button = "Skip Confirmation"
            message = 'If you\'re seeing this message even after you logged in, Click "{}".'.format(button)
        count += 1
        if alert(message, "Login Required", button) and count > limit:
            return
