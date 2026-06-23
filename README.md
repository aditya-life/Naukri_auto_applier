# Naukri Auto Applier 🤖💼

A robust, automated job application bot for **Naukri.com** built in Python with Selenium. It uses `undetected_chromedriver` to securely navigate job search pages, autofills credentials, bypasses profile-locking conflicts, matches candidate suitability against resume keywords or official scorecards, and handles screening questionnaires/chatbot drawers.

---

## Key Features 🚀

- **Conflict-Free Chrome Profile**: Uses a dedicated Chrome profile (`naukri-job-apply-profile`) allowing the bot to run alongside your primary browser.
- **Persistent Session & Bypassed OTPs**: Cookies and login states are stored persistently. Once you complete manual verification or OTP once, you remain logged in on subsequent runs.
- **Suitability & Resume Matching**: 
  - **Local TF-IDF Match**: Compares the job description (JD) with your PDF resume or fallback text. Filters out jobs below your threshold (e.g. 50%).
  - **Naukri Official Scorecard Match**: Can directly check Naukri's official match widget for Keyskills, Experience, and Location compatibility.
- **Advanced Questionnaire Chatbot Solver**: Detects overlay chatbot drawers (`chatbot_Drawer`), matches question text, selects custom-styled radio buttons/checkboxes, and clicks footer save elements (e.g., `Save` divs).
- **Precise Status Tracking**: Prevents false-positive success checks by verifying if active inputs are still present. Logs incomplete applications as `Failed (Questions Incomplete)` instead of falsely logging them as `Applied`.

---

## Answering Questionnaire & AI Integration Options 🧠

When screening questions appear, the bot can solve them using one of three modes, configurable via `ai_provider` in `config/naukri_settings.py` (with `use_AI = True`):

### 1. Gemini Pro / Cloud AI Providers (Recommended)
You can use external LLM APIs (Gemini, OpenAI, or Deepseek) to read your resume and dynamically generate precise screening answers.
- **Getting a Free Gemini API Key**: Go to [Google AI Studio](https://aistudio.google.com/) and click **Get API key** to create a free API key.
- **Setup**: In `config/auth.py`, enter your API key under `llm_api_key` (set `ai_provider = "gemini"` and `llm_model = "gemini-1.5-flash"` in settings).

### 2. Ollama Local AI (100% Free & Private)
Run lightweight Large Language Models (like `llama3`, `qwen`, or `gemma`) locally on your Mac without any API keys.
- **Setup**: Install [Ollama](https://ollama.com/), download a model (e.g., `ollama run llama3` or `ollama run qwen:1.5b`), and set `ai_provider = "ollama"` and `llm_model = "qwen:1.5b"` in your settings.

### 3. Built-in Local NLP Resume Parser (Zero-Dependency & Offline)
An offline, rule-based NLP parser that searches your resume text using keyword pattern matching and context extraction. It requires no API key, no Ollama setup, and no extra heavy Python packages.
- **Setup**: Set `ai_provider = "local_nlp"` in settings. It will match terms in the question (like skills, experience years, notice period, location) against your resume and auto-fill them. (Note: This is also used as an automatic fallback if a cloud API request fails).

---

## Project Structure 📁

```text
Naukri_auto_applier/
├── main.py                    # App entry point & main run loop
├── config/
│   ├── auth.py                # Naukri login email, password, and AI keys (Git ignored)
│   ├── auth.py.example        # Template for auth credentials
│   ├── naukri_settings.py     # Search keywords, location, exp limit, and driver settings
│   ├── personal.py            # User legal name, phone number, and location details
│   └── personal.py.example    # Template for personal configuration
├── modules/
│   ├── chrome_launcher.py     # Configures and instantiates undetected_chromedriver
│   ├── element_interaction.py # Handles visible inputs and button click selectors
│   ├── naukri_auth.py         # Performs auto-login & manual verification checkpoint
│   ├── naukri_applier.py      # Core scraping loop, NLP logic, AI questions solver, and apply functions
│   └── utilities.py           # Custom delay buffers, logging, and lock cleanup
├── logs/
│   └── log.txt                # Operation logs for debugging
└── all excels/
    ├── naukri_applied_applications_history.csv  # CSV record of successful applications
    └── naukri_failed_applications_history.csv   # CSV record of failed/incomplete applications
```

---

## Quick Setup 🛠️

### 1. Prerequisites
Ensure you have Python 3.10+ and Google Chrome installed. Install required packages:
```bash
pip3 install undetected-chromedriver selenium pyautogui requests pypdf
```

### 2. Configuration
Create your credentials configuration from the provided examples:
1. Copy the example files:
   ```bash
   cp config/auth.py.example config/auth.py
   cp config/personal.py.example config/personal.py
   ```
2. Open the config files to customize:
   - **`config/auth.py`**: Enter your Naukri email/phone (`username`), password, and API keys.
   - **`config/personal.py`**: Enter your personal details and path to your PDF resume (e.g. `/Users/yourusername/Desktop/Aditya_CV.pdf`).
   - **`config/naukri_settings.py`**: Customize search settings (e.g. `search_keywords = ["IT Support Engineer, Service Desk Engineer"]`, `experience_years = 4`), and toggle `use_AI = True` if you want AI to answer chatbot questions.

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
