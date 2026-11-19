#! python3
# -*- coding: utf-8 -*-
"""Naukri Daily update - Using Chrome"""

import io
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from random import choice, randint
from string import ascii_uppercase, digits

try:
    import schedule
except ImportError:
    schedule = None  # scheduler is optional; only needed for --schedule mode

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import constants

# ── Credentials & paths from constants ──────────────────────────────────────
username = constants.USERNAME
password = constants.PASSWORD
mob = constants.MOBILE

originalResumePath = constants.ORIGINAL_RESUME_PATH

# Output directory: use the same folder as the original resume if not set
_resume_output_dir = (
    constants.RESUME_OUTPUT_DIR
    if constants.RESUME_OUTPUT_DIR
    else os.path.dirname(os.path.abspath(originalResumePath))
)
resumeBasename = constants.RESUME_BASENAME

# ── Feature flags ────────────────────────────────────────────────────────────
# Set True only if your resume is a PDF and you want hidden random text added.
updatePDF = False

# If Headless = True, Chrome runs without a visible window.
# Set to True so Chrome doesn't pop up during your daily work.
headless = True

# ── URLs ─────────────────────────────────────────────────────────────────────
NaukriURL = constants.NAUKRI_LOGIN_URL

logging.basicConfig(
    level=logging.INFO, filename="naukri.log", format="%(asctime)s    : %(message)s"
)
os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_LOG_LEVEL"] = "0"


# ── Slot / rename helpers ─────────────────────────────────────────────────────

def get_slot_number():
    """
    Return 1 if current time is before the midpoint between the two schedule
    slots, otherwise return 2.

    Using the MIDPOINT (not the exact slot1 time) as the boundary avoids a
    race condition where launchd fires a few seconds after 9:00:00, causing
    the script to wrongly report slot 2.

    Example with slot1=09:00, slot2=14:00:
      midpoint = 11:30 AM
      Before 11:30 → slot 1  (morning upload)
      11:30 or later → slot 2  (afternoon upload)
    """
    now = datetime.now()
    slot1_h, slot1_m = map(int, constants.SCHEDULE_TIME_SLOT_1.split(":"))
    slot2_h, slot2_m = map(int, constants.SCHEDULE_TIME_SLOT_2.split(":"))

    # Total minutes from midnight for each slot
    slot1_mins = slot1_h * 60 + slot1_m
    slot2_mins = slot2_h * 60 + slot2_m
    midpoint_mins = (slot1_mins + slot2_mins) // 2

    now_mins = now.hour * 60 + now.minute
    return 1 if now_mins < midpoint_mins else 2


def get_renamed_resume_path():
    """
    Build a timestamped copy path for the resume.

    Pattern:  <RESUME_BASENAME>-<DD><mon><slot>.<ext>
    Examples:
        Rahul_Varanasi-DevOps-Resume-23jun1.docx   (9 AM upload on 23 June)
        Rahul_Varanasi-DevOps-Resume-23jun2.docx   (2 PM upload on 23 June)
        Rahul_Varanasi-DevOps-Resume-24jun1.docx   (9 AM upload on 24 June)
    """
    now = datetime.now()
    day = now.strftime("%d").lstrip("0")   # e.g. "23" → "23", "05" → "5"
    month = now.strftime("%b").lower()     # e.g. "jun"
    slot = get_slot_number()               # 1 or 2

    _, ext = os.path.splitext(originalResumePath)  # e.g. ".docx" or ".pdf"
    filename = f"{resumeBasename}-{day}{month}{slot}{ext}"
    return os.path.join(_resume_output_dir, filename)


# ── Humanization helpers ──────────────────────────────────────────────────────

# Rotating pool of real Mac Chrome user-agents.
# A different one is picked each run so the fingerprint changes daily.
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_7_10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


def human_type(element, text):
    """
    Type text into an element character-by-character with random delays,
    mimicking the speed of a real human typist (50–180 ms per character).
    """
    for char in text:
        element.send_keys(char)
        time.sleep(randint(50, 180) / 1000.0)


def human_pause(min_ms=300, max_ms=900):
    """Random short pause between UI actions to simulate human reaction time."""
    time.sleep(randint(min_ms, max_ms) / 1000.0)


def log_msg(message):
    """Print to console and store to Log"""
    print(message)
    logging.info(message)


