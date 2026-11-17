# SplitSmart Bouncer

## New: standalone Next.js prototype

The [SplitSmart frontend](frontend/README.md) is the new polished, interactive Toronto group-planning demo. Launch it independently with `cd frontend`, `npm install`, then `npm run dev`, and open http://127.0.0.1:3000. It includes guided demo controls, group voting, dietary checks, an itinerary, editable equal/itemized receipt splitting, and two-way settlement acknowledgment. All data and interactions are simulated in the browser; it requires no backend or API keys. The existing Python application below remains independently available at port 8000.

A hackathon group-trip coordinator: FastAPI, optional MongoDB Atlas persistence, a Gemini-backed conversation-understanding test, and a single responsive group-chat interface. The agent participates as **Bouncer**; the web UI has no dashboard, tabs, or side panels.

## Run locally

Python 3.12+ recommended. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Only if .env does not already exist:
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs. Linux/macOS: activate with `source .venv/bin/activate`.

The delivered local `.env` contains the supplied Atlas URI, but starts in SQLite/mock mode so a demo can run without cloud access. It is ignored by Git and excluded from the ZIP. Do not overwrite it with the example. Rotate the password shared in chat. No secrets belong in commit messages, screenshots, or logs.

## What works

- Three seeded members with private editable boundaries, transport modes, and total budgets; organizer-controlled versioned group policy.
- A single-thread web chat with recent conversation context for Gemini; the authenticated chat API accepts PNG/JPEG attachments but the current agent does not parse images.
- Deterministic tag, dietary evidence, transport, per-person cap, cumulative budget, and schedule checks. Scheduling uses explicit timezone offsets and a configurable travel buffer; it does not query live routes or opening hours.
- Eligible proposals go to one ballot round. Each member has one replaceable vote. All members must vote; organizer closes. Most votes wins, ties use lowest cost then earliest submission then ID. The winner is rechecked against current policy and itinerary.
- Equal expense splitting in integer CAD cents; sorted member IDs receive remainder cents deterministically. Submitter is payer. Every debtor and payer separately attest sent/received. No payment API, refund, bank verification, or money movement exists.
- Simulated ticket cancellation requires an explicit owner action. Real tickets are blocked, even with approval. There is no live cancellation integration.
- `policies`, `decisions`, `auditEvents`, `groups`, `members`, `venues`, `proposals`, `votes`, `expenses`, `payments`, `tickets`, `conversations` collections in Atlas mode.

## Chat demo

The web app opens directly to the Montreal weekend group chat. In this understanding-test stage, Bouncer replies with the keywords, intent, and entities it understood from the latest message rather than recommending places or taking actions. With `AGENT_MODE=gemini` and a configured Gemini API key, these fields come from Gemini structured JSON output; mock mode and provider errors use a simple local keyword fallback. The validated, versioned analysis is stored on the user's conversation document with its source and authenticated reporter ID so it can be migrated into its own MongoDB collection later.

Text expense statements are also captured by a deterministic parser into a versioned `expense_mention` object on the authenticated user's conversation document. The object contains normalized integer cents, currency and its source, description, merchant, date text, item details, clarification status, and server-stamped source/reporting member IDs. Partial mentions trigger a follow-up and can be completed in the next message, including by another group member, while preserving the original reporter. Model output cannot set member IDs. This stage does not create an expense, split costs, or initiate payment. Receipt images are not parsed.

The underlying API still supports proposal voting, expense acknowledgements, boundary updates, and simulated ticket actions. For an automated expense flow against a fresh running server: `python scripts/demo.py`. It deliberately writes demo records. To start over in SQLite mode, stop the server and rename `splitsmart.sqlite`; the next start seeds a fresh database.

For an automated expense flow against a fresh running server: `python scripts/demo.py`. It deliberately writes demo records. To start over in SQLite mode, stop the server and rename `splitsmart.sqlite`; the next start seeds a fresh database.

## Atlas setup

