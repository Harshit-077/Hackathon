# IntentUI WebSocket Contract v1

Frozen interface between Browser (Interaction Domain) and Intent Engine (Reasoning Domain).

## Client → Engine

See `shared/schema.json` → `ClientEvent`

Event types: `speech_final` | `pointer_click` | `selection_resolved` | `ui_snapshot`

## Engine → Client

See `shared/schema.json` → `EngineResponse`

Decisions: `execute` | `clarify` | `error`

## Versioning

Contract version: **v1** — do not change field names without team agreement.
