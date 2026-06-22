# Naukri Auto Applier 🤖💼

A robust, automated job application bot for **Naukri.com** built in Python with Selenium. It uses `undetected_chromedriver` to securely navigate job search pages, autofills credentials using resilient visible selectors, bypasses profile-locking conflicts, and submits direct applications to match your experience and target location.

---

## Key Features 🚀

- **Conflict-Free Chrome Profile**: Uses a dedicated Chrome profile (`naukri-job-apply-profile`) allowing the bot to run alongside your primary browser.
- **Persistent Session & Bypassed OTPs**: Cookies and login states are stored persistently. Once you complete manual verification or OTP once, you remain logged in on subsequent runs.
- **Robust UI selectors**: Auto-detects visible fields (handling dynamic input IDs) on both traditional and server-driven web interfaces.
- **Direct Apply & Logging**: Iterates through job list pages, opens postings in separate tabs, direct-applies to matching roles, and exports application statuses (`Applied`, `Failed`, `External`) to a CSV history file.

---

## Project Structure 📁

```text
Naukri_auto_applier/
├── main.py                    # App entry point & main run loop
├── config/
│   ├── auth.py                # Naukri login email, password, and AI keys (Git ignored)
│   ├── naukri_settings.py     # Search keywords, location, exp limit, and driver settings
│   └── personal.py            # User legal name, phone number, and location details
├── modules/
│   ├── chrome_launcher.py     # Configures and instantiates undetected_chromedriver
│   ├── element_interaction.py # Handles visible inputs and button click selectors
│   ├── naukri_auth.py         # Performs auto-login & manual verification checkpoint
│   ├── naukri_applier.py      # Job card scraper, pagination navigation, and apply logic
│   └── utilities.py           # Custom delay buffers, logging, and lock cleanup
└── .gitignore                 # Excludes caches, auth credentials, and local excels
```

---

## Quick Setup 🛠️

### 1. Prerequisites
Ensure you have Python 3.10+ and Google Chrome installed. Install required packages:
```bash
pip3 install undetected-chromedriver selenium pyautogui
```

### 2. Configuration
Open `config/` files to customize the bot:
- **`config/auth.py`**: Configure your Naukri.com registered `username` (email/phone) and `password`.
- **`config/naukri_settings.py`**: Add your target keywords (e.g., `["Full Stack Developer", "Software Engineer"]`), `search_location`, and `experience_years`.

---

## Usage 🏃‍♂️

Run the applier from your terminal:
```bash
python3 main.py
```

### Note on Login & Verification:
- On your **first run**, the bot will launch a Chrome window and attempt to log in using the configured credentials.
- If Naukri prompts you for **OTP, CAPTCHA, or email verification**, complete it manually in the browser window and click **Confirm Login** in the terminal prompt.
- The session is saved. All future runs will automatically reuse the saved cookies and bypass login/OTP checks completely!
