# IntentUI Architecture

## Domains

**Browser / Interaction** — voice, pointer, DOM extraction, highlighting, action execution, TTS.

**Reasoning** — session state, candidates, reference resolution, confidence fusion, ambiguity/conflict, action planning.

**LLM Gateway** — semantic extraction + explanation only. No action execution.

## Data Flow

```
User → Voice + Pointer → Browser Context Layer → WebSocket → Intent Engine → Response
                                                                    ↓
                                                              LLM Gateway
                                                              (Gemini → Groq → stub)
```

## Key Files

| Layer | Entry |
|-------|-------|
| Frontend | `frontend/src/App.tsx` |
| WebSocket | `backend/main.py` |
| Engine | `backend/engine/orchestrator.py` |
| LLM | `backend/llm_gateway/gateway.py` |
| Contract | `shared/schema.json` |
