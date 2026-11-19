# Naukri Auto-Updater — Personal Reference Guide

> **What this does:** Automatically logs into Naukri, updates your profile, and uploads a
> renamed copy of your resume twice a day (9 AM & 2 PM) so recruiters always see a
> freshly-updated profile.

---

## Table of Contents
1. [How It Works](#1-how-it-works)
2. [Project Structure](#2-project-structure)
3. [Configuration (constants.py)](#3-configuration-constantspy)
4. [Resume Naming Pattern](#4-resume-naming-pattern)
5. [First-Time Setup](#5-first-time-setup)
6. [launchd Scheduler — Daily Commands](#6-launchd-scheduler--daily-commands)
7. [Checking Logs](#7-checking-logs)
8. [Changing Schedule Times](#8-changing-schedule-times)
9. [Troubleshooting](#9-troubleshooting)
10. [Running Manually (one-off)](#10-running-manually-one-off)
11. [Security Reminders](#11-security-reminders)

---

## 1. How It Works

```
launchd (macOS scheduler)
    │
    ├── 9:00 AM ──► python naukri.py
    │                   │
    │                   ├── Login to Naukri
    │                   ├── Update profile (mobile number touch)
    │                   ├── Copy resume → Rahul_Varanasi-Resume-23jun1.docx
    │                   ├── Upload renamed resume
    │                   └── Logout
    │
    └── 2:00 PM ──► python naukri.py
                        │
                        ├── Login to Naukri
                        ├── Update profile
                        ├── Copy resume → Rahul_Varanasi-Resume-23jun2.docx
                        ├── Upload renamed resume
                        └── Logout
```

- Chrome runs **headlessly** (invisible) so it doesn't interrupt your work.
- The original resume file is **never modified** — only a renamed copy is created and uploaded.
- Everything is logged to `naukri.log` in the project folder.

---

## 2. Project Structure

```
/Users/rvaranas/PROJECTS/naukri-A/Naukri/
│
├── constants.py              ← ✏️  Your config (credentials, paths, times)
├── naukri.py                 ← Main automation script
├── requirements.txt          ← Python dependencies
├── com.naukri.updater.plist  ← macOS launchd scheduler config
├── SETUP_GUIDE.md            ← This file
│
├── resume/
│   ├── Rahul_Varanasi-Resume.docx        ← ✅ Your ORIGINAL resume (never touched)
│   ├── Rahul_Varanasi-Resume-23jun1.docx ← Auto-generated copies (safe to delete)
│   ├── Rahul_Varanasi-Resume-23jun2.docx
│   └── ...
│
├── naukri.log                ← Main log (appended every run)
└── naukri_launchd_error.log  ← Error log from launchd
```

---

## 3. Configuration (`constants.py`)

Open this file to change any setting:
```
/Users/rvaranas/PROJECTS/naukri-A/Naukri/constants.py
```

| Setting | Current Value | What to change |
|---|---|---|
| `USERNAME` | your Naukri email | If you change your login email |
| `PASSWORD` | your Naukri password | If you change your password |
| `MOBILE` | your phone number | If you change your phone |
| `ORIGINAL_RESUME_PATH` | `.../resume/Rahul_Varanasi-Resume.docx` | If you move the resume file |
| `RESUME_OUTPUT_DIR` | `""` (same folder as original) | Set a different output folder |
| `RESUME_BASENAME` | `Rahul_Varanasi-Resume` | If you rename the resume |
| `SCHEDULE_TIME_SLOT_1` | `"09:00"` | Morning upload time |
| `SCHEDULE_TIME_SLOT_2` | `"14:00"` | Afternoon upload time |

> ⚠️ **After changing schedule times**, you must reload the launchd job:
> ```bash
> launchctl unload ~/Library/LaunchAgents/com.naukri.updater.plist
> launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist
> ```

---

## 4. Resume Naming Pattern

The script auto-generates a name based on **date + slot number**:

```
Rahul_Varanasi-Resume-<day><month><slot>.docx
```

| Time of run | Example output filename |
|---|---|
| 23 June — 9 AM (slot 1) | `Rahul_Varanasi-Resume-23jun1.docx` |
| 23 June — 2 PM (slot 2) | `Rahul_Varanasi-Resume-23jun2.docx` |
| 24 June — 9 AM (slot 1) | `Rahul_Varanasi-Resume-24jun1.docx` |
| 1 July — 9 AM (slot 1) | `Rahul_Varanasi-Resume-1jul1.docx` |

All copies are saved in the same `resume/` folder. You can safely delete old copies anytime.

---

## 5. First-Time Setup

> ✅ Already done — keeping this here for reference if you ever re-clone or set up on a new Mac.

```bash
# 1. Clone and enter project
git clone <repo-url>
cd /Users/rvaranas/PROJECTS/naukri-A/Naukri

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install schedule

# 3. Edit your credentials
nano constants.py   # or open in any editor

# 4. Copy launchd plist to LaunchAgents
cp com.naukri.updater.plist ~/Library/LaunchAgents/

# 5. Load the scheduler
launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist

# 6. Verify it's active
launchctl list | grep naukri
# Expected output:  -   0   com.naukri.updater
```

---

## 6. launchd Scheduler — Daily Commands

### Check if the scheduler is active
```bash
launchctl list | grep naukri
```
Output: `- 0 com.naukri.updater` → ✅ Active and waiting  
Output: nothing → ❌ Not loaded (run the load command below)

### Stop the scheduler (pause uploads)
```bash
launchctl unload ~/Library/LaunchAgents/com.naukri.updater.plist
```

### Start / restart the scheduler
```bash
launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist
```

### Permanently remove (disable forever)
```bash
launchctl unload ~/Library/LaunchAgents/com.naukri.updater.plist
rm ~/Library/LaunchAgents/com.naukri.updater.plist
```

---

## 7. Checking Logs

### Quick check — last 20 lines of the main log
```bash
tail -20 /Users/rvaranas/PROJECTS/naukri-A/Naukri/naukri.log
```

### Watch it live (useful right after a manual run)
```bash
tail -f /Users/rvaranas/PROJECTS/naukri-A/Naukri/naukri.log
```
Press `Ctrl+C` to stop watching.

### Check for errors
```bash
cat /Users/rvaranas/PROJECTS/naukri-A/Naukri/naukri_launchd_error.log
```

### What a successful run looks like in the log
```
2026-06-23 09:00:12  : -----Naukri.py Script Run Begin-----
2026-06-23 09:00:12  : Upload slot: 1
2026-06-23 09:00:15  : Google Chrome Launched!
2026-06-23 09:00:18  : Website Loaded Successfully.
2026-06-23 09:00:25  : Naukri Login Successful
2026-06-23 09:00:30  : Profile Update Successful
2026-06-23 09:00:32  : Copied resume to: .../resume/Rahul_Varanasi-Resume-23jun1.docx
2026-06-23 09:00:45  : Resume Document Upload Successful. Last Updated date = Jun 23, 2026
2026-06-23 09:00:47  : Logout Successful
2026-06-23 09:00:48  : Driver Closed Successfully
2026-06-23 09:00:48  : -----Naukri.py Script Run Ended-----
```

---

## 8. Changing Schedule Times

1. **Edit `constants.py`:**
   ```python
   SCHEDULE_TIME_SLOT_1 = "08:00"   # Change to 8 AM
   SCHEDULE_TIME_SLOT_2 = "13:00"   # Change to 1 PM
   ```

2. **Reload launchd** (times are baked into the plist, so also edit the plist):
   ```bash
   nano /Users/rvaranas/PROJECTS/naukri-A/Naukri/com.naukri.updater.plist
   ```
   Update the `<integer>` values under `StartCalendarInterval`.

3. **Re-copy and reload:**
   ```bash
   cp /Users/rvaranas/PROJECTS/naukri-A/Naukri/com.naukri.updater.plist ~/Library/LaunchAgents/
   launchctl unload ~/Library/LaunchAgents/com.naukri.updater.plist
   launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist
   ```

---

## 9. Troubleshooting

### Problem: `launchctl list | grep naukri` shows nothing
```bash
# Re-load it
launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist
```

### Problem: Script ran but login failed
- Check if your Naukri password changed → update `constants.py`
- Naukri may have added a CAPTCHA → run manually once to clear it:
  ```bash
  cd /Users/rvaranas/PROJECTS/naukri-A/Naukri
  source .venv/bin/activate
  python naukri.py   # opens Chrome visibly since headless=True needs to be temporarily False
  ```

### Problem: Resume upload failed
- Make sure the file exists at:  
  `/Users/rvaranas/PROJECTS/naukri-A/Naukri/resume/Rahul_Varanasi-Resume.docx`
- Check if Naukri changed their UI → look at `naukri_launchd_error.log`

### Problem: Script didn't run at scheduled time
- The Mac must be **awake** at the scheduled time. If it was asleep, the job is skipped.
- launchd does **not** catch up on missed jobs after sleep.
- Solution: Keep the lid open or plug in power at 9 AM / 2 PM.

### Problem: Chrome driver error
```bash
# Update chrome driver via pip
source .venv/bin/activate
pip install --upgrade selenium
```

### Problem: After macOS update, scheduler stopped
```bash
launchctl unload ~/Library/LaunchAgents/com.naukri.updater.plist
launchctl load ~/Library/LaunchAgents/com.naukri.updater.plist
```

---

## 10. Running Manually (one-off)

Useful for testing or when you want to trigger an immediate update:

```bash
cd /Users/rvaranas/PROJECTS/naukri-A/Naukri
source .venv/bin/activate
python naukri.py
```

> **Note:** Running manually at 11 AM will still generate a slot-2 filename  
> (since 11 AM > 9 AM slot boundary), e.g. `Rahul_Varanasi-Resume-23jun2.docx`.  
> This is fine — Naukri just sees a fresh file.

---

## 11. Security Reminders

> ⚠️ `constants.py` contains your Naukri **username and password in plain text**.

- **Never commit or push `constants.py` to GitHub.**
- It's already in `.gitignore` — double check with: `git status` (it should not appear)
- If you accidentally push it, **change your Naukri password immediately**.
- Do not share the `constants.py` file with anyone.

---

*Last updated: June 2026*

---

## 12. Private GitHub Repo + Tracking Upstream Updates

### Why not just fork?
GitHub does not allow making a fork private on free accounts. Instead, **duplicate** the repo to a private one and configure the original as `upstream`.

### One-time setup

```bash
cd /Users/rvaranas/PROJECTS/naukri-A/Naukri

# 1. Add YOUR private GitHub repo as origin (replace URL with yours)
git remote add origin https://github.com/YOUR_USERNAME/Naukri-private.git

# 2. Add the original author's repo as upstream
git remote add upstream https://github.com/navchandar/Naukri.git

# 3. Verify both remotes are set
git remote -v

# 4. Push your customized code to your private repo
git add .
git commit -m "Initial: customized setup with resume rename and scheduler"
git push -u origin master
```

### When upstream has updates (after getting notified — see Section 13)

```bash
git fetch upstream                  # Download author's latest changes
git merge upstream/master           # Merge into your local branch
# Fix any conflicts, then:
git push origin master              # Push merged result to your private repo
```

> **Files most likely to have conflicts:** `naukri.py` (we added rename logic) and `constants.py` (we added new fields).  
> When in doubt, ask Antigravity AI to help resolve conflicts safely.

---

## 13. Auto-Notification When Original Author Updates His Repo

A GitHub Actions workflow (`.github/workflows/upstream-notifier.yml`) is already set up in your repo. It:

1. Runs **every day at 1:30 PM IST** automatically
2. Checks the latest commit SHA on [navchandar/Naukri](https://github.com/navchandar/Naukri)
3. If anything changed since the last check → **opens an Issue in your private repo**
4. GitHub emails you about the new issue automatically
5. Stores the latest SHA so it doesn't notify you twice for the same commit

### What the notification issue looks like

```
⚠️ Upstream update detected: navchandar/Naukri

Commit Details:
  Message: Fix login flow for new Naukri UI
  Author:  navchandar
  Date:    2026-07-10
  Link:    https://github.com/navchandar/Naukri/commit/abc123

What to do:
  1. Ask Antigravity AI to review and merge the changes
  2. Run: git fetch upstream && git merge upstream/master
  3. Resolve conflicts in naukri.py / constants.py
  4. Push: git push origin master
  5. Close this issue
```

### Enable GitHub email notifications (one-time)
Go to: **GitHub → Settings → Notifications → Issues** → make sure email is ON.

### Manually trigger the check anytime
Go to your private repo on GitHub → **Actions** tab → `Notify on Upstream Updates` → **Run workflow**.

### No secrets needed
The workflow uses the built-in `GITHUB_TOKEN` — no setup required.