def catch(error):
    """Method to catch errors and log error details"""
    _, _, exc_tb = sys.exc_info()
    lineNo = str(exc_tb.tb_lineno)
    msg = "%s : %s at Line %s." % (type(error), error, lineNo)
    print(msg)
    logging.error(msg)


def getObj(locatorType):
    """This map defines how elements are identified"""
    map = {
        "ID": By.ID,
        "NAME": By.NAME,
        "XPATH": By.XPATH,
        "TAG": By.TAG_NAME,
        "CLASS": By.CLASS_NAME,
        "CSS": By.CSS_SELECTOR,
        "LINKTEXT": By.LINK_TEXT,
    }
    return map[locatorType.upper()]


def GetElement(driver, elementTag, locator="ID"):
    """Wait max 15 secs for element and then select when it is available"""
    try:

        def _get_element(_tag, _locator):
            _by = getObj(_locator)
            if is_element_present(driver, _by, _tag):
                return WebDriverWait(driver, 15).until(
                    lambda d: driver.find_element(_by, _tag)
                )

        element = _get_element(elementTag, locator.upper())
        if element:
            return element
        else:
            log_msg("Element not found with %s : %s" % (locator, elementTag))
            return None
    except Exception as e:
        catch(e)
    return None


def is_element_present(driver, how, what):
    """Returns True if element is present"""
    try:
        driver.find_element(by=how, value=what)
    except NoSuchElementException:
        return False
    return True


def WaitTillElementPresent(driver, elementTag, locator="ID", timeout=30):
    """Wait till element present. Default 30 seconds"""
    result = False
    driver.implicitly_wait(0)
    locator = locator.upper()

    for _ in range(timeout):
        time.sleep(0.99)
        try:
            if is_element_present(driver, getObj(locator), elementTag):
                result = True
                break
        except Exception as e:
            log_msg("Exception when WaitTillElementPresent : %s" % e)
            pass

    if not result:
        log_msg("Element not found with %s : %s" % (locator, elementTag))
    driver.implicitly_wait(3)
    return result

def Logout(driver):
    """Logout from Naukri session """

    try:
        # -------- Drawer Menu XPaths --------
        drawer_xpaths = [
            f"//*[contains({ci('@class')}, 'drawer__icon')]",
            f"//div[contains({ci('@class')}, 'drawer')]"
        ]

        for xpath in drawer_xpaths:
            if is_element_present(driver, By.XPATH, xpath):
                try:
                    el = GetElement(driver, xpath, locator="XPATH")
                    if el:
                        el.click()
                        time.sleep(1)
                        log_msg("Drawer menu opened")
                        break
                except Exception as e:
                    log_msg(f"Drawer open failed ({xpath}): {e}")
                    continue

        # -------- Logout XPaths --------
        logout_xpaths = [
            "//a[@data-type='logoutLink']",

            f"//a[contains({ci('@class')}, 'list-cta') and contains({ci('@title')}, 'logout')]",
            f"//a[contains({ci('@class')}, 'logout')]",
            f"//a[contains({ci('@href')}, 'logout')]",

            f"//*[contains({ci('text()')}, 'logout')]",
            f"//*[contains({ci('.')}, 'logout')]",
        ]

        for xpath in logout_xpaths:
            if is_element_present(driver, By.XPATH, xpath):
                try:
                    el = GetElement(driver, xpath, locator="XPATH")
                    if el:
                        driver.execute_script("arguments[0].scrollIntoView(true);", el)
                        time.sleep(0.5)
                        el.click()
                        time.sleep(2)
                        log_msg("Logout Successful")
                        return True
                except Exception as e:
                    log_msg(f"Logout click failed ({xpath}): {e}")
                    continue

        log_msg("Logout button not found")
        return False

    except Exception as e:
        log_msg(f"Logout error: {e}")
        return False
    
def ci(xpath_part: str) -> str:
    """
    Wraps an XPath string in lowercase translate() for case-insensitive matching.
    Usage:
        ci("@class") → "translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"
        ci("text()") → "translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"
    """
    return f"translate({xpath_part},'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"


def tearDown(driver):
    try:
        driver.close()
        log_msg("Driver Closed Successfully")
    except Exception as e:
        catch(e)
        pass

    try:
        driver.quit()
        log_msg("Driver Quit Successfully")
    except Exception as e:
        catch(e)
        pass


