"""Profile data model plus local load/save helpers.

The profile holds everything AutoApply needs to fill out an application:
the resume path, contact details, and answers to the questions most job
applications ask. It is persisted as a plain JSON file on the user's machine
(``config.json`` by default) and is git-ignored so personal data never leaves
the computer.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Supported browsers for the picker. Keys are stored in the profile; values are
# the human-friendly labels shown in the GUI dropdown.
SUPPORTED_BROWSERS = {
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "edge": "Microsoft Edge",
}


@dataclass
class Profile:
    """Everything we know about the applicant.

    Every field is optional (defaults to an empty string) so a partially filled
    profile still works — AutoApply only fills the fields it has answers for.
    """

    # --- Files ---
    resume_path: str = ""
    cover_letter_path: str = ""

    # --- Identity / contact ---
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""

    # --- Address ---
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = ""

    # --- Common screening questions ---
    age: str = ""
    birth_year: str = ""
    date_of_birth: str = ""  # free-form, e.g. 1995-04-21 or 04/21/1995
    work_authorized: str = ""  # "Yes" / "No"
    needs_sponsorship: str = ""  # "Yes" / "No"
    years_experience: str = ""
    desired_salary: str = ""
    earliest_start_date: str = ""
    how_did_you_hear: str = ""

    # --- Links ---
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

    # --- EEO / voluntary self-identification ---
    gender: str = ""
    race_ethnicity: str = ""
    veteran_status: str = ""
    disability_status: str = ""

    # --- Tool settings ---
    browser: str = "chrome"
    use_existing_profile: bool = False  # reuse the real browser profile (stay logged in)
    auto_submit: bool = False  # if False, fill the form but let the user submit

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> "Profile":
        """Load a profile from JSON, ignoring unknown/legacy keys."""
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: str = DEFAULT_CONFIG_PATH) -> None:
        """Write the profile to JSON."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)
