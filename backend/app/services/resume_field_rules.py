"""Deterministic resume field rules — layered extraction with confidence scoring.

This module is the *Rule Parser -> Validator -> Confidence / Conflict Detector*
stage of the resume pipeline:

    Text Extractor
        -> Rule Parser            (this module)
        -> Validator              (this module)
        -> Confidence / Conflict  (this module)
        -> AI Enhancer            (future — see llm_extract_service)
        -> Human Review

Everything here is pure and deterministic: no database, no filesystem, no
network. That keeps it unit-testable and keeps the AI extension point clean —
a future AI Enhancer consumes the ExtractedProfile produced here and may raise
confidence or resolve conflicts, but never replaces these rules.

Design principle for v0.2.1:
    Never guess a name or a phone number. When the evidence is ambiguous we
    return no value plus an explicit conflict code, so the file lands in human
    review instead of silently creating a wrong Lead.
"""

import json
import re

# -- Confidence levels ------------------------------------------------------

CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_MISSING = "missing"

# Only `high` is auto-confirmable. Everything else goes to human review.
AUTO_CONFIRMABLE_CONFIDENCE = {CONF_HIGH}

# -- Conflict codes ---------------------------------------------------------

CODE_NAME_CONFLICT = "NAME_CONFLICT"
CODE_PHONE_CONFLICT = "PHONE_CONFLICT"
CODE_NAME_MISSING = "NAME_MISSING"
CODE_PHONE_MISSING = "PHONE_MISSING"

# Leading non-empty lines treated as the resume's "personal info" zone.
HEADER_ZONE_LINES = 15

# -- Character class helpers ------------------------------------------------

CJK_RE = re.compile(r"^[一-鿿·]+$")
_CJK_CHAR_RE = re.compile(r"[一-鿿]")

# ---------------------------------------------------------------------------
# Name rules
# ---------------------------------------------------------------------------

# Priority 1: explicit label. Handles "姓名：", "姓 名:", "姓名 张三", "Name: ".
NAME_LABEL_RE = re.compile(
    r"(?:个人姓名|真实姓名|中文姓名|候选人姓名|姓\s{0,3}名|名\s{0,3}字|\bName\b|\bNAME\b)",
    re.IGNORECASE,
)

# Words that can never be a person's name, matched as substrings.
NAME_BLOCK_SUBSTRINGS = (
    "简历", "个人信息", "基本信息", "基本资料", "个人资料", "个人评价", "自我评价",
    "个人总结", "个人简介", "自我介绍", "职业总结", "职业概述",
    "求职", "应聘", "联系方式", "联系电话", "教育背景", "教育经历", "工作经历",
    "工作经验", "项目经验", "项目经历", "实习经历", "专业技能", "技能特长",
    "证书", "荣誉", "获奖", "期望", "意向", "姓名", "性别", "年龄", "民族",
    "籍贯", "学历", "专业", "学校", "院校", "毕业", "电话", "手机", "邮箱",
    "地址", "婚姻", "政治面貌", "出生", "身高", "爱好", "特长", "培训",
    "resume", "curriculum", "vitae", "profile", "contact", "education",
    "experience", "skills", "objective",
    # Education levels and other high-frequency resume vocabulary. Without
    # these, a bare "本科" line in the header zone reads as a 2-character
    # Chinese name.
    "本科", "专科", "大专", "硕士", "博士", "研究生", "学士", "中专", "高中",
    "初中", "小学", "中学", "高职", "统招", "全日制", "在读", "应届",
    "已婚", "未婚", "党员", "团员", "群众", "汉族", "户籍", "现居", "所在",
)

# Organisation-like suffixes — "北京大学" is not a name.
NAME_BLOCK_SUFFIXES = (
    "大学", "学院", "学校", "中学", "高中", "小学", "公司", "集团", "有限",
    "科技", "中心", "研究所", "研究院", "银行", "医院", "工作室", "事业部",
    "部门", "分公司", "股份", "企业", "机构", "基地",
)

# Location names — a bare city/province in the resume header is a place, not a
# person. This is deliberately a *closed* set of the four municipalities plus
# the province-level short names, matched exactly, so it can never reject a name
# that merely contains a location string ("王北京" still parses as a name).
LOCATION_BLOCK_WORDS = frozenset({
    "北京", "上海", "天津", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽",
    "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古",
    "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
})

# Administrative-region suffixes — "北京市" / "河北省" / "海淀区" / "朝阳县"
# are locations, never names. No legitimate Chinese name ends in one of these,
# so this stays deterministic and free of name-collision risk.
LOCATION_SUFFIXES = ("省", "市", "区", "县", "镇", "乡", "州", "旗", "盟")

# Tokens that terminate an inline field value: "姓名：张三 | 性别：男".
_VALUE_SEPARATOR_RE = re.compile(r"[|｜/\\,，;；、\t]|\s{2,}")

# Labels of *other* fields — a name value stops when the next label starts.
_NEXT_LABEL_RE = re.compile(
    r"性别|年龄|民族|籍贯|出生|生日|电话|手机|邮箱|邮件|地址|学历|专业|学校|"
    r"院校|毕业|婚姻|政治面貌|身高|求职|应聘|意向|期望|微信|QQ|Email|E-mail|"
    r"Tel|Phone|Mobile|Gender|Age",
    re.IGNORECASE,
)


def _is_all_cjk(text: str) -> bool:
    """True when every character is a CJK ideograph (or the name separator ·)."""
    return bool(text) and bool(CJK_RE.match(text))


def _is_location_name(name: str) -> bool:
    """Reject administrative-region names that are never person names.

    ``name`` must already be a normalised, space-free CJK string. A bare
    municipality/province name ("北京") or a name ending in an administrative
    suffix ("北京市", "海淀区") is a location, not a candidate. The rule is
    exact-match/suffix only — it never rejects a name that merely contains a
    location string, so legitimate names like 王北京 survive.
    """
    if name in LOCATION_BLOCK_WORDS:
        return True
    return name.endswith(LOCATION_SUFFIXES)


def normalize_name(raw: str | None) -> str | None:
    """Normalise a raw name candidate.

    Collapses whitespace, and for pure-CJK names removes the internal spaces
    used for typographic alignment:  "张 三" -> "张三",  "王 小 明" -> "王小明".
    Latin names keep their single spaces: "Zhang San" -> "Zhang San".
    """
    if raw is None:
        return None
    text = raw.strip().strip(":：.-_*•")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    without_spaces = text.replace(" ", "")
    if _is_all_cjk(without_spaces):
        return without_spaces
    return text


def is_plausible_name(name: str | None) -> bool:
    """Validate a normalised name candidate.

    Rejects digits, punctuation, section headings, and organisation names.
    """
    if not name:
        return False
    if len(name) > 20:
        return False
    if re.search(r"[0-9@:：/\\|｜<>()（）\[\]{}#$%^&*+=~`\"'？?！!]", name):
        return False

    lowered = name.lower()
    for blocked in NAME_BLOCK_SUBSTRINGS:
        if blocked.lower() in lowered:
            return False
    for suffix in NAME_BLOCK_SUFFIXES:
        if name.endswith(suffix):
            return False

    without_spaces = name.replace(" ", "")
    if _is_all_cjk(without_spaces):
        if _is_location_name(without_spaces):
            return False
        return 2 <= len(without_spaces) <= 6
    if re.fullmatch(r"[A-Za-z][A-Za-z .'\-·]{1,38}", name):
        return sum(1 for c in name if c.isalpha()) >= 2
    return False


def _cut_field_value(rest: str) -> str:
    """Trim an inline field value at the first separator or next field label."""
    value = rest.strip().lstrip(":：").strip()
    if not value:
        return ""

    sep = _VALUE_SEPARATOR_RE.search(value)
    if sep:
        value = value[: sep.start()]

    nxt = _NEXT_LABEL_RE.search(value)
    if nxt:
        value = value[: nxt.start()]

    return value.strip()