def randomText():
    return "".join(choice(ascii_uppercase + digits) for _ in range(randint(1, 5)))


def LoadNaukri(headless):
    """Open Chrome to load Naukri.com with anti-bot-detection options."""

    options = webdriver.ChromeOptions()

    # ── Standard options ──────────────────────────────────────────────────────
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popups")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # ── Anti-bot-detection options ────────────────────────────────────────────
    # Naukri uses Cloudflare which fingerprints headless Chrome. These options
    # make the browser look like a regular user session.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Rotate user-agent on every run so the fingerprint changes daily
    chosen_ua = choice(USER_AGENTS)
    options.add_argument(f"user-agent={chosen_ua}")
    log_msg(f"Using user-agent: {chosen_ua[:60]}...")

    # Randomise window size slightly so it's never the same exact viewport
    width  = randint(1280, 1440)
    height = randint(800, 900)
    options.add_argument(f"--window-size={width},{height}")

    if headless:
        # Use the newer headless mode — significantly less detectable than the
        # old '--headless' flag which Cloudflare easily identifies.
        options.add_argument("--headless=new")

    # ── Launch driver ─────────────────────────────────────────────────────────
    driver = None
    try:
        driver = webdriver.Chrome(options=options, service=ChromeService())
    except Exception as e:
        print(f"Error launching Chrome: {e}")
        driver = webdriver.Chrome(options)

    # Mask the webdriver property that sites check via JavaScript
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    log_msg("Google Chrome Launched!")
    driver.implicitly_wait(5)
    driver.get(NaukriURL)
    return driver


def naukriLogin(headless=False):
    """Open Chrome browser and Login to Naukri.com"""
    status = False
    driver = None
    username_locator = "usernameField"
    password_locator = "passwordField"
    login_btn_locator = "//*[@type='submit' and normalize-space()='Login']"
    skip_locator = "//*[text() = 'SKIP AND CONTINUE']"
    close_locator = "//*[contains(@class, 'cross-icon') or @alt='cross-icon']"

    try:
        driver = LoadNaukri(headless)

        log_msg(driver.title)
        if "naukri.com" in driver.title.lower():
            log_msg("Website Loaded Successfully.")

        emailFieldElement = None
        if is_element_present(driver, By.ID, username_locator):
            emailFieldElement = GetElement(driver, username_locator, locator="ID")
            time.sleep(1)
            passFieldElement = GetElement(driver, password_locator, locator="ID")
            time.sleep(1)
            loginButton = GetElement(driver, login_btn_locator, locator="XPATH")
        else:
            log_msg("None of the elements found to login.")

        if emailFieldElement is not None:
            emailFieldElement.clear()
            human_pause(400, 800)        # pause before typing, like a real user
            human_type(emailFieldElement, username)
            human_pause(300, 700)
            passFieldElement.clear()
            human_pause(200, 500)
            human_type(passFieldElement, password)
            human_pause(500, 1000)       # think before clicking login
            loginButton.send_keys(Keys.ENTER)
            time.sleep(3)

            # Added click to Skip button
            print("Checking Skip button")
            if WaitTillElementPresent(driver, close_locator, "XPATH", 10):
                GetElement(driver, close_locator, "XPATH").click()
            if WaitTillElementPresent(driver, skip_locator, "XPATH", 5):
                GetElement(driver, skip_locator, "XPATH").click()

            # CheckPoint to verify login
            if WaitTillElementPresent(driver, "ff-inventory", locator="ID", timeout=40):
                CheckPoint = GetElement(driver, "ff-inventory", locator="ID")
                if CheckPoint:
                    log_msg("Naukri Login Successful")
                    status = True
                    return (status, driver)
                else:
                    log_msg("Unknown Login Error")
                    return (status, driver)
            else:
                log_msg("Unknown Login Error")
                return (status, driver)

    except Exception as e:
        catch(e)
    return (status, driver)


