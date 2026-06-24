"""Tkinter GUI for editing the profile and launching the autofiller."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .profile import SUPPORTED_BROWSERS, Profile

# Form layout: (profile attribute, label, widget kind, options).
# kind is "entry", "file", "choice".
SECTIONS: list[tuple[str, list[tuple[str, str, str, list[str]]]]] = [
    ("Files", [
        ("resume_path", "Resume file", "file", []),
        ("cover_letter_path", "Cover letter (optional)", "file", []),
    ]),
    ("Contact", [
        ("first_name", "First name", "entry", []),
        ("last_name", "Last name", "entry", []),
        ("email", "Email", "entry", []),
        ("phone", "Phone", "entry", []),
    ]),
    ("Address", [
        ("address", "Street address", "entry", []),
        ("city", "City", "entry", []),
        ("state", "State / Province", "entry", []),
        ("zip_code", "ZIP / Postal code", "entry", []),
        ("country", "Country", "entry", []),
    ]),
    ("Common application questions", [
        ("age", "Age", "entry", []),
        ("birth_year", "Birth year", "entry", []),
        ("date_of_birth", "Date of birth", "entry", []),
        ("work_authorized", "Authorized to work?", "choice", ["Yes", "No"]),
        ("needs_sponsorship", "Need visa sponsorship?", "choice", ["Yes", "No"]),
        ("years_experience", "Years of experience", "entry", []),
        ("desired_salary", "Desired salary", "entry", []),
        ("earliest_start_date", "Earliest start date", "entry", []),
        ("how_did_you_hear", "How did you hear about us?", "entry", []),
    ]),
    ("Links", [
        ("linkedin", "LinkedIn URL", "entry", []),
        ("github", "GitHub URL", "entry", []),
        ("portfolio", "Portfolio / website", "entry", []),
    ]),
    ("Voluntary self-identification (EEO)", [
        ("gender", "Gender", "entry", []),
        ("race_ethnicity", "Race / ethnicity", "entry", []),
        ("veteran_status", "Veteran status", "entry", []),
        ("disability_status", "Disability status", "entry", []),
    ]),
]


class AutoApplyGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.profile = Profile.load()
        self.vars: dict[str, tk.StringVar] = {}

        root.title("AutoApply — Job Application Autofiller")
        root.geometry("560x720")

        self._build_scrollable_body()
        self._build_form()
        self._build_controls()

    # --- layout scaffolding ---
    def _build_scrollable_body(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)
        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

    def _build_form(self) -> None:
        for section_title, rows in SECTIONS:
            header = ttk.Label(self.body, text=section_title, font=("TkDefaultFont", 11, "bold"))
            header.pack(anchor="w", padx=12, pady=(14, 4))
            for attr, label, kind, options in rows:
                self._build_row(attr, label, kind, options)

    def _build_row(self, attr: str, label: str, kind: str, options: list[str]) -> None:
        row = ttk.Frame(self.body)
        row.pack(fill="x", padx=12, pady=2)
        ttk.Label(row, text=label, width=24, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(getattr(self.profile, attr, "") or ""))
        self.vars[attr] = var

        if kind == "choice":
            ttk.Combobox(row, textvariable=var, values=options, state="readonly", width=28).pack(
                side="left", fill="x", expand=True
            )
        elif kind == "file":
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="Browse", command=lambda v=var: self._pick_file(v)).pack(side="left", padx=(4, 0))
        else:
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _build_controls(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", side="bottom", padx=12, pady=10)

        # Browser picker.
        browser_row = ttk.Frame(bar)
        browser_row.pack(fill="x", pady=(0, 6))
        ttk.Label(browser_row, text="Browser", width=24, anchor="w").pack(side="left")
        self.browser_var = tk.StringVar(value=SUPPORTED_BROWSERS.get(self.profile.browser, "Google Chrome"))
        ttk.Combobox(
            browser_row, textvariable=self.browser_var,
            values=list(SUPPORTED_BROWSERS.values()), state="readonly", width=28,
        ).pack(side="left", fill="x", expand=True)

        # Toggles.
        self.existing_profile_var = tk.BooleanVar(value=self.profile.use_existing_profile)
        ttk.Checkbutton(
            bar, text="Use my real browser profile (stay logged in)",
            variable=self.existing_profile_var,
        ).pack(anchor="w")
        self.auto_submit_var = tk.BooleanVar(value=self.profile.auto_submit)
        ttk.Checkbutton(
            bar, text="Auto-submit after filling (off = review first)",
            variable=self.auto_submit_var,
        ).pack(anchor="w", pady=(0, 6))

        # URL + actions.
        url_row = ttk.Frame(bar)
        url_row.pack(fill="x", pady=(2, 6))
        ttk.Label(url_row, text="Job URL", width=24, anchor="w").pack(side="left")
        self.url_var = tk.StringVar()
        ttk.Entry(url_row, textvariable=self.url_var).pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(bar)
        actions.pack(fill="x")
        ttk.Button(actions, text="Save Profile", command=self.save_profile).pack(side="left")
        ttk.Button(actions, text="Open & Auto-Fill", command=self.run_autofill).pack(side="right")

        self.status = ttk.Label(bar, text="Ready.", foreground="gray")
        self.status.pack(anchor="w", pady=(8, 0))

    # --- actions ---
    def _pick_file(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            title="Select file",
            filetypes=[("Documents", "*.pdf *.doc *.docx *.txt"), ("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _collect(self) -> Profile:
        for attr, var in self.vars.items():
            setattr(self.profile, attr, var.get().strip())
        label_to_key = {v: k for k, v in SUPPORTED_BROWSERS.items()}
        self.profile.browser = label_to_key.get(self.browser_var.get(), "chrome")
        self.profile.use_existing_profile = self.existing_profile_var.get()
        self.profile.auto_submit = self.auto_submit_var.get()
        return self.profile

    def save_profile(self) -> None:
        self._collect().save()
        self._set_status("Profile saved to config.json.")

    def run_autofill(self) -> None:
        profile = self._collect()
        profile.save()
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste the job application URL first.")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        self._set_status("Launching browser…")
        # Run in a thread so the GUI stays responsive.
        threading.Thread(target=self._do_autofill, args=(profile, url), daemon=True).start()

    def _do_autofill(self, profile: Profile, url: str) -> None:
        try:
            from .browser import create_driver
            from .filler import autofill

            driver = create_driver(profile.browser, profile.use_existing_profile)
            driver.get(url)
            result = autofill(driver, profile)

            summary = f"Filled {len(result.filled)} field(s): {', '.join(result.filled) or 'none'}."
            if result.skipped_resume:
                summary += " (no resume upload field found)"
            if not profile.auto_submit:
                summary += " Review the page, then submit yourself."
            self._set_status(summary)
        except Exception as exc:
            self._set_status(f"Error: {exc}")
            messagebox.showerror("AutoApply error", str(exc))

    def _set_status(self, text: str) -> None:
        # Tkinter widgets must be touched on the main thread.
        self.root.after(0, lambda: self.status.config(text=text))


def launch() -> None:
    root = tk.Tk()
    AutoApplyGUI(root)
    root.mainloop()
