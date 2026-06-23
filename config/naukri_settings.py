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
# Safe mode - opens Chrome using guest profile or if you have multiple profiles in browser. This will open chrome in guest profile!
safe_mode = True                    # True or False, Note: True or False are case-sensitive

# Search Configuration
# Job search queries to loop through
search_keywords = ["IT Support Engineer, Service Desk Engineer, L1 Support, L2 Support, Desktop Support, System Administrator"]
# Naukri locations
search_location = "India"
# Naukri experience level (Years)
experience_years = 4  # 0 for fresher, 1, 2, 3 etc.

# Enable AI answering for any screening questionnaires if they appear
use_AI = False
ai_provider = "gemini" # "openai", "gemini", "deepseek"

# ==============================================================================
# Resume Matching & Filtering Settings (Resume Matching Feature)
# ==============================================================================
# [HINDI SETUP GUIDE]:
# 1. 'enable_resume_matching' ko True/False set karein feature ko on/off karne ke liye.
# 2. 'resume_match_threshold' me minimum match limit (jaise 60) set karein apne hisab se.
# 3. 'resume_keywords' me apne resume ke main keywords/skills daalein.
# 4. 'resume_raw_text' me apna poora resume paste karein jo PDF read na hone pe fallback tarike se use hoga.
# 5. [PDF AUTOMATION SETUP]: Agar aap chahte hain ki aapki PDF file se text automatic nikal liya jaye:
#    - Terminal me command run karein: pip install pypdf
#    - 'config/personal.py' file me jaakar 'default_resume_path' ko apne resume file ke real path par set karein.
#    - Agar ye setup rehta hai, toh bot automatically PDF se match karega.
#
# [ENGLISH SETUP GUIDE]:
# 1. Set 'enable_resume_matching' to True/False to enable or disable the filtering.
# 2. Set 'resume_match_threshold' to your desired match percentage (e.g. 60 for 60% match).
# 3. Add your main technical skills to 'resume_keywords'.
# 4. Paste your resume text in 'resume_raw_text' as a fallback if PDF parsing fails.
# 5. [PDF AUTOMATION SETUP]: To extract resume text directly from your PDF file automatically:
#    - Run: pip install pypdf
#    - Ensure 'default_resume_path' in 'config/personal.py' points to your actual PDF resume.

# Set to True to analyze job descriptions and filter before applying (True or False)
enable_resume_matching = True

# Minimum match percentage required to apply for the job (0 to 100)
# Updated to 50% as requested by the user
resume_match_threshold = 50

# Resume key technical skills/keywords for keyword-overlap calculations.
# (Highly recommended: list tools, programming languages, and certifications you have)
resume_keywords = [
    "IT Support", "Service Desk", "L1 Support", "L2 Support", 
    "Desktop Support", "Troubleshooting", "Windows", "MacOS", 
    "Office 365", "Outlook", "Active Directory", "ITIL", "Ticketing System"
]

# Raw text of your Resume/CV for advanced semantic TF-IDF match calculations.
# Paste your full resume text here. If PDF parsing fails, this text will be used.
resume_raw_text = """
Aditya Kumar
IT Support Engineer & Service Desk Specialist
Phone: YOUR_PHONE_NUMBER | Email: aditya12186@gmail.com
Skills: L1 Support, L2 Support, Desktop Support, Windows, MacOS, Office 365, Outlook configuration, Active Directory, Troubleshooting hardware and software, ITSM Ticketing tools, Incident Management, Customer Support, ITIL guidelines.
"""

# ==============================================================================
# Naukri Official Scorecard Match Settings
# ==============================================================================
# Set to True to use Naukri.com's own matching scorecard displayed on the page.
# If True, it will bypass our local resume similarity check and use Naukri's check instead.
use_naukri_official_match = True

# Match requirements if using Naukri's official match (True or False)
# If True, the job will only be applied to if Naukri says that specific field is a match.
require_keyskills_match = True       # Must match key skills according to Naukri
require_experience_match = True     # Must match experience according to Naukri
require_location_match = False       # Must match location according to Naukri
