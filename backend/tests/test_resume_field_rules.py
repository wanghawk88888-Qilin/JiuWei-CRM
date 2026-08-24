"""Unit tests for the deterministic name / phone extraction rules.

These cover requirement scenarios 5-14: name formats, phone formats, and the
"never guess" conflict behaviour.
"""

import pytest

from app.services import resume_field_rules as rules
from app.services.resume_extract_service import extract_all


def profile(text: str) -> dict:
    return rules.extract_profile(text)


# ---------------------------------------------------------------------------
# Name — priority 1: explicit label
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "line",
    [
        "姓名：张三",
        "姓 名：张三",
        "姓名: 张三",
        "姓名 张三",
        "个人姓名：张三",
        "Name: 张三",
        "Name：张三",
    ],
)
def test_labeled_name_formats(line):
    """Scenario 5 — standard labelled name formats are high confidence."""
    result = profile(f"个人简历\n{line}\n手机号：13812345678")
    assert result["name"] == "张三"
    assert result["name_confidence"] == rules.CONF_HIGH


def test_labeled_name_with_trailing_fields():
    result = profile("姓名：张三  性别：男  年龄：24\n手机：13812345678")
    assert result["name"] == "张三"


def test_labeled_name_on_next_line_table_layout():
    """docx tables often put the label and value in separate cells."""
    result = profile("姓名\n张三\n手机号\n13812345678")
    assert result["name"] == "张三"


# ---------------------------------------------------------------------------
# Name — priority 2: header zone, no label
# ---------------------------------------------------------------------------

def test_unlabeled_header_name():
    """Scenario 6 — name at the top of the resume with contact info below."""
    result = profile(
        "张三\n男 | 24岁 | 北京\n13812345678\nzhangsan@example.com"
    )
    assert result["name"] == "张三"
    assert result["name_confidence"] == rules.CONF_HIGH


def test_resume_title_is_not_a_name():
    """Titles like 个人简历 must never be picked up as the candidate's name."""
    result = profile(
        "个人简历\n李四\n手机 13800001111\nlisi@example.com"
    )
    assert result["name"] == "李四"


@pytest.mark.parametrize(
    "heading",
    ["个人简历", "求职简历", "简历", "个人信息", "基本信息"],
)
def test_headings_rejected_as_names(heading):
    assert not rules.is_plausible_name(heading)


def test_organisation_is_not_a_name():
    assert not rules.is_plausible_name("北京大学")
    assert not rules.is_plausible_name("字节跳动科技")


# ---------------------------------------------------------------------------
# v0.2.1 blind-test fixes — section headings and locations are never names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "heading",
    ["个人总结", "个人简介", "自我介绍", "职业总结", "职业概述"],
)
def test_section_headings_are_not_names(heading):
    assert not rules.is_plausible_name(heading)


@pytest.mark.parametrize(
    "location",
    [
        "北京", "上海", "天津", "重庆",
        "北京市", "河北省", "海淀区", "朝阳县", "广州",
    ],
)
def test_locations_are_not_names(location):
    assert not rules.is_plausible_name(location)


@pytest.mark.parametrize(
    "name",
    ["王天", "车夏", "顾安祺", "张三", "李四", "王小明"],
)
def test_real_chinese_names_still_pass(name):
    assert rules.is_plausible_name(name)


def test_blind_test_candidates_exclude_heading_and_location():
    """The exact blind-test resume: 个人总结 and 北京 must not be candidates."""
    result = profile(
        "王天\n"
        "个人总结\n"
        "北京\n"
        "13812345678\n"
        "wangtian@example.com"
    )
    assert result["name"] == "王天"
    assert result["name_confidence"] == rules.CONF_HIGH
    assert "个人总结" not in result["name_candidates"]
    assert "北京" not in result["name_candidates"]


def test_city_with_suffix_is_not_a_candidate():
    """A bare 北京市 in the header must not become the name candidate."""
    result = profile(
        "车夏\n"
        "北京市\n"
        "13812345678\n"
        "chexia@example.com"
    )
    assert result["name"] == "车夏"
    assert "北京市" not in result["name_candidates"]


# ---------------------------------------------------------------------------
# Name — priority 3: spaced layout
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [("张 三", "张三"), ("王 小 明", "王小明"), ("  李  雷 ", "李雷")],
)
def test_spaced_names_are_normalized(raw, expected):
    """Scenario 7 — typographic spacing is stripped for CJK names."""
    assert rules.normalize_name(raw) == expected


def test_spaced_name_end_to_end():
    result = profile("姓名：王 小 明\n手机号：13912345678")
    assert result["name"] == "王小明"


def test_latin_name_keeps_its_space():
    assert rules.normalize_name("Zhang  San") == "Zhang San"


# ---------------------------------------------------------------------------
# Name — conflicts and absence
# ---------------------------------------------------------------------------

def test_name_conflict_is_not_auto_resolved():
    """Scenario 12 analogue — two labelled names must not be guessed between."""
    result = profile("姓名：张三\n联系方式\n姓名：李四\n手机号：13812345678")
    assert result["name"] is None
    assert result["conflicts"]["name"]["code"] == rules.CODE_NAME_CONFLICT
    assert set(result["conflicts"]["name"]["candidates"]) == {"张三", "李四"}
    assert result["auto_confirmable"] is False


def test_missing_name():
    """Scenario 13 — no name at all."""
    result = profile("求职意向：测试工程师\n手机号：13812345678\n本科")
    assert result["name"] is None
    assert result["name_confidence"] == rules.CONF_MISSING
    assert result["auto_confirmable"] is False


# ---------------------------------------------------------------------------
# Name — priority 2: identity block detection (v0.2.1)
# ---------------------------------------------------------------------------

def test_identity_block_name_next_to_phone_and_email():
    """Name with a phone + email in the following lines -> high confidence."""
    result = profile("许多\n13812345678\nxuduo20050224@163.com")
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_HIGH
    assert result["phone"] == "13812345678"


def test_identity_block_name_gender_age_phone():
    """Name + gender + age + phone -> high confidence (condition B)."""
    result = profile("许多\n男 | 21岁\n13812345678")
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_HIGH


def test_identity_block_name_phone_intention():
    """Name + phone + 求职意向 -> high confidence."""
    result = profile("许多\n13812345678\n求职意向：Python")
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_HIGH


def test_bare_name_without_identity_signals_is_not_high():
    """A name with no identity fields nearby must never reach high confidence."""
    result = profile("许多\n个人优势\n熟悉 Python\n教育经历")
    assert result["name_confidence"] != rules.CONF_HIGH
    assert result["auto_confirmable"] is False


def test_weak_identity_block_name_is_medium_not_high():
    """A name with only a weak identity signal stays medium, never auto-confirm."""
    body = "\n".join(f"第{i}行正文内容" for i in range(20))
    result = profile(body + "\n许多\n男")
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_MEDIUM
    assert result["auto_confirmable"] is False


def test_project_members_do_not_become_identity_names():
    """小组分工 members must never be picked up as high-confidence names."""
    text = (
        "小组分工：\n"
        "许多：统筹项目进度与任务分配\n"
        "王瑞岐：负责实验环境配置\n"
        "槐明君：负责数据集预处理\n"
    )
    result = profile(text)
    assert result["name_confidence"] != rules.CONF_HIGH
    assert result["auto_confirmable"] is False


def test_identity_block_beats_repeated_project_member_name():
    """The identity block name wins even when the same name appears in 小组分工."""
    text = (
        "小组分工：\n"
        "许多：统筹项目进度与任务分配\n"
        "王瑞岐：负责实验环境配置\n"
        "槐明君：负责数据集预处理\n"
        "许多\n"
        "男 | 21岁\n"
        "13269035122\n"
        "xuduo20050224@163.com\n"
        "求职意向：Python | 期望城市：北京\n"
    )
    result = profile(text)
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_HIGH
    assert result["phone"] == "13269035122"
    assert result["phone_confidence"] == rules.CONF_HIGH
    assert result["conflicts"] == {}
    assert result["auto_confirmable"] is True


def test_multiple_identity_block_names_conflict():
    """Two distinct high-confidence identity names -> NAME_CONFLICT, no guess."""
    text = (
        "张三\n13812345678\nzhangsan@163.com\n"
        "李四\n13912345678\nlisi@163.com\n"
    )
    result = profile(text)
    assert result["name"] is None
    assert result["conflicts"]["name"]["code"] == rules.CODE_NAME_CONFLICT
    assert result["auto_confirmable"] is False


def test_section_heading_is_not_an_identity_block_name():
    """A section heading never becomes an identity-block candidate."""
    result = profile(
        "个人总结\n熟悉 Python\n13812345678\nzhangsan@163.com"
    )
    assert result["name"] != "个人总结"
    assert "个人总结" not in (result["name_candidates"] or [])


def test_location_is_not_an_identity_block_name():
    """A location line never becomes an identity-block candidate."""
    result = profile("北京\n13812345678\nzhangsan@163.com")
    assert result["name"] != "北京"
    assert "北京" not in (result["name_candidates"] or [])