1. Set `STORAGE=mongo` in `.env`; provide `MONGODB_URI` and a dedicated `MONGODB_DB=splitsmart` database. Do not use a production database for this demo.
2. Allow your development machine's IP in Atlas network access. Use a dedicated database user. Keep the URI out of source control.
3. Startup creates collections, unique ID indexes, and strict JSON Schema validators. It needs collection creation and `collMod` privileges. For deployment, provision schema with an administrator and separate that responsibility from the runtime account (a follow-up hardening task).
4. Atlas/replica-set transactions are required. Domain changes, decisions, and audit events commit together. A group revision write serializes concurrent mutations; write conflicts fail rather than silently accept stale policy. Retry the user action after refreshing. The local SQLite repository uses `BEGIN IMMEDIATE` for equivalent serialized demo operations.

MongoDB validators enforce document structure; Python evaluates cross-document policy. The agent has no direct database tool. Audit, decision, and policy records have no application update/delete endpoints. Database administrators can still change them: **this is not immutable storage or an audit-proof ledger**. Use restrictive roles, backups, external audit exports, and retention controls for stronger evidence preservation.

## Gemini setup

Set `AGENT_MODE=gemini`, `GEMINI_API_KEY`, and a `GEMINI_MODEL` available to your Google project. The example model is configurable; access/availability is not assumed. The Google Gen AI SDK sends the latest user text and recent conversation turns to Gemini for structured keyword understanding. Images are not sent to Gemini by the current agent.

The current chat agent makes one structured-output request and validates the result with Pydantic. It does not expose action tools, search, create proposals, or write expenses. User identity is attached by the server, not generated by Gemini. If Gemini is unavailable, the server logs the provider error and returns a clearly labeled local keyword summary.

## Evidence and limitations

- Garden Table is fictional. Its seed evidence is enabled only in demo mode. No live venue discovery, halal certification, allergen certification, receipt OCR in mock mode, or human evidence-verification workflow is implemented. Unknown compliance requires review and cannot win a vote.
- User/model categories and tags are fallible. The deterministic gate verifies supplied structured data plus a small conservative keyword check; it cannot guarantee detection of misclassified, hidden, or omitted ingredients. This is not a guarantee of dietary or medical safety. Add authenticated curated venue facts and human review before real use.
- Single seeded group, three fixed members, equal all-member splits, one ballot at a time, CAD only. Member signup/invites, multi-group isolation, arbitrary split weights, abstention/deadlines, notifications, and live chat adapters are extension points.
- Budget accounting conservatively reserves accepted plan amounts plus approved expenses. Recording an expense for an already reserved plan can count twice; expense-to-plan reconciliation is not implemented.
- Accepted plans are not automatically cancelled when a profile/policy changes; new submissions and ballot resolution use current constraints.
- Replay displays the last 100 events/decisions via refresh; this MVP does not implement Change Streams. Health restrictions are hidden in other members' profiles; decisions reveal only generic conflicts. Group rules, shared messages, expense records, and proposals are visible to all members.
- `DEMO_MODE=true` exposes convenient demo identity switching. Bind to localhost. Outside demo mode, set a JSON `AUTH_TOKENS` map from long random secrets to seeded member IDs. This is bearer-token MVP authentication, not production identity management. Add TLS, OIDC, rate limits, retention and privacy controls before deployment.
- Google Chat/Discord must verify signatures, map external identities/group membership, and deduplicate deliveries before constructing `ChatEnvelope`. The protocol is in `app/adapters.py`; no unsigned webhook is exposed.

## Tests

```powershell
python -m pytest -q
python -m unittest discover -s tests -p test_core.py -v
```

API tests cover authentication, privacy, malicious requests, evidence review, budgets, scheduling, stale policies, vote replacement/ties, cent conservation, payment-party authorization/idempotency, cancellation, validation, rollback, and static assets. Offline domain tests separately exercise the policy and transaction core. See `VALIDATION.md` for the actual checks performed in the build environment; live Atlas/Gemini require a credentialed integration test.

## Architecture

`Web / future authenticated adapter → structured conversation understanding → versioned analysis on conversation → transactional repository`

Read-only UI refreshes currently acquire the same repository transaction as writes for simplicity. MongoDB startup migration and all-collection loading are hackathon-scale choices; use indexed repository queries, pagination and migration tooling before scaling.

API references used: [Google Gen AI SDK](https://googleapis.github.io/python-genai/), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [MongoDB schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/update-schema-validation/).
