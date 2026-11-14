# Project handoff

**Prepared:** 2026-11-14  
**Repository:** `sxdi1/mongodb-hackathon`  
**Branch:** `develop-backend`

## Current goal

The app is a simulated group chat, not a dashboard. Bouncer is a participant in the conversation. The backend uses Gemini to understand the latest message and produce a concise conversational reply, while keeping expense extraction and all state-changing actions deterministic.

## Current behavior

- `AGENT_MODE=mock` uses local keyword extraction and a lightweight local intent classifier.
- `AGENT_MODE=gemini` sends recent conversation and the latest text message to Gemini for one structured JSON response containing keywords, intent, entities, and a grounded reply, validated by Pydantic.
- If a Gemini request fails, the chat handler logs a redacted provider error and falls back to local understanding.
- Validated analysis is saved on the user's conversation message with `schema_version`, `source`, `reported_by`, and `source_message_id`. This is intended to make a later migration into a dedicated MongoDB collection straightforward.
- The AI agent has no proposal, search, expense-write, or payment tools.
- Text expense statements are handled separately by the deterministic parser in `app/expense_mentions.py`. The parser stores a versioned `expense_mention` on the user's message. Incomplete mentions prompt for missing details; the next message can complete them while retaining the original reporter.
- An `expense_mention` is not a ledger expense. This stage does not split a cost, create a shared expense, or move money.
- Image uploads are accepted by the chat API, but the agent explicitly asks the user to type the message instead. Receipt OCR and image understanding are not implemented.

## Relevant files

- `app/agent.py` — local understanding, Gemini structured output, reply formatting, and local fallback.
- `app/models.py` — strict Pydantic models for `ConversationUnderstanding` and `ExpenseMention`.
- `app/main.py` — chat request handling, redacted provider-error logging, fallback, and persistence of analysis/extraction.
- `app/expense_mentions.py` — deterministic text expense extraction and clarification flow.
- `app/adapters.py` — chat envelope and conversation context passed to the agent.
- `tests/test_app.py` — coverage for local/Gemini understanding, fallback, persistence, no AI side effects, and expense mentions.
- `README.md` — current setup and feature overview.

## Worktree state

At handoff, the following files are modified and not committed:

- `README.md`
- `app/agent.py`
- `app/main.py`
- `app/models.py`
- `tests/test_app.py`

`HANDOFF.md` is newly added by this handoff. Preserve these changes when moving the project to another device; do not reset or discard the worktree.

## Verification

Run the backend tests from the repository root:

```bash
.venv/bin/python -m pytest -q tests
```

Focused result after the conversational-reply change: **2 passed** for the Gemini structured-response tests. A live Gemini smoke test succeeded with `gemini-3-flash-preview`. A live authenticated `/api/chat` request succeeded with `analysis_source=gemini`, `agent_status=ok`, and a relevant reply to “I want tacos in Montreal”. The full suite remains affected by the managed Windows temp-directory permission error; the application assertions were not the cause of those setup failures.

## Local setup reminders

- Use the existing `.env` if present; it is local and must not be copied into source control or shared as part of this handoff.
- The documented defaults use SQLite and mock mode, so the app can be run without Atlas or Gemini credentials.
- To test Gemini, configure `AGENT_MODE=gemini`, a valid `GEMINI_API_KEY`, and an available model in `GEMINI_MODEL`. The verified model for the current key is `gemini-3-flash-preview`. Provider capacity errors such as HTTP 503 are temporary; the app should use the local fallback.
- Start the app with `uvicorn app.main:app --host 127.0.0.1 --port 8000`.

## Suggested next steps

1. On the receiving device, inspect `git status` and transfer the uncommitted worktree changes without overwriting local `.env` or other device-specific files.
2. Run the test command above.
3. Start in SQLite/mock mode and send a few messages to verify local understanding and text expense clarification flow.
4. Start in Gemini mode and send a natural message such as “I want tacos in Montreal”; verify the response is conversational and `analysis_source` is `gemini`.
5. If Gemini fails, inspect the redacted provider error and confirm the local fallback is used; do not interpret a provider 503 as an application parsing failure.
6. Before extending expense tracking, decide the persistence and product contract for turning a captured mention into a shared expense. Keep that separate from the current AI understanding response.