@pytest.mark.parametrize(
    "name,phone,email",
    [
        ("王天", "13371600897", "wangtian@example.com"),
        ("车夏", "13718701307", "chexia@example.com"),
        ("顾安祺", "13522944267", "guanqi@example.com"),
    ],
)
def test_original_real_names_still_high(name, phone, email):
    """The three original real resumes keep high name/phone confidence."""
    result = profile(f"{name}\n{phone}\n{email}")
    assert result["name"] == name
    assert result["name_confidence"] == rules.CONF_HIGH
    assert result["phone"] == phone
    assert result["phone_confidence"] == rules.CONF_HIGH
    assert result["auto_confirmable"] is True


def test_auto_confirmable_requires_phone_high_too():
    """A high identity-block name with a low-confidence phone is not auto-confirm."""
    body = "\n".join(f"第{i}行正文内容" for i in range(20))
    result = profile(
        body + "\n许多\n13812345678\n求职意向：Python"
    )
    assert result["name"] == "许多"
    assert result["name_confidence"] == rules.CONF_HIGH
    assert result["phone"] == "13812345678"
    assert result["phone_confidence"] == rules.CONF_MEDIUM
    assert result["auto_confirmable"] is False


# ---------------------------------------------------------------------------
# Phone formats
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        "13812345678",
        "138 1234 5678",
        "138-1234-5678",
        "+86 13812345678",
        "+86-138-1234-5678",
        "8613812345678",
    ],
)
def test_phone_formats_normalize(raw):
    """Scenarios 8-11 — all accepted formats collapse to 11 digits."""
    result = profile(f"姓名：张三\n手机号：{raw}")
    assert result["phone"] == "13812345678"
    assert result["phone_confidence"] == rules.CONF_HIGH


def test_normalize_phone_rejects_non_mobile():
    assert rules.normalize_phone("010-88886666") is None
    assert rules.normalize_phone("12345") is None
    assert rules.normalize_phone("12812345678") is None  # 1[3-9] required


def test_id_card_number_is_not_a_phone():
    """An 18-digit ID must not be mined for a fake mobile number."""
    result = profile("姓名：张三\n身份证号：110101199003071234")
    assert result["phone"] is None


def test_phone_missing():
    """Scenario 14 — no phone at all."""
    result = profile("姓名：张三\n邮箱：zhangsan@example.com")
    assert result["phone"] is None
    assert result["phone_confidence"] == rules.CONF_MISSING
    assert result["auto_confirmable"] is False


# ---------------------------------------------------------------------------
# Phone conflicts
# ---------------------------------------------------------------------------

def test_phone_conflict_multiple_ambiguous_numbers():
    """Scenario 12 — several candidate numbers, none clearly the candidate's."""
    text = (
        "张三\n"
        "项目经历\n"
        "对接联系方式 13800001111\n"
        "业务联系方式 13900002222\n"
        "备用联系方式 13700003333\n"
    )
    result = profile(text)
    assert result["phone"] is None
    assert result["conflicts"]["phone"]["code"] == rules.CODE_PHONE_CONFLICT
    assert len(result["conflicts"]["phone"]["candidates"]) >= 2
    assert result["auto_confirmable"] is False


def test_explicit_mobile_label_wins_over_other_numbers():
    """A clear 手机 label disambiguates, so no human review is needed."""
    text = (
        "张三\n"
        "手机号：13812345678\n"
        "工作经历\n"
        "公司总机 13900002222\n"
    )
    result = profile(text)
    assert result["phone"] == "13812345678"
    assert result["phone_confidence"] == rules.CONF_HIGH


def test_emergency_contact_number_is_not_used():
    text = "姓名：张三\n紧急联系人电话：13900002222\n"
    result = profile(text)
    assert result["phone"] is None


def test_negative_label_does_not_leak_to_the_next_line():
    """A 联系人 label on one line must not disqualify the next line's number."""
    text = (
        "个人简历\n"
        "姓名：赵六\n"
        "联系人电话：13700001111\n"
        "业务联系方式：13700002222\n"
        "对接联系方式：13700003333\n"
    )
    result = profile(text)
    # Two un-negated but equally ambiguous numbers remain -> conflict, no guess.
    assert result["phone"] is None
    assert result["conflicts"]["phone"]["code"] == rules.CODE_PHONE_CONFLICT
    assert result["auto_confirmable"] is False


