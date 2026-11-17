# Two-minute scripted demo

## Launch

From the repository folder in a normal PowerShell terminal:

```powershell
.\Start-Demo.ps1
```

Open http://127.0.0.1:8010 and hard-refresh with Ctrl+F5. Select Alex.
The launcher uses Atlas and a new demo database on each run, leaving existing data intact.
Your local environment must contain a working MONGODB_URI. No Gemini or LangSearch calls are made.
If the port is occupied, use ` .\Start-Demo.ps1 -Port 8011`.
For rehearsal without internet, use ` .\Start-Demo.ps1 -Offline`; this uses SQLite, not Atlas.

## Say this to the audience

"This is a scripted walkthrough of our group-trip assistant. In this run, MongoDB Atlas persists the conversation and expense mentions. The assistant replies are fixed for a repeatable presentation; live AI and restaurant discovery are not being demonstrated."

## Send these exact messages

Click each matching prompt chip, then press Enter. Wait for the reply before continuing.

1. **Hey Bouncer!** — introduces Alex, Sara and Dev.
2. **I want tacos in Montreal** — introduces a fictional Taco Night scenario.
3. **Our budget is $30 per person** — sets the scripted CAD 90 group budget.
4. **We need halal and nut-free options** — shows the scripted dietary REVIEW checkpoint. This dialogue is illustrative, not a newly persisted policy decision.
5. **We paid $90 for dinner** — the real deterministic parser captures and persists an expense mention.
6. **Split it equally** — shows the fixed CAD 30/person preview, assuming Alex paid. No ledger entry or payment is created.
7. **Recap** — summarizes the scenario and outstanding verification.

## Show MongoDB

In Atlas, open the database name printed by the launcher, then the conversations collection.
Show the user message containing the expense extraction with amount_cents=9000 and the assistant replies.
Do not present these as live search results, executed bookings, payment records, or real policy evaluations.

## Repeat

To restart the conversation in the same database, click the **info (i)** button, then **Clear messages** and confirm. This permanently removes saved messages and their attached expense mentions for everyone in the demo, but keeps policies, audit history, and ledger records.

Stop with Ctrl+C and run the launcher again for a fresh chat. Old demo databases remain available; nothing is deleted.
The exact messages above always produce the same replies, even when repeated or sent out of order.
