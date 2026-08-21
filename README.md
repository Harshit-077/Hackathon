# IntentUI

**An adaptive interface that understands what the user means, not merely what the user says.**

Multimodal analytics dashboard combining voice, pointer position, and semantic DOM context with a confidence-aware Intent Engine.

## Quick Start

```bash
# 1. Environment
cp .env.example .env
# Add GEMINI_API_KEY and/or GROQ_API_KEY (see below)

# 2. Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## API Keys (model capability only)

| Variable | Where to get it | Purpose |
|----------|----------------|---------|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | Primary LLM (semantic extraction + explanations) |
| `GROQ_API_KEY` | https://console.groq.com/keys | Fallback when Gemini fails |

Without keys, the system uses a **deterministic stub** — fully demoable offline.

Optional model overrides: `GEMINI_MODEL`, `GROQ_MODEL` (see `.env.example`).

## Run Modes

| Mode | Config | Use case |
|------|--------|----------|
| Live | `VITE_ENGINE_MODE=live` | Full stack with backend WebSocket |
| Mock | `VITE_ENGINE_MODE=mock` | Frontend-only, no backend needed |

## Tests

```bash
# Backend
python -m backend.evaluate_demo    # 7-step demo replay
pytest                             # unit tests

# Frontend
cd frontend && npm test
```

## Architecture

```
frontend/     Browser — voice, pointer, DOM, UI adaptation
backend/      Intent Engine — reasoning, confidence, decisions
shared/       Frozen WebSocket contract (schema.json)
docs/         Architecture, demo script, API reference
```

See [docs/architecture.md](docs/architecture.md) for details.

## Demo Scenarios

1. Point at Revenue → "Explain this."
2. "Compare this with Churn."
3. Point at Users → "Explain Revenue." → **conflict clarification**
4. "Make this bigger." → adaptive resize
5. "Show me the last 30 days." → date filter
6. Ambiguous compare → clarification UI
7. "Explain Revenue" then "Compare it with Churn." → reference resolution

## Endpoints

- WebSocket: `ws://localhost:8000/ws`
- Health: `GET /health`
- Debug log: `GET /debug`

## Failure Recovery

| Failure | Fallback |
|---------|----------|
| Gemini down | Groq |
| Groq down | Deterministic stub |
| WebSocket down | Mock mode + reconnect |
| Speech API down | Text input bar |

## License

Hackathon MVP — MIT
