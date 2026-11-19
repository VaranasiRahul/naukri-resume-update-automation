# Configuration and constants used in the script.
# In GitHub Actions, all sensitive values come from repository Secrets (env vars).
# Locally, you can create a .env file or set env vars in your shell.

import os

USERNAME = os.environ.get("NAUKRI_USERNAME", "")
PASSWORD = os.environ.get("NAUKRI_PASSWORD", "")
MOBILE   = os.environ.get("NAUKRI_MOBILE", "")

# --- Resume rename configuration ---
# In GitHub Actions the resume is checked in at resume/Rahul_Varanasi-Resume.docx
# and ORIGINAL_RESUME_PATH defaults to that relative path.
ORIGINAL_RESUME_PATH = os.environ.get(
    "RESUME_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume", "Rahul_Varanasi-Resume.docx")
)

# Directory where renamed/modified copies will be saved.
# Leave empty string "" to use the same folder as the original resume.
RESUME_OUTPUT_DIR = os.environ.get("RESUME_OUTPUT_DIR", "")

# Base name of your resume WITHOUT extension and WITHOUT the date suffix.
# Example: "Rahul_Varanasi-Resume" → output: "Rahul_Varanasi-Resume-23jun1.docx"
RESUME_BASENAME = os.environ.get("RESUME_BASENAME", "Rahul_Varanasi-Resume")

# --- Schedule configuration ---
# Times (24-hour HH:MM) at which the script should auto-run each day.
# Slot 1 = first upload of the day, Slot 2 = second upload.
SCHEDULE_TIME_SLOT_1 = "09:00"  # 9:00 AM IST (03:30 UTC)
SCHEDULE_TIME_SLOT_2 = "14:00"  # 2:00 PM IST (08:30 UTC)

# --- URLs ---
NAUKRI_LOGIN_URL  = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"