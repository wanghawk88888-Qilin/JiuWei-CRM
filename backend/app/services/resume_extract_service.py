"""Rule-based resume extraction service.

Since v0.2.1 the actual rules live in :mod:`app.services.resume_field_rules`,
which adds layered name detection, phone normalisation and confidence /
conflict reporting. This module stays as the stable entry point used by the
single-resume import flow, so its function names and return shapes are
unchanged.
"""

from app.services import resume_field_rules
from app.services.resume_field_rules import (  # re-exported for compatibility
    EMAIL_RE as EMAIL_PATTERN,
    PHONE_STRICT_RE,
    extract_education,
    extract_email,
    extract_skills,
    normalize_phone,
)

# Kept for backwards compatibility with code/tests that imported these names.
PHONE_PATTERN = PHONE_STRICT_RE
EDUCATION_KEYWORDS = list(resume_field_rules.EDUCATION_PRIORITY.keys())
SKILL_KEYWORDS = list(resume_field_rules.SKILL_KEYWORDS)

__all__ = [
    "EDUCATION_KEYWORDS",
    "EMAIL_PATTERN",
    "PHONE_PATTERN",
    "SKILL_KEYWORDS",
    "extract_all",
    "extract_education",
    "extract_email",
    "extract_name_from_resume",
    "extract_phone",
    "extract_profile",
    "extract_skills",
    "normalize_phone",
]


def extract_phone(text: str) -> str | None:
    """Extract the candidate's mainland mobile number, normalised.

    Returns None when the number is missing or ambiguous — the caller must not
    guess. Formats accepted: 13812345678, 138 1234 5678, 138-1234-5678,
    +86 13812345678, +86-138-1234-5678.
    """
    return resume_field_rules.detect_phone(
        resume_field_rules.split_lines(text or "")
    )["value"]


def extract_name_from_resume(text: str) -> str | None:
    """Extract the candidate's name using the layered rules.

    Returns None when no confident candidate exists or candidates conflict.
    """
    lines = resume_field_rules.split_lines(text or "")
    phone = resume_field_rules.detect_phone(lines)
    return resume_field_rules.detect_name(lines, phone.get("line"))["value"]


def extract_profile(text: str) -> dict:
    """Full extraction including confidence and conflict metadata.

    See :func:`app.services.resume_field_rules.extract_profile`.
    """
    return resume_field_rules.extract_profile(text)


def extract_all(text: str) -> dict:
    """Run all rule-based extractions on the given text.

    Legacy shape used by the single-resume import flow.
    """
    profile = resume_field_rules.extract_profile(text)
    return {
        "name": profile["name"],
        "phone": profile["phone"],
        "email": profile["email"],
        "education": profile["education"],
        "skills": profile["skills"],
    }
