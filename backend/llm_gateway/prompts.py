"""LLM prompt templates — structured output only, no action execution."""

SEMANTIC_EXTRACTION_PROMPT = """You extract semantic intent from user speech about an analytics dashboard.

Dashboard elements (ids): revenue, users, conversion, churn, retention, geographic, date_filter, summary

Return ONLY valid JSON with this schema:
{
  "action": "explain" | "compare" | "resize" | "filter" | null,
  "entity": "<element id or null>",
  "references": ["this", "that", "it", ...],
  "raw_confidence": 0.0-1.0
}

Rules:
- action=null if unclear
- entity=null if user uses pronouns only
- references=list pronouns detected (this, that, it, the other one, the first one, the second one)
- Do NOT decide final targets — only extract semantics
"""

EXPLANATION_PROMPT = """Explain this dashboard metric briefly (2-3 sentences) for a business user.
Return plain text only, no JSON."""
