# AutoApply

A personal desktop tool for filling out job/work application forms automatically.

You enter your details once (resume, contact info, and the questions most
applications ask — age, birth year, work authorization, EEO answers, etc.),
pick which browser to drive, and AutoApply opens that browser on a job's
application page and fills in everything it can recognize. You stay in control:
it **fills** the form and **stops before submitting** by default, so you can
review and click submit yourself.

> ⚠️ Use responsibly. This is meant to save you typing the same answers over and
> over on legitimate applications. Don't use it to mass-spam employers, and always
> review what was filled before submitting. Respect each site's Terms of Service.

## Features

- **Profile editor (GUI):** one place to enter your resume path and all the
  common application answers.
- **Resume upload:** automatically attaches your resume file to file-upload
  fields on the page.
- **Common questions covered:** name, email, phone, address, age, birth year,
  date of birth, work authorization, visa sponsorship, years of experience,
  desired salary, LinkedIn/GitHub/portfolio, plus EEO questions (gender, race,
  veteran & disability status), and "how did you hear about us".
- **Browser selection:** choose Chrome, Firefox, or Edge. Optionally use your
  real browser profile so you stay logged in to job sites.
- **Review-before-submit:** by default it fills and pauses so you can check.

## Requirements

- Python 3.9+
- One of: Google Chrome, Mozilla Firefox, or Microsoft Edge installed
- Python packages from `requirements.txt`

Selenium 4 auto-downloads the matching browser driver, so you don't need to
install chromedriver/geckodriver manually.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

1. Fill in your details and pick your resume file.
2. Choose your browser.
3. Click **Save Profile** (stored locally in `config.json` — git-ignored).
4. Paste a job application URL and click **Open & Auto-Fill**.
5. Review the filled form in the browser, then submit it yourself.

Your data never leaves your machine — the profile is a local JSON file and the
browser runs locally.

## Project layout

```
app.py                  Entry point (launches the GUI)
autoapply/
  profile.py            Profile data model + load/save
  browser.py            Browser driver factory (Chrome/Firefox/Edge)
  filler.py             Form-field detection and autofill heuristics
  gui.py                Tkinter GUI
config.example.json     Example profile shape
```