def UpdateProfile(driver):
    try:
        mobXpath = "//*[@name='mobile'] | //*[@id='mob_number']"
        saveXpath = "//button[@ type='submit'][@value='Save Changes'] | //*[@id='saveBasicDetailsBtn']"
        view_profile_locator = "//*[contains(@class, 'view-profile')]//a"
        edit_locator = "(//*[contains(@class, 'icon edit')])[1]"
        save_confirm = "//*[text()='today' or text()='Today']"
        close_locator = "//*[contains(@class, 'crossIcon')]"

        WaitTillElementPresent(driver, view_profile_locator, "XPATH", 20)
        profElement = GetElement(driver, view_profile_locator, locator="XPATH")
        profElement.click()
        driver.implicitly_wait(2)

        if WaitTillElementPresent(driver, close_locator, "XPATH", 10):
            GetElement(driver, close_locator, locator="XPATH").click()
            time.sleep(2)

        WaitTillElementPresent(driver, edit_locator + " | " + saveXpath, "XPATH", 20)
        if is_element_present(driver, By.XPATH, edit_locator):
            editElement = GetElement(driver, edit_locator, locator="XPATH")
            editElement.click()

            WaitTillElementPresent(driver, mobXpath, "XPATH", 10)
            mobFieldElement = GetElement(driver, mobXpath, locator="XPATH")
            if mobFieldElement:
                mobFieldElement.clear()
                mobFieldElement.send_keys(mob)
                driver.implicitly_wait(2)
                
            saveFieldElement = GetElement(driver, saveXpath, locator="XPATH")
            saveFieldElement.send_keys(Keys.ENTER)
            driver.implicitly_wait(3)

            WaitTillElementPresent(driver, save_confirm, "XPATH", 10)
            if is_element_present(driver, By.XPATH, save_confirm):
                log_msg("Profile Update Successful")
            else:
                log_msg("Profile Update Failed")

        elif is_element_present(driver, By.XPATH, saveXpath):
            mobFieldElement = GetElement(driver, mobXpath, locator="XPATH")
            if mobFieldElement:
                mobFieldElement.clear()
                mobFieldElement.send_keys(mob)
                driver.implicitly_wait(2)
    
            saveFieldElement = GetElement(driver, saveXpath, locator="XPATH")
            saveFieldElement.send_keys(Keys.ENTER)
            driver.implicitly_wait(3)

            WaitTillElementPresent(driver, "confirmMessage", locator="ID", timeout=10)
            if is_element_present(driver, By.ID, "confirmMessage"):
                log_msg("Profile Update Successful")
            else:
                log_msg("Profile Update Failed")

        time.sleep(5)

    except Exception as e:
        catch(e)



def PrepareResume():
    """
    Prepare the resume file to upload.

    - For .docx / any non-PDF file: simply copy the original to a new
      timestamped filename so Naukri sees it as a fresh document.
    - For .pdf files with updatePDF=True: additionally embed invisible random
      text (original behaviour) before saving to the timestamped path.

    Returns the absolute path of the file to upload.
    """
    dest_path = get_renamed_resume_path()

    try:
        _, ext = os.path.splitext(originalResumePath)
        is_pdf = ext.lower() == ".pdf"

        if is_pdf and updatePDF:
            # ── PDF path: embed hidden random text ──────────────────────────
            txt = randomText()
            xloc = randint(700, 1000)  # far right – outside visible page area
            fsize = randint(1, 10)

            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFont("Helvetica", fsize)
            can.drawString(xloc, 100, txt)
            can.save()
            packet.seek(0)

            new_pdf = PdfReader(packet)
            with open(originalResumePath, "rb") as f:
                existing_pdf = PdfReader(f)
                pagecount = len(existing_pdf.pages)
                log_msg("Found %s pages in PDF" % pagecount)

                output = PdfWriter()
                for pageNum in range(pagecount - 1):
                    output.add_page(existing_pdf.pages[pageNum])
                page = existing_pdf.pages[pagecount - 1]
                page.merge_page(new_pdf.pages[0])
                output.add_page(page)

                with open(dest_path, "wb") as out_stream:
                    output.write(out_stream)

            log_msg("Saved modified PDF to: %s" % dest_path)
        else:
            # ── Non-PDF (docx etc.) or PDF without hidden-text: just copy ───
            shutil.copy2(originalResumePath, dest_path)
            log_msg("Copied resume to: %s" % dest_path)

        return os.path.abspath(dest_path)

    except Exception as e:
        catch(e)
        log_msg("PrepareResume failed – falling back to original file.")
        return os.path.abspath(originalResumePath)



