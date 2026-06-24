"""Form-field detection and autofill heuristics.

The autofiller walks every input/textarea/select on the current page, works out
what each field is *asking for* by looking at its label, name, id, placeholder
and aria-label, and fills in the matching answer from the profile. It is
deliberately conservative: it only touches fields it can confidently match, it
never clears a field the user already filled, and it stops before submitting
unless explicitly told to submit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


@dataclass
class FillResult:
    filled: list[str]
    skipped_resume: bool
    notes: list[str]


# Ordered list of (profile attribute, keyword patterns). Order matters: more
# specific fields (e.g. birth_year) must come before generic ones (e.g. year).
# A field on the page matches a rule if ANY of its keywords appears in the
# field's combined label text.
FIELD_RULES: list[tuple[str, list[str]]] = [
    ("email", ["email", "e-mail"]),
    ("phone", ["phone", "mobile", "telephone", "cell"]),
    ("first_name", ["first name", "firstname", "given name", "fname"]),
    ("last_name", ["last name", "lastname", "surname", "family name", "lname"]),
    ("full_name", ["full name", "your name", "legal name", "name"]),
    ("birth_year", ["birth year", "year of birth", "yob"]),
    ("date_of_birth", ["date of birth", "dob", "birth date", "birthday", "birthdate"]),
    ("age", ["age"]),
    ("address", ["street", "address line", "address"]),
    ("city", ["city", "town"]),
    ("state", ["state", "province", "region"]),
    ("zip_code", ["zip", "postal", "postcode"]),
    ("country", ["country"]),
    ("years_experience", ["years of experience", "years experience", "experience (years)"]),
    ("desired_salary", ["desired salary", "salary expectation", "expected salary", "compensation"]),
    ("earliest_start_date", ["start date", "available", "availability", "notice period"]),
    ("work_authorized", ["authorized to work", "work authorization", "legally authorized", "right to work"]),
    ("needs_sponsorship", ["sponsorship", "require sponsorship", "visa sponsor"]),
    ("linkedin", ["linkedin"]),
    ("github", ["github"]),
    ("portfolio", ["portfolio", "website", "personal site", "url"]),
    ("how_did_you_hear", ["how did you hear", "how you heard", "referral source", "source"]),
    ("gender", ["gender", "sex"]),
    ("race_ethnicity", ["race", "ethnicity", "ethnic"]),
    ("veteran_status", ["veteran", "military"]),
    ("disability_status", ["disability", "disabled"]),
]


def _label_text(driver, element) -> str:
    """Build the best-guess label for a form field, lowercased.

    Combines: associated <label for=...>, wrapping <label>, aria-label,
    placeholder, name, id, and the field's own visible text (for selects).
    """
    parts: list[str] = []
    for attr in ("aria-label", "placeholder", "name", "id", "title"):
        val = element.get_attribute(attr)
        if val:
            parts.append(val)

    el_id = element.get_attribute("id")
    if el_id:
        try:
            lbl = driver.find_element(By.CSS_SELECTOR, f"label[for='{el_id}']")
            parts.append(lbl.text)
        except Exception:
            pass

    # Wrapping <label> or nearby text.
    try:
        parent = element.find_element(By.XPATH, "./ancestor::label[1]")
        parts.append(parent.text)
    except Exception:
        pass

    return " ".join(p for p in parts if p).lower()


def _match_attribute(profile, label: str) -> str | None:
    """Return the profile attribute name whose keywords match ``label``."""
    for attr, keywords in FIELD_RULES:
        if any(kw in label for kw in keywords):
            return attr
    return None


def _value_for(profile, attr: str) -> str:
    if attr == "full_name":
        return profile.full_name
    return str(getattr(profile, attr, "") or "")


def _fill_text(element, value: str) -> bool:
    """Type ``value`` into a text-like field if it's empty. Returns True if filled."""
    if element.get_attribute("value"):
        return False  # don't overwrite what the user already entered
    try:
        element.clear()
    except Exception:
        pass
    element.send_keys(value)
    return True


def _fill_select(element, value: str) -> bool:
    """Choose the option in a <select> that best matches ``value``."""
    select = Select(element)
    target = value.strip().lower()
    for option in select.options:
        text = (option.text or "").strip().lower()
        if not text:
            continue
        if target == text or target in text or text in target:
            select.select_by_visible_text(option.text)
            return True
    return False


def _fill_radio_or_checkbox(driver, element, value: str) -> bool:
    """For radio groups, click the option whose label matches ``value``."""
    label = _label_text(driver, element)
    target = value.strip().lower()
    if target and target in label:
        if not element.is_selected():
            element.click()
        return True
    return False


def autofill(driver, profile) -> FillResult:
    """Fill every recognizable field on the current page from ``profile``."""
    filled: list[str] = []
    notes: list[str] = []
    skipped_resume = True

    # 1) Resume / cover-letter file uploads.
    skipped_resume = not _attach_files(driver, profile, filled, notes)

    # 2) Text inputs and textareas.
    text_selector = (
        "input[type='text'], input[type='email'], input[type='tel'], "
        "input[type='url'], input[type='number'], input[type='date'], "
        "input:not([type]), textarea"
    )
    for element in driver.find_elements(By.CSS_SELECTOR, text_selector):
        try:
            if not element.is_displayed() or not element.is_enabled():
                continue
            label = _label_text(driver, element)
            attr = _match_attribute(profile, label)
            if not attr:
                continue
            value = _value_for(profile, attr)
            if value and _fill_text(element, value):
                filled.append(attr)
        except Exception as exc:  # never let one bad field abort the run
            notes.append(f"input error: {exc}")

    # 3) Dropdowns.
    for element in driver.find_elements(By.TAG_NAME, "select"):
        try:
            if not element.is_displayed() or not element.is_enabled():
                continue
            label = _label_text(driver, element)
            attr = _match_attribute(profile, label)
            if not attr:
                continue
            value = _value_for(profile, attr)
            if value and _fill_select(element, value):
                filled.append(attr)
        except Exception as exc:
            notes.append(f"select error: {exc}")

    # 4) Radio buttons (Yes/No screening + EEO questions).
    for element in driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
        try:
            if not element.is_displayed() or not element.is_enabled():
                continue
            label = _label_text(driver, element)
            attr = _match_attribute(profile, label)
            if not attr:
                continue
            value = _value_for(profile, attr)
            if value and _fill_radio_or_checkbox(driver, element, value):
                filled.append(attr)
        except Exception as exc:
            notes.append(f"radio error: {exc}")

    return FillResult(filled=sorted(set(filled)), skipped_resume=skipped_resume, notes=notes)


def _attach_files(driver, profile, filled: list[str], notes: list[str]) -> bool:
    """Send resume / cover-letter paths to file-upload inputs. Returns True if a
    resume was attached."""
    attached_resume = False
    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if not file_inputs:
        return False

    resume = profile.resume_path
    cover = profile.cover_letter_path

    for element in file_inputs:
        try:
            label = _label_text(driver, element)
            is_cover = any(k in label for k in ("cover", "letter"))
            path = cover if (is_cover and cover) else resume
            if not path:
                continue
            if not os.path.exists(path):
                notes.append(f"file not found: {path}")
                continue
            element.send_keys(os.path.abspath(path))
            if is_cover and cover:
                filled.append("cover_letter")
            else:
                filled.append("resume")
                attached_resume = True
        except Exception as exc:
            notes.append(f"file upload error: {exc}")

    return attached_resume
