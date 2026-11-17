# SplitSmart frontend prototype

A standalone, browser-only Next.js App Router application built with React, TypeScript, Tailwind CSS, Lucide, and Motion. It runs independently of the existing FastAPI service. No environment variables, API keys, database, authentication, or live services are needed.

## Launch

From this directory, with Node.js 22.18+ and npm installed:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:3000. A VS Code **SplitSmart: frontend** task is also included at the repository root.

```powershell
npm run typecheck
npm test
npm run build
```

The production build produces a static site in `out/`; it can be served by any static web server. There are no Next.js server endpoints. `npm start` is not used for static exports.

## Present the demo

The initial screen previews activity recommendations. Click **Start demo** to begin the guided story at step 1. **Next step** advances through ten stages: planning, recommendations, activity confirmation, food conflict, alternatives, dinner approval, receipt upload, expense analysis, sent acknowledgments, and final receipt confirmations. **Previous step** reconstructs the selected earlier stage; edited receipt amounts and payments are reset on backtracking. **Reset demo** clears custom chat messages, attachments, selections, receipt edits, votes, and payments. Budget and display preferences last until refresh.

For a hands-on demonstration:

1. Choose either activity; click each member’s avatar to simulate a vote. Four votes enable **Confirm activity**.
2. Type a message about pork BBQ to trigger the dietary conflict, then approve either fictional restaurant.
3. Choose **Try sample receipt**, or attach a local PNG/JPEG/WebP and send it. Local files are represented by name and the sample receipt; no file content is uploaded or analyzed. Extraction always uses the deterministic sample, explicitly labeled in the interface.
4. Switch between **Split equally** and **Split by item**. Edit amounts or assign individual items. A shared line item is allocated to all four members; tax and tip are allocated proportionally in itemized mode. Edits invalidate prior acknowledgments.
5. Click **Mark sent** for each debtor, then **Confirm received** as the demo payer, Alex. Only the second acknowledgment settles that share. The final state appears when all three debts are settled.

The sample subtotal is $104.00, Ontario HST is $13.52 (13%), and tip is $15.60 (15% before tax), totaling **$133.12**. Equal shares are **$33.28**. Itemized shares (Alex, Sarah, Omar, Maya) are **$37.12, $32.00, $34.56, $29.44**. All calculations use integer cents with deterministic remainder allocation.

Group preferences let you adjust the budget; Settings controls reduced motion and proactive food checks on custom chat messages. The guided story always includes its scripted dietary conflict. Other group entries are labeled conversation previews. Chat handles activity decisions, food conflicts, budget questions, and expenses with local scripted responses; it is not a general-purpose AI model. The sample receipt illustration retains its original amounts; the extracted expense card is the editable source of truth.

Venue names and dietary claims, forecasts, reservations, and payments are illustrative. Transit fares are excluded from plan estimates. State lives in memory and resets on refresh.

## Structure

- [Application and design system](src/app/)
- [Interactive components](src/components/splitsmart.tsx)
- [Demo data, reducer, and cent-exact calculations](src/lib/demo.ts)
- [Deterministic state and financial tests](tests/demo.test.mjs)
- [Bundled SVG artwork](public/)
