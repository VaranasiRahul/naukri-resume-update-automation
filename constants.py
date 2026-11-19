# Configuration and constants used in the script. Update values as needed.

USERNAME = "rahulvaranasi04@gmail.com"
PASSWORD = "Gangstar#1"
MOBILE = "9346304157"

# --- Resume rename configuration ---
# Full path to your original resume file (can be .docx or .pdf)
ORIGINAL_RESUME_PATH = "/Users/rvaranas/PROJECTS/naukri-A/Naukri/resume/Rahul_Varanasi-Resume.docx"

# Directory where renamed/modified copies will be saved (must exist or be writable)
# Leave empty string "" to use the same folder as the original resume
RESUME_OUTPUT_DIR = ""

# Base name of your resume WITHOUT extension and WITHOUT the date suffix.
# Example: "Rahul_Varanasi-Resume" → output: "Rahul_Varanasi-Resume-23jun1.docx"
RESUME_BASENAME = "Rahul_Varanasi-Resume"

# --- Schedule configuration ---
# Times (24-hour HH:MM) at which the script should auto-run each day.
# Slot 1 = first upload of the day, Slot 2 = second upload.
SCHEDULE_TIME_SLOT_1 = "09:00"  # 9:00 AM
SCHEDULE_TIME_SLOT_2 = "14:00"  # 2:00 PM

# --- URLs ---
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"