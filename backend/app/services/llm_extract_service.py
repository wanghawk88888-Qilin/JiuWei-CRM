"""LLM-enhanced resume extraction service — placeholder for v0.1.

This module is intentionally kept as a placeholder. In v0.1, no real LLM
calls are made. The enhance_resume_extract function always returns a result
indicating that no LLM was used, so the main resume import pipeline never
blocks on AI availability.
"""


def enhance_resume_extract(text: str) -> dict:
    """Placeholder: enhance rule-based extraction results with LLM.

    In v0.1 this always returns a no-op result. Future versions may
    integrate with a real LLM provider to produce richer summaries
    and course suggestions.

    Returns:
        A dict with keys:
            llm_used (bool): Always False in v0.1.
            llm_provider (str | None): Always None.
            ai_summary (str | None): Always None.
            ai_course_suggestion (str | None): Always None.
    """
    return {
        "llm_used": False,
        "llm_provider": None,
        "ai_summary": None,
        "ai_course_suggestion": None,
    }
