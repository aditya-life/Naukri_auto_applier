"""
Naukri Auto Applier
Developed by Aditya Kumar
GitHub: https://github.com/aditya-life/Naukri_auto_applier
"""

# Config settings for Naukri.com Bot

# Excel output config files
file_name = "all excels/naukri_applied_applications_history.csv"
failed_file_name = "all excels/naukri_failed_applications_history.csv"
logs_folder_path = "logs"

# Delays between actions (seconds)
click_gap = 1

# Stealth Mode settings
stealth_mode = True
run_in_background = False
disable_extensions = False
safe_mode = False

# Search Configuration
# Job search queries to loop through
search_keywords = ["Full Stack Developer", "Software Engineer", "Web Developer"]
# Naukri locations
search_location = "India"
# Naukri experience level (Years)
experience_years = 1  # 0 for fresher, 1, 2, 3 etc.

# Enable AI answering for any screening questionnaires if they appear
use_AI = False
ai_provider = "gemini" # "openai", "gemini", "deepseek"
