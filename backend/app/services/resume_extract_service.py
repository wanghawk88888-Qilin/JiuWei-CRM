"""Rule-based resume extraction service.

Extracts phone, email, education, and skill keywords from resume text
using regular expressions and keyword matching.
"""

import re

# -- Regular expression patterns --------------------------------------------

# China mainland mobile phone number: 1[3-9]XXXXXXXXX
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")

# Common email pattern
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# -- Keyword lists ----------------------------------------------------------

EDUCATION_KEYWORDS = [
    "博士",
    "硕士",
    "研究生",
    "本科",
    "大专",
    "专科",
    "高中",
]

SKILL_KEYWORDS = [
    "Python",
    "Java",
    "JavaScript",
    "测试",
    "自动化测试",
    "AI",
    "机器学习",
    "深度学习",
    "大模型",
    "LLM",
]


def extract_phone(text: str) -> str | None:
    """Extract the first China mainland mobile phone number from text."""
    match = PHONE_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def extract_email(text: str) -> str | None:
    """Extract the first email address from text."""
    match = EMAIL_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def extract_education(text: str) -> str | None:
    """Extract education level by keyword matching.

    Returns the highest-level match found (博士 > 硕士/研究生 > 本科 > 大专/专科 > 高中).
    """
    priority = {
        "博士": 5,
        "硕士": 4,
        "研究生": 4,
        "本科": 3,
        "大专": 2,
        "专科": 2,
        "高中": 1,
    }
    best = None
    best_priority = 0
    for keyword, pri in priority.items():
        if keyword in text and pri > best_priority:
            best = keyword
            best_priority = pri
    return best


def extract_skills(text: str) -> list[str]:
    """Extract skill keywords from text.

    Returns a deduplicated list of matched skill keywords.
    """
    found: list[str] = []
    for keyword in SKILL_KEYWORDS:
        if keyword.lower() in text.lower():
            found.append(keyword)
    return found


def extract_name_from_resume(text: str) -> str | None:
    """Try to extract a name from the first non-empty line of the resume.

    This is a naive heuristic — real name extraction would need NER/AI.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None
    # The first line often contains the candidate's name in Chinese resumes
    first_line = lines[0]
    # Heuristic: if the first line is short (2-4 Chinese characters), treat it as name
    # Filter out lines that look like titles/headers
    skip_keywords = ["简历", "个人", "求职", "应聘", "RESUME", "CV", "个人简历", "求职简历"]
    for kw in skip_keywords:
        if kw.lower() in first_line.lower():
            # Try the next meaningful line
            for line in lines[1:5]:
                line = line.strip()
                if line and not any(kw2.lower() in line.lower() for kw2 in skip_keywords):
                    # If it looks like a name (2-4 chars, no numbers, no special chars)
                    if 2 <= len(line) <= 10 and not re.search(r"[0-9@:/]", line):
                        return line
            return None
    # Simple check: if the line is short enough to be a name
    if 2 <= len(first_line) <= 10 and not re.search(r"[0-9@:/]", first_line):
        return first_line
    return None


def extract_all(text: str) -> dict:
    """Run all rule-based extractions on the given text.

    Returns a dict with extracted fields.
    """
    phone = extract_phone(text)
    email = extract_email(text)
    education = extract_education(text)
    skills = extract_skills(text)
    name = extract_name_from_resume(text)

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "education": education,
        "skills": ", ".join(skills) if skills else None,
    }
