"""LLM prompt templates — structured output only, no action execution."""

SEMANTIC_EXTRACTION_PROMPT = """You extract semantic intent from user speech about a multimodal dashboard.

Dashboard / workspace element ids:
revenue, users, conversion, churn, retention, geographic, date_filter, summary,
laptop-workspace, phone-dashboard, monitor-panel, bottle-card

Return ONLY valid JSON with this schema:
{
  "action": "explain" | "compare" | "resize" | "filter" | "focus" | "open" | "details" | "close" | null,
  "entity": "<element id or null>",
  "references": ["this", "that", "it", "its", "isko", "usko", ...],
  "raw_confidence": 0.0-1.0
}

Rules:
- Understand English, Hindi, and Hinglish. Do not translate unless needed to fill the JSON.
- action=null if unclear
- entity=null if user uses pronouns only
- Map laptop/notebook→laptop-workspace, phone/mobile→phone-dashboard, monitor/tv/screen→monitor-panel
- references=list pronouns detected
- Do NOT decide final targets — only extract semantics
"""

EXPLANATION_PROMPT = """Explain this dashboard metric briefly (2-3 sentences) for a business user.
Return plain text only, no JSON."""