def cleanup_old_resumes(days_to_keep=7):
    """
    Delete dated resume copies (e.g. Rahul_Varanasi-Resume-23jun1.docx) that
    are older than `days_to_keep` days from the resume output directory.
    The original resume file (matching ORIGINAL_RESUME_PATH) is never deleted.
    """
    try:
        original_abs = os.path.abspath(originalResumePath)
        _, ext = os.path.splitext(originalResumePath)
        cutoff = time.time() - (days_to_keep * 86400)
        deleted = []

        for fname in os.listdir(_resume_output_dir):
            # Only touch files that match our basename pattern and extension
            if not (fname.startswith(resumeBasename + "-") and fname.endswith(ext)):
                continue
            fpath = os.path.join(_resume_output_dir, fname)
            if os.path.abspath(fpath) == original_abs:
                continue  # never delete the original
            if os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                deleted.append(fname)

        if deleted:
            log_msg("Cleaned up %d old resume copy(s): %s" % (len(deleted), ", ".join(deleted)))
        else:
            log_msg("No old resume copies to clean up.")
    except Exception as e:
        catch(e)


def UploadResume(driver, resumePath):
    try:
        attachCVID = "attachCV"
        lazyattachCVID = "lazyAttachCV"
        uploadCV_btn = "//*[contains(@class, 'upload')]//input[@value='Update resume']"
        CheckPointXpath = "//*[contains(@class, 'updateOn')]"
        saveXpath = "//button[@type='button']"
        close_locator = "//*[contains(@class, 'crossIcon')]"

        driver.get(constants.NAUKRI_PROFILE_URL)

        time.sleep(2)
        if WaitTillElementPresent(driver, close_locator, "XPATH", 10):
            GetElement(driver, close_locator, locator="XPATH").click()
            time.sleep(2)

        if WaitTillElementPresent(driver, lazyattachCVID, locator="ID", timeout=5):
            AttachElement = GetElement(driver, uploadCV_btn, locator="XPATH")
            AttachElement.send_keys(os.path.abspath(resumePath))

        if WaitTillElementPresent(driver, attachCVID, locator="ID", timeout=5):
            AttachElement = GetElement(driver, attachCVID, locator="ID")
            AttachElement.send_keys(os.path.abspath(resumePath))

        if WaitTillElementPresent(driver, saveXpath, locator="XPATH", timeout=5):
            saveElement = GetElement(driver, saveXpath, locator="XPATH")
            saveElement.click()

        WaitTillElementPresent(driver, CheckPointXpath, locator="XPATH", timeout=30)
        CheckPoint = GetElement(driver, CheckPointXpath, locator="XPATH")
        if CheckPoint:
            LastUpdatedDate = CheckPoint.text
            todaysDate1 = datetime.today().strftime("%b %d, %Y")
            todaysDate2 = datetime.today().strftime("%b %#d, %Y")
            if todaysDate1 in LastUpdatedDate or todaysDate2 in LastUpdatedDate:
                log_msg(
                    "Resume Document Upload Successful. Last Updated date = %s"
                    % LastUpdatedDate
                )
            else:
                log_msg(
                    "Resume Document Upload failed. Last Updated date = %s"
                    % LastUpdatedDate
                )
        else:
            log_msg("Resume Document Upload failed. Last Updated date not found.")

    except Exception as e:
        catch(e)
    time.sleep(2)


def main():
    """Single run: login → update profile → upload renamed resume → logout."""
    log_msg("-----Naukri.py Script Run Begin-----")
    log_msg("Upload slot: %s" % get_slot_number())

    # ── Random startup delay ──────────────────────────────────────────────────
    # Sleep 1–7 minutes before doing anything. This means the actual execution
    # time shifts by a different random amount every day, so Naukri never sees
    # a perfectly repeating pattern (e.g. always exactly 09:03:00).
    # Skip the delay if running manually from command line with --no-delay flag.
    if "--no-delay" not in sys.argv and os.environ.get("GITHUB_ACTIONS") != "true":
        delay_secs = randint(60, 420)   # 1 min to 7 min
        log_msg("Humanization delay: %d seconds (~%d min) before starting." % (
            delay_secs, delay_secs // 60
        ))
        time.sleep(delay_secs)

    log_msg("Actual start time: %s" % datetime.now().strftime("%H:%M:%S"))
    driver = None
    try:
        status, driver = naukriLogin(headless)
        if status:
            UpdateProfile(driver)
            if os.path.exists(originalResumePath):
                # Always prepare (copy/rename) the resume before uploading so
                # Naukri registers a new file with the date-slot suffix.
                resumePath = PrepareResume()
                UploadResume(driver, resumePath)
                # Clean up resume copies older than 7 days
                cleanup_old_resumes(days_to_keep=7)
            else:
                log_msg("Resume not found at %s " % originalResumePath)

    except Exception as e:
        catch(e)

    finally:
        if driver is not None:
            try:
                Logout(driver)
                time.sleep(2)
            except Exception as e:
                log_msg("Error during logout: %s" % e)
        tearDown(driver)

    log_msg("-----Naukri.py Script Run Ended-----\n")

    # Schedule the Mac to wake up for the next upload slot (macOS only)
    if sys.platform == "darwin":
        schedule_next_wake()


def schedule_next_wake():
    """
    Use macOS 'pmset' to schedule a one-time wake event 8 minutes before
    the next upload slot. This ensures the Mac wakes from sleep (lid closed)
    in time for launchd to trigger the script.

    Requires the laptop to be plugged into power to wake from lid-closed sleep.
    Silently skips if pmset is unavailable or user lacks permissions.

    Wake times scheduled:
      Slot 1 (morning) → wakes 8 min before SCHEDULE_TIME_SLOT_1 (e.g. 08:55)
      Slot 2 (afternoon) → wakes 8 min before SCHEDULE_TIME_SLOT_2 (e.g. 13:55)
    """
    try:
        import subprocess
        now = datetime.now()
        current_slot = get_slot_number()

        # Determine which slot comes NEXT
        if current_slot == 1:
            # Just ran slot 1 → schedule wake for slot 2
            slot_h, slot_m = map(int, constants.SCHEDULE_TIME_SLOT_2.split(":"))
            wake_label = "afternoon"
        else:
            # Just ran slot 2 → schedule wake for slot 1 tomorrow
            slot_h, slot_m = map(int, constants.SCHEDULE_TIME_SLOT_1.split(":"))
            wake_label = "morning (tomorrow)"

        # Wake 8 minutes before the launchd trigger time
        wake_m = slot_m - 8
        wake_h = slot_h
        if wake_m < 0:
            wake_m += 60
            wake_h -= 1

        # Build the date: today for slot 2, tomorrow for slot 1 (next morning)
        if current_slot == 1:
            wake_date = now.strftime("%m/%d/%Y")
        else:
            from datetime import timedelta
            wake_date = (now + timedelta(days=1)).strftime("%m/%d/%Y")

        wake_time_str = "%s %02d:%02d:00" % (wake_date, wake_h, wake_m)

        result = subprocess.run(
            ["sudo", "-n", "pmset", "schedule", "wake", wake_time_str],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log_msg("Mac wake scheduled for %s upload at %s" % (wake_label, wake_time_str))
        else:
            # sudo -n fails silently if password is required — that's fine
            log_msg("Mac wake scheduling skipped (sudo not available without password). "
                    "Keep laptop plugged in and lid open for automatic wake.")
    except Exception as e:
        # Non-critical — don't crash the script over this
        log_msg("Could not schedule Mac wake: %s" % e)


# ── Scheduler (twice-daily daemon mode) ──────────────────────────────────────

def run_scheduler():
    """
    Run as a long-lived daemon that triggers `main()` at the two configured
    times every day.

    Usage:
        python naukri.py --schedule

    The script will stay alive and wake up at SCHEDULE_TIME_SLOT_1 and
    SCHEDULE_TIME_SLOT_2 (defined in constants.py) to perform the upload.
    """
    if schedule is None:
        log_msg(
            "ERROR: 'schedule' package is not installed. "
            "Run: pip install schedule"
        )
        sys.exit(1)

    t1 = constants.SCHEDULE_TIME_SLOT_1  # e.g. "09:00"
    t2 = constants.SCHEDULE_TIME_SLOT_2  # e.g. "14:00"

    schedule.every().day.at(t1).do(main)
    schedule.every().day.at(t2).do(main)

    log_msg(
        "Scheduler started. Jobs scheduled at %s and %s every day. "
        "Press Ctrl+C to stop." % (t1, t2)
    )

    while True:
        schedule.run_pending()
        time.sleep(30)  # check every 30 seconds


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        run_scheduler()
    else:
        main()
