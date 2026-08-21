# Seven-Step Demo Script

1. **Speech + pointer grounding** — Point at Revenue, say "Explain this."
2. **Comparison** — Point at Revenue, say "Compare this with Churn."
3. **Conflict** — Point at Users, say "Explain Revenue." → clarify with conflict message.
4. **Conflict resolution** — Click Revenue → explanation executes.
5. **Adaptive resize** — Say "Make this bigger." → Revenue expands.
6. **Filter** — Say "Show me the last 30 days." → Date filter updates.
7. **Conversation reference** — Say "Explain Revenue." then "Compare it with Churn." → "it" = Revenue.

Run backend evaluation: `python -m backend.evaluate_demo`

Frontend mock mode: set `VITE_ENGINE_MODE=mock` in `.env`