def _labeled_name_candidates(lines: list[str]) -> list[tuple[str, int]]:
    """Priority 1 — names introduced by an explicit label."""
    found: list[tuple[str, int]] = []
    for idx, line in enumerate(lines):
        match = NAME_LABEL_RE.search(line)
        if not match:
            continue

        value = _cut_field_value(line[match.end():])
        # Table layouts put the label and the value on separate lines/cells.
        if not value and idx + 1 < len(lines):
            value = _cut_field_value(lines[idx + 1])

        name = normalize_name(value)
        if is_plausible_name(name):
            found.append((name, idx))
    return found


def _header_name_candidates(
    lines: list[str],
    phone_line: int | None,
    email_line: int | None,
) -> list[tuple[str, int, int]]:
    """Priority 2 — names sitting in the personal-info zone at the top.

    Returns (name, line_index, score) triples. Score encodes how strongly the
    layout suggests this really is the candidate's name.
    """
    candidates: list[tuple[str, int, int]] = []
    for idx, line in enumerate(lines[:HEADER_ZONE_LINES]):
        if len(line) > 24:
            continue

        name = normalize_name(_cut_field_value(line))
        if not is_plausible_name(name):
            continue

        score = 0
        if idx == 0:
            score += 3
        elif idx <= 2:
            score += 2
        elif idx <= 5:
            score += 1

        # Adjacency to contact details is strong evidence of a header block.
        for contact_line in (phone_line, email_line):
            if contact_line is not None and abs(idx - contact_line) <= 5:
                score += 2
                break

        without_spaces = name.replace(" ", "")
        if _is_all_cjk(without_spaces) and 2 <= len(without_spaces) <= 4:
            score += 1

        candidates.append((name, idx, score))
    return candidates


def detect_name(
    lines: list[str],
    phone_line: int | None = None,
    email_line: int | None = None,
) -> dict:
    """Run the layered name detection.

    Returns {"value", "confidence", "conflict", "candidates"}.
    A conflict always forces value=None so no Lead can be created from a guess.
    """
    labeled = _labeled_name_candidates(lines)
    distinct_labeled = list(dict.fromkeys(name for name, _ in labeled))

    if len(distinct_labeled) == 1:
        return {
            "value": distinct_labeled[0],
            "confidence": CONF_HIGH,
            "conflict": None,
            "candidates": distinct_labeled,
        }
    if len(distinct_labeled) > 1:
        return {
            "value": None,
            "confidence": CONF_LOW,
            "conflict": CODE_NAME_CONFLICT,
            "candidates": distinct_labeled,
        }

    # Priority 2 — identity block: a bare name heading a personal-info block
    # anywhere in the document (PDF extraction often drops the name far from
    # the first lines even when it visually heads the page).
    identity = _identity_block_name_candidates(lines)
    if identity:
        high_names = sorted({name for name, _idx, _score, high in identity if high})
        if len(high_names) == 1:
            return {
                "value": high_names[0],
                "confidence": CONF_HIGH,
                "conflict": None,
                "candidates": high_names,
            }
        if len(high_names) > 1:
            return {
                "value": None,
                "confidence": CONF_LOW,
                "conflict": CODE_NAME_CONFLICT,
                "candidates": high_names,
            }

    header = _header_name_candidates(lines, phone_line, email_line)
    if not header:
        if identity:
            # A weak identity-block name is a better suggestion than nothing,
            # but it is never auto-confirmable.
            best_by_name: dict[str, int] = {}
            for name, _idx, score, _high in identity:
                if score > best_by_name.get(name, -1):
                    best_by_name[name] = score
            ordered = sorted(best_by_name, key=lambda n: -best_by_name[n])
            return {
                "value": ordered[0],
                "confidence": CONF_MEDIUM,
                "conflict": None,
                "candidates": ordered,
            }
        return {
            "value": None,
            "confidence": CONF_MISSING,
            "conflict": CODE_NAME_MISSING,
            "candidates": [],
        }

    # Keep the best score per distinct name.
    best_by_name: dict[str, int] = {}
    for name, _idx, score in header:
        if score > best_by_name.get(name, -1):
            best_by_name[name] = score

    top_score = max(best_by_name.values())
    winners = [name for name, score in best_by_name.items() if score == top_score]
    ordered = sorted(best_by_name, key=lambda n: -best_by_name[n])

    if len(winners) > 1:
        return {
            "value": None,
            "confidence": CONF_LOW,
            "conflict": CODE_NAME_CONFLICT,
            "candidates": ordered,
        }

    # A single unambiguous header name adjacent to contact info is as good as
    # an explicit label; anything weaker still needs a human to look at it.
    confidence = CONF_HIGH if top_score >= 5 else CONF_MEDIUM
    return {
        "value": winners[0],
        "confidence": confidence,
        "conflict": None,
        "candidates": ordered,
    }