def test_table_layout_label_on_previous_line_still_works():
    """A bare number line still borrows the label from the line above it."""
    result = profile("姓名\n张三\n手机号\n13812345678")
    assert result["phone"] == "13812345678"
    assert result["phone_confidence"] == rules.CONF_HIGH


# ---------------------------------------------------------------------------
# Auto-confirmable gating (the core safety rule)
# ---------------------------------------------------------------------------

def test_auto_confirmable_requires_both_fields_high():
    good = profile("姓名：张三\n手机号：13812345678\n本科")
    assert good["auto_confirmable"] is True

    no_phone = profile("姓名：张三\n本科")
    assert no_phone["auto_confirmable"] is False

    no_name = profile("手机号：13812345678\n本科")
    assert no_name["auto_confirmable"] is False


# ---------------------------------------------------------------------------
# Secondary fields
# ---------------------------------------------------------------------------

def test_secondary_fields_are_best_effort():
    text = (
        "姓名：张三\n"
        "性别：男  年龄：26\n"
        "手机号：13812345678\n"
        "邮箱：zhangsan@example.com\n"
        "微信号：zs_wechat\n"
        "学历：本科\n"
        "毕业院校：北京大学\n"
        "专业：计算机科学与技术\n"
        "现居城市：北京\n"
        "求职意向：测试开发工程师\n"
        "熟悉 Python 与自动化测试\n"
    )
    result = profile(text)
    assert result["email"] == "zhangsan@example.com"
    assert result["gender"] == "male"
    assert result["age"] == 26
    assert result["education"] == "本科"
    assert result["school"] == "北京大学"
    assert result["major"] == "计算机科学与技术"
    assert result["city"] == "北京"
    assert result["wechat"] == "zs_wechat"
    assert "Python" in result["skills"]


def test_intended_course_is_never_filled_by_rules():
    """Requirement 13 — course is reserved for the future AI enhancer."""
    result = profile("姓名：张三\n手机号：13812345678\n想学 AI 大模型课程")
    assert "intended_course_id" not in result


# ---------------------------------------------------------------------------
# Major — 专业技能 must never be mistaken for the major "技能"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "heading",
    ["专业技能", "专业能力", "专业特长", "专业知识", "专业课程", "专业证书", "专业资格", "专业经验"],
)
def test_skill_heading_is_not_a_major(heading):
    """A compound 专业X heading must never yield major="X" (or "X" at all)."""
    result = profile(f"姓名：王天\n手机号：13812345678\n{heading}\n熟悉 Python")
    assert result["major"] is None


def test_major_with_colon_label():
    result = profile("姓名：张三\n手机号：13812345678\n专业：电子信息工程")
    assert result["major"] == "电子信息工程"


def test_major_with_halfwidth_colon_label():
    result = profile("姓名：张三\n手机号：13812345678\n专业: 通信工程")
    assert result["major"] == "通信工程"


def test_major_with_explicit_compound_label():
    result = profile("姓名：车夏\n手机号：13812345678\n所学专业：通信工程")
    assert result["major"] == "通信工程"


def test_major_space_separated_label():
    result = profile("姓名：张三\n手机号：13812345678\n专业  通信工程")
    assert result["major"] == "通信工程"


def test_major_table_layout_label_on_own_line():
    result = profile("姓名：张三\n手机号：13812345678\n专业\n通信工程")
    assert result["major"] == "通信工程"


def test_missing_major_returns_none():
    """No reliable major field present — must not guess from body text."""
    result = profile("姓名：顾安祺\n手机号：13812345678\n本科\n5 年工作经验")
    assert result["major"] is None


def test_education_picks_highest_level():
    assert rules.extract_education("本科 硕士") == "硕士"
    assert rules.extract_education("大专 本科") == "本科"


# ---------------------------------------------------------------------------
# Backward compatibility of the legacy extraction entry point
# ---------------------------------------------------------------------------

def test_extract_all_keeps_legacy_shape():
    """Scenario 21 support — the single-import flow's contract is unchanged."""
    result = extract_all("姓名：张三\n手机号：13812345678\n学历：本科\n熟悉 Python")
    assert set(result.keys()) == {"name", "phone", "email", "education", "skills"}
    assert result["name"] == "张三"
    assert result["phone"] == "13812345678"
    assert result["education"] == "本科"


def test_conflict_serialization_roundtrip():
    conflicts = {"name": {"code": "NAME_CONFLICT", "candidates": ["张三", "李四"]}}
    raw = rules.dump_conflicts(conflicts)
    assert rules.load_conflicts(raw) == conflicts
    assert rules.load_conflicts(None) == {}
    assert rules.load_conflicts("not json") == {}