# ---------------------------------------------------------------------------
# Phone rules
# ---------------------------------------------------------------------------

# Accepts 13812345678 / 138 1234 5678 / 138-1234-5678 / +86 13812345678 /
# +86-138-1234-5678. Digit lookaround stops matches inside ID card numbers.
PHONE_RAW_RE = re.compile(
    r"(?<![0-9])(?:\+?86[\s\-]?)?(1[3-9][0-9](?:[\s\-]?[0-9]){8})(?![0-9])"
)

# Canonical form check.
PHONE_STRICT_RE = re.compile(r"^1[3-9]\d{9}$")

PHONE_STRONG_LABELS = ("手机号码", "手机号", "手机", "移动电话", "本人电话", "mobile")
PHONE_WEAK_LABELS = (
    "联系电话", "联系方式", "电话", "联络电话", "tel", "phone", "contact",
)
# Contexts that mean the number belongs to somebody other than the candidate.
PHONE_NEGATIVE_LABELS = (
    "紧急联系", "紧急联络", "联系人", "公司电话", "座机", "固话", "项目联系",
    "推荐人", "介绍人", "家长", "父亲", "母亲", "配偶", "客服", "招聘", "hr电话",
    "前台", "总机", "传真",
)


def normalize_phone(raw: str | None) -> str | None:
    """Normalise a raw phone string to the canonical 11-digit mainland form."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0086"):
        digits = digits[4:]
    elif digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    if PHONE_STRICT_RE.match(digits):
        return digits
    return None


def is_valid_phone(value: str | None) -> bool:
    """True when value is already a canonical mainland mobile number."""
    return bool(value) and bool(PHONE_STRICT_RE.match(value))


ALL_PHONE_LABELS = PHONE_STRONG_LABELS + PHONE_WEAK_LABELS + PHONE_NEGATIVE_LABELS


def _phone_context(lines: list[str], idx: int) -> str:
    """Context used to classify a phone number found on line ``idx``.

    A line that carries its own label is judged on that label alone. Only a
    bare number line borrows the previous line, which is how table-style
    resumes put "手机号" and the value in separate cells. Without this split, a
    "紧急联系人" label on one line would wrongly poison the number on the next.
    """
    line = lines[idx]
    lowered = line.lower()
    has_own_label = any(label in lowered for label in ALL_PHONE_LABELS)
    if has_own_label or idx == 0:
        return line
    return lines[idx - 1] + " " + line


def _phone_occurrences(lines: list[str]) -> dict[str, dict]:
    """Collect distinct normalised phones with their surrounding context."""
    occurrences: dict[str, dict] = {}

    for idx, line in enumerate(lines):
        for match in PHONE_RAW_RE.finditer(line):
            phone = normalize_phone(match.group(1))
            if not phone:
                continue

            lowered = _phone_context(lines, idx).lower()

            entry = occurrences.setdefault(
                phone,
                {"phone": phone, "line": idx, "strong": False, "weak": False,
                 "negative": False},
            )
            entry["line"] = min(entry["line"], idx)
            if any(label in lowered for label in PHONE_STRONG_LABELS):
                entry["strong"] = True
            if any(label in lowered for label in PHONE_WEAK_LABELS):
                entry["weak"] = True
            if any(label in lowered for label in PHONE_NEGATIVE_LABELS):
                entry["negative"] = True

    return occurrences


def detect_phone(lines: list[str]) -> dict:
    """Run phone detection with context scoring and conflict detection.

    Returns {"value", "confidence", "conflict", "candidates", "line"}.
    """
    occurrences = _phone_occurrences(lines)
    if not occurrences:
        return {
            "value": None,
            "confidence": CONF_MISSING,
            "conflict": CODE_PHONE_MISSING,
            "candidates": [],
            "line": None,
        }

    all_phones = sorted(occurrences, key=lambda p: occurrences[p]["line"])
    # A number labelled as somebody else's is never the candidate's number.
    positives = [p for p in all_phones if not occurrences[p]["negative"]]

    if not positives:
        return {
            "value": None,
            "confidence": CONF_LOW,
            "conflict": CODE_PHONE_CONFLICT,
            "candidates": all_phones,
            "line": occurrences[all_phones[0]]["line"],
        }

    def _in_header(phone: str) -> bool:
        return occurrences[phone]["line"] < HEADER_ZONE_LINES

    if len(positives) == 1:
        phone = positives[0]
        entry = occurrences[phone]
        # Spec: high confidence needs a contact label nearby, the header zone,
        # or an identity block (gender + age + email flanking the number).
        has_context = (
            entry["strong"]
            or entry["weak"]
            or _in_header(phone)
            or _is_identity_block_phone(lines, entry["line"])
        )
        return {
            "value": phone,
            "confidence": CONF_HIGH if has_context else CONF_MEDIUM,
            "conflict": None,
            "candidates": all_phones,
            "line": entry["line"],
        }

    strong = [p for p in positives if occurrences[p]["strong"]]
    if len(strong) == 1:
        return {
            "value": strong[0],
            "confidence": CONF_HIGH,
            "conflict": None,
            "candidates": all_phones,
            "line": occurrences[strong[0]]["line"],
        }

    if not strong:
        header_phones = [p for p in positives if _in_header(p)]
        if len(header_phones) == 1:
            return {
                "value": header_phones[0],
                "confidence": CONF_HIGH,
                "conflict": None,
                "candidates": all_phones,
                "line": occurrences[header_phones[0]]["line"],
            }

    # Several plausible numbers and no way to tell them apart — ask a human.
    return {
        "value": None,
        "confidence": CONF_LOW,
        "conflict": CODE_PHONE_CONFLICT,
        "candidates": all_phones,
        "line": occurrences[positives[0]]["line"],
    }


# ---------------------------------------------------------------------------
# Secondary fields — best effort, never blocking
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

EDUCATION_PRIORITY = {
    "博士": 5, "硕士": 4, "研究生": 4, "本科": 3, "学士": 3,
    "大专": 2, "专科": 2, "高职": 2, "中专": 1, "高中": 1,
}

SKILL_KEYWORDS = (
    "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "SQL",
    "测试", "自动化测试", "性能测试", "AI", "人工智能", "机器学习", "深度学习",
    "大模型", "LLM", "数据分析", "数据挖掘", "运维", "前端", "后端", "算法",
    "产品经理", "UI设计", "项目管理",
)

WECHAT_LABELS = ("微信号", "微信", "wechat", "weixin")
SCHOOL_LABELS = ("毕业院校", "毕业学校", "学校名称", "院校", "学校")
# Only labels that can never be part of a skill/ability/course compound word.
MAJOR_LABELS = ("所学专业", "专业名称", "就读专业", "毕业专业")
# Suffixes that turn a bare "专业" into a section heading / body text rather
# than a field label — "专业技能" is a heading, not "专业：技能".
MAJOR_NEGATIVE_SUFFIXES = (
    "技能", "能力", "特长", "知识", "课程", "证书", "资格", "经验",
)
CITY_LABELS = ("现居城市", "现居住地", "所在城市", "居住地", "现居地", "所在地", "城市")
POSITION_LABELS = ("求职意向", "应聘职位", "意向职位", "目标职位", "职位", "岗位")
COMPANY_LABELS = ("最近公司", "公司名称", "任职公司", "所在公司", "工作单位", "单位名称")
GRADUATION_LABELS = ("毕业时间", "毕业年份", "毕业日期")
WORK_YEARS_LABELS = ("工作年限", "工作经验", "从业年限", "工作年份")
GENDER_LABELS = ("性别",)
AGE_LABELS = ("年龄",)


# ---------------------------------------------------------------------------
# Identity block name detection (Priority 2)
# ---------------------------------------------------------------------------
# A personal identity block clusters the candidate's name with strong contact
# signals (phone / email) and auxiliary bio signals (gender / age / job
# intention / city / wechat). Unlike the header-zone heuristic this scan runs
# over the *whole* document, because PDF extraction often places the name far
# from the first lines even when it visually heads the page.

# Standalone 男 / 女 — the lookaround rejects 男性 / 女生 / 男女 compound words.
IDENTITY_GENDER_RE = re.compile(r"(?<![一-鿿])[男女](?![一-鿿])")
IDENTITY_AGE_RE = re.compile(r"(?<!\d)\d{1,2}\s*(?:岁|周岁)")
# 求职意向 and friends are once-per-resume personal fields, never body text.
IDENTITY_INTENTION_RE = re.compile(
    r"求职意向|应聘职位|意向职位|目标职位|期望职位|求职方向|求职岗位"
)
IDENTITY_CITY_RE = re.compile(
    r"期望城市|意向城市|期望地点|现居城市|所在城市|现居住地|现居地|工作地点"
)
IDENTITY_WECHAT_RE = re.compile(r"微信|wechat|weixin", re.IGNORECASE)


def _identity_block_name_candidates(
    lines: list[str],
) -> list[tuple[str, int, int, bool]]:
    """Find bare name lines that head a personal identity block.

    Scans the whole document. A candidate is a plausible name occupying its own
    line, with identity signals in the 1-3 lines *below* it (a name always sits
    at the top of its identity block). Looking below only keeps section headings
    out: a "个人优势" heading sits *below* the block, so it never sees signals
    under it.

    Returns (name, line_index, score, high_eligible) tuples. ``high_eligible``
    is True only when the evidence clears the auto-confirm bar:
        A) phone + email,  or
        B) phone + at least two auxiliary fields,  or
        phone + 求职意向 (a distinctive once-per-resume personal field).
    """
    candidates: list[tuple[str, int, int, bool]] = []
    for idx, line in enumerate(lines):
        if len(line) > 24:
            continue
        name = normalize_name(line)
        if not is_plausible_name(name):
            continue

        window = lines[idx + 1 : idx + 4]
        window_text = " ".join(window)

        has_phone = any(PHONE_RAW_RE.search(part) for part in window)
        has_email = any(EMAIL_RE.search(part) for part in window)
        has_gender = bool(IDENTITY_GENDER_RE.search(window_text))
        has_age = bool(IDENTITY_AGE_RE.search(window_text))
        has_intention = bool(IDENTITY_INTENTION_RE.search(window_text))
        has_city = bool(IDENTITY_CITY_RE.search(window_text))
        has_wechat = bool(IDENTITY_WECHAT_RE.search(window_text))

        strong = int(has_phone) + int(has_email)
        aux = (
            int(has_gender)
            + int(has_age)
            + int(has_intention)
            + int(has_city)
            + int(has_wechat)
        )
        if strong + aux == 0:
            continue

        high_eligible = (
            (has_phone and has_email)
            or (has_phone and has_intention)
            or (has_phone and aux >= 2)
        )
        score = strong * 3 + aux
        candidates.append((name, idx, score, high_eligible))
    return candidates


def _is_identity_block_phone(lines: list[str], idx: int) -> bool:
    """True when a phone sits in a personal identity block.

    Spec section 14: a bare number flanked by gender + age + email is the
    candidate's own number, so it may be high confidence even without a contact
    label or a header-zone position.
    """
    window = " ".join(lines[max(0, idx - 2) : idx + 3])
    return (
        bool(IDENTITY_GENDER_RE.search(window))
        and bool(IDENTITY_AGE_RE.search(window))
        and bool(EMAIL_RE.search(window))
    )


def _labeled_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
    """Generic 'Label: value' lookup, with table-cell fallback to the next line."""
    for idx, line in enumerate(lines):
        lowered = line.lower()
        for label in labels:
            pos = lowered.find(label.lower())
            if pos < 0:
                continue
            value = _cut_field_value(line[pos + len(label):])
            if not value and idx + 1 < len(lines):
                value = _cut_field_value(lines[idx + 1])
            if value:
                return value
    return None


def extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_education(text: str) -> str | None:
    """Return the highest education level mentioned anywhere in the resume."""
    best: str | None = None
    best_priority = 0
    for keyword, priority in EDUCATION_PRIORITY.items():
        if keyword in text and priority > best_priority:
            best = keyword
            best_priority = priority
    return best


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [kw for kw in SKILL_KEYWORDS if kw.lower() in lowered]


def _extract_gender(lines: list[str], text: str) -> str | None:
    value = _labeled_value(lines, GENDER_LABELS)
    if value:
        if "男" in value:
            return "male"
        if "女" in value:
            return "female"
    header = "\n".join(lines[:HEADER_ZONE_LINES])
    if re.search(r"(?<![一-鿿])男(?![一-鿿])", header):
        return "male"
    if re.search(r"(?<![一-鿿])女(?![一-鿿])", header):
        return "female"
    return None


def _extract_age(lines: list[str], text: str) -> int | None:
    value = _labeled_value(lines, AGE_LABELS)
    if value:
        match = re.search(r"\d{1,2}", value)
        if match:
            age = int(match.group(0))
            if 14 <= age <= 80:
                return age
    match = re.search(r"(\d{1,2})\s*(?:岁|周岁)", text)
    if match:
        age = int(match.group(1))
        if 14 <= age <= 80:
            return age
    return None


def _extract_school(lines: list[str]) -> str | None:
    value = _labeled_value(lines, SCHOOL_LABELS)
    if value and 2 <= len(value) <= 40:
        return value
    for line in lines[:40]:
        stripped = line.strip()
        if 4 <= len(stripped) <= 20 and stripped.endswith(("大学", "学院", "学校")):
            return stripped
    return None


def _extract_major(lines: list[str]) -> str | None:
    """Extract the candidate's major without mistaking skill/ability text.

    A generic substring match on "专业" breaks on section headings like
    "专业技能": it finds "专业" and treats the trailing "技能" as the major.
    Bare "专业" is therefore accepted only when it acts as a field label —
    immediately followed by a colon (专业：/专业:) or by whitespace plus a value
    on the same line (专业  通信工程) — and never when it is part of a compound
    word (专业技能 / 专业能力 / 专业课程, ...). When nothing reliable is found we
    return None rather than guess.
    """
    # 1) Unambiguous labels never appear in a skills/ability/course context.
    value = _labeled_value(lines, MAJOR_LABELS)
    if value:
        return value

    # 2) Bare "专业" only as an explicit field label.
    for idx, line in enumerate(lines):
        pos = line.find("专业")
        while pos != -1:
            prev = line[pos - 1] if pos > 0 else ""
            if prev and _CJK_CHAR_RE.match(prev):
                # Part of a longer word (本专业 / 相关专业) — not a label.
                pos = line.find("专业", pos + 1)
                continue

            nxt = line[pos + 2:pos + 3]
            value = None
            if nxt in (":", "："):
                value = _cut_field_value(line[pos + 3:])
            elif nxt.isspace():
                value = _cut_field_value(line[pos + 2:])
            elif nxt == "" and idx + 1 < len(lines):
                # "专业" alone on a line — table-cell fallback to the next line.
                value = _cut_field_value(lines[idx + 1])

            if value and not value.startswith(MAJOR_NEGATIVE_SUFFIXES):
                if 2 <= len(value) <= 40:
                    return value

            pos = line.find("专业", pos + 1)
    return None


def _extract_work_years(lines: list[str], text: str) -> str | None:
    value = _labeled_value(lines, WORK_YEARS_LABELS)
    if value and len(value) <= 20:
        return value
    match = re.search(r"(\d{1,2})\s*年(?:以上)?(?:工作)?经验", text)
    if match:
        return f"{match.group(1)}年"
    return None


def _extract_graduation_time(lines: list[str], text: str) -> str | None:
    value = _labeled_value(lines, GRADUATION_LABELS)
    if value and len(value) <= 20:
        return value
    match = re.search(r"(\d{4})\s*[年./-]\s*(\d{1,2})?\s*月?\s*毕业", text)
    if match:
        return match.group(0).replace(" ", "")
    return None


def _extract_latest_company(lines: list[str]) -> str | None:
    value = _labeled_value(lines, COMPANY_LABELS)
    if value and 2 <= len(value) <= 40:
        return value
    # Fall back to the first organisation-looking line under a work section.
    in_work_section = False
    for line in lines:
        stripped = line.strip()
        if re.search(r"工作经[历验]|职业经历|工作履历", stripped):
            in_work_section = True
            continue
        if not in_work_section:
            continue
        if re.search(r"教育|项目经[历验]|技能|自我评价", stripped):
            break
        candidate = _cut_field_value(stripped)
        if 3 <= len(candidate) <= 30 and candidate.endswith(
            ("公司", "集团", "科技", "有限", "研究院", "研究所", "银行", "医院")
        ):
            return candidate
    return None


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:limit]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def split_lines(text: str) -> list[str]:
    """Split resume text into non-empty, whitespace-trimmed lines."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_profile(text: str) -> dict:
    """Extract a full candidate profile with confidence and conflict metadata.

    Returns a dict with all LeadDraft-compatible fields plus:
        name_confidence, phone_confidence  -- high | medium | low | missing
        conflicts                          -- {"name": {...}, "phone": {...}}
        auto_confirmable                   -- bool, True only when both P0
                                              fields are high confidence
    """
    lines = split_lines(text or "")

    phone_result = detect_phone(lines)

    email = extract_email(text or "")
    email_line: int | None = None
    if email:
        for idx, line in enumerate(lines):
            if email in line:
                email_line = idx
                break

    name_result = detect_name(lines, phone_result.get("line"), email_line)

    skills = extract_skills(text or "")
    conflicts: dict[str, dict] = {}
    if name_result["conflict"]:
        conflicts["name"] = {
            "code": name_result["conflict"],
            "candidates": name_result["candidates"][:5],
        }
    if phone_result["conflict"]:
        conflicts["phone"] = {
            "code": phone_result["conflict"],
            "candidates": phone_result["candidates"][:5],
        }

    auto_confirmable = (
        name_result["value"] is not None
        and phone_result["value"] is not None
        and name_result["confidence"] in AUTO_CONFIRMABLE_CONFIDENCE
        and phone_result["confidence"] in AUTO_CONFIRMABLE_CONFIDENCE
    )

    return {
        "name": name_result["value"],
        "phone": phone_result["value"],
        "email": email,
        "gender": _extract_gender(lines, text or ""),
        "age": _extract_age(lines, text or ""),
        "education": extract_education(text or ""),
        "school": _truncate(_extract_school(lines), 255),
        "major": _truncate(_extract_major(lines), 255),
        "graduation_time": _truncate(_extract_graduation_time(lines, text or ""), 50),
        "city": _truncate(_labeled_value(lines, CITY_LABELS), 100),
        "work_years": _truncate(_extract_work_years(lines, text or ""), 50),
        "latest_company": _truncate(_extract_latest_company(lines), 255),
        "latest_position": _truncate(_labeled_value(lines, POSITION_LABELS), 255),
        "wechat": _truncate(_labeled_value(lines, WECHAT_LABELS), 255),
        "skills": ", ".join(skills) if skills else None,
        # NOTE: intended_course_id is deliberately never filled by rules —
        # it is reserved for the future AI Course Suggestion enhancer.
        "name_confidence": name_result["confidence"],
        "phone_confidence": phone_result["confidence"],
        "name_candidates": name_result["candidates"][:5],
        "phone_candidates": phone_result["candidates"][:5],
        "conflicts": conflicts,
        "auto_confirmable": auto_confirmable,
    }


def dump_conflicts(conflicts: dict | None) -> str | None:
    """Serialise the conflict map for storage in lead_drafts.conflict_flags."""
    if not conflicts:
        return None
    return json.dumps(conflicts, ensure_ascii=False)


def load_conflicts(raw: str | None) -> dict:
    """Parse lead_drafts.conflict_flags back into a dict (tolerates junk)."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
