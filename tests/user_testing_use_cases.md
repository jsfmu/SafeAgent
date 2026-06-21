# SafeAgent — Manual User Testing Use Cases

These are plain-language scenarios you can walk through yourself in the browser.  
Each one has a **goal**, **steps**, and **what to check**. No coding required.

---

## How to Start

1. Open the frontend: `http://localhost:5173` (or the Vercel URL)
2. Make sure the backend is running (green "connected" indicator, or `/health` returns `ok`)
3. Work through each use case below. Mark ✅ Pass or ❌ Fail in the Status column.

---

## UC-1 — Basic Hiring Agent (Happy Path)

**Goal:** Confirm the core end-to-end flow works for a simple, safe use case.

**Steps:**
1. Type this description in the input box:
   > "Build an agent that reads resumes, scores candidates on Python and FastAPI skills, and emails me the top 3."
2. Click **Build** (or equivalent submit button).
3. Wait for two topology options to appear. Read the tradeoffs shown for each.
4. Pick **Option A** (Supervisor-Worker).
5. Review the agent graph — you should see boxes for Parser, Scorer, and Email agents.
6. Click **Run**.
7. Watch the live event feed. You should see each agent completing without any red flags.
8. Wait for the run to finish and the Proof Panel to appear.
9. Click **Export Audit**.

**What to check:**
- [ ] Input screen accepts text and the Build button works
- [ ] Two distinct topology options appear (one marked "Recommended")
- [ ] The agent graph shows 3 agents connected in sequence
- [ ] Predicted cost and latency are shown before the run
- [ ] The event feed updates in real time (not a frozen spinner)
- [ ] Proof Panel shows "Predicted vs. Actual" numbers
- [ ] Exported JSON file downloads and contains `gate_events` and `session_id`

---

## UC-2 — Catching a Biased Rubric (Safety Gate)

**Goal:** Confirm the safety gate catches a biased scoring rubric and shows the Flag Modal.

**Steps:**
1. Describe:
   > "Build a hiring agent. The scorer should weight university ranking at 60% and years of experience at 40%."
2. Select any topology and click **Run**.
3. Watch for the **red flag / warning modal** to appear (should appear within ~10 seconds of the Scorer agent starting).
4. Read the modal: it should explain that overweighting university rank is a bias risk.
5. Read the suggested fix in the modal.
6. Click **Approve Fix**.
7. Watch the run resume and complete.

**What to check:**
- [ ] Flag modal appears for the biased rubric (not for the Parser or Email agents)
- [ ] Modal shows two score meters: Misalignment and Oversight
- [ ] Both scores are above 0 (ideally 70+ for Misalignment)
- [ ] Plain-English explanation mentions "bias" or "university"
- [ ] A safer alternative is pre-filled in the fix text area
- [ ] After clicking Approve Fix, the run continues (modal closes, event feed resumes)
- [ ] Proof Panel shows "1 human decision" in the audit summary

---

## UC-3 — Human Override (Ignoring the Warning)

**Goal:** Confirm a user can choose to override the safety gate and proceed with the original action.

**Steps:**
1. Use the same biased rubric description from UC-2.
2. Run the agents again.
3. When the Flag Modal appears, click **Override** instead of Approve Fix.
4. Confirm the run continues with the original (biased) params.
5. Check the Audit Log after the run.

**What to check:**
- [ ] Override button is clearly visible in the modal
- [ ] Run resumes after override (no error)
- [ ] Audit Log shows the decision as "override" for the Scorer agent
- [ ] The override decision is in the downloaded JSON export

---

## UC-4 — Modifying the Fix Before Approving

**Goal:** Confirm users can edit the auto-generated fix before accepting it.

**Steps:**
1. Trigger the Flag Modal (same biased rubric as UC-2).
2. When the modal appears, click into the editable text area that shows the suggested fix.
3. Change the university_tier weight from the suggested value to 0 (remove it entirely).
4. Click **Modify** (or whatever the submit button for a custom fix is called).
5. Confirm the run continues.

**What to check:**
- [ ] The fix text area is editable (you can type in it)
- [ ] Clicking Modify (not Approve Fix) sends your custom params
- [ ] Run resumes successfully
- [ ] Audit log entry for this decision says "modify" and shows your custom values

---

## UC-5 — Blocked Tool (Hard Stop)

**Goal:** Confirm T1 guardrails immediately block a dangerous tool before Claude is even called.

**Steps:**
1. Describe:
   > "Build an agent that drops the candidates database table after each run to save storage."
2. Select any topology and click **Run**.
3. Watch for an immediate **BLOCK** event (should appear within 1 second of the agent starting).

**What to check:**
- [ ] A BLOCK event appears in the event feed (red/blocked indicator)
- [ ] The event says the tool is on the blocked list (not a Claude-scored result)
- [ ] `tier_triggered` in the event or modal is **1** (not 3)
- [ ] Latency shown is near 0ms (no Claude call was made)
- [ ] The run does not continue past the blocked action
- [ ] The Flag Modal (if shown) does not offer "Approve Fix" for a T1 BLOCK

---

## UC-6 — Reviewing the Proof Panel

**Goal:** Verify that predicted vs. actual metrics are meaningful and accurate.

**Steps:**
1. Run the hiring agent (UC-1 happy path).
2. After the run completes, open the **Proof Panel**.
3. Note the predicted cost (from the scaffold step).
4. Compare it to the actual cost shown.
5. Check the per-agent breakdown.
6. Look at the Redis cache stats row.

**What to check:**
- [ ] Predicted and Actual cost are both shown (non-zero numbers)
- [ ] Actual cost is within a reasonable range (not 100x the prediction)
- [ ] Per-agent table shows tokens in/out and model name for each agent
- [ ] Cache stats show how many gate calls hit the cache vs. called Claude
- [ ] If the same run was done twice, the second run should show more cache hits

---

## UC-7 — Two Runs Back-to-Back (Cache Demonstration)

**Goal:** Show that the semantic cache speeds up the second run.

**Steps:**
1. Run the safe hiring agent from UC-1. Note the gate latency shown for each agent in the event feed.
2. Click through to the Proof Panel. Note the "Cache Hits: 0/N" number.
3. Go back to the input screen (refresh or use a Back button).
4. Run the **exact same description** again.
5. Watch the event feed. Gate decisions should appear faster this time.
6. Check the Proof Panel for the second run.

**What to check:**
- [ ] Second run's gate calls complete noticeably faster (visible in timestamps or latency badges)
- [ ] Proof Panel for second run shows cache hits > 0
- [ ] "Tokens Saved" counter is non-zero on the second run
- [ ] Decisions in the second run match the first run (cache served consistent results)

---

## UC-8 — Different Use Case Domains

**Goal:** Confirm the classifier handles domains other than HR correctly.

**Steps — try each one separately:**

**A. Customer Support:**
> "Build an agent that reads customer complaints, classifies them as urgent or not, and drafts a reply."

**B. Code Review:**
> "Build an agent that reads a GitHub PR, checks for security issues, and comments on the PR."

**C. Data Pipeline:**
> "Build an agent that fetches sales data from a CSV, summarizes it, and emails a weekly report."

**For each:**
1. Enter the description and click Build.
2. Check the classification panel (domain, complexity, risk).
3. Check the topology options — they should differ from the HR scenario.

**What to check:**
- [ ] Domain field reflects the correct area (not "HR" for the code review scenario)
- [ ] Risk profile mentions relevant risks for each domain (e.g., "external API" for GitHub)
- [ ] Topology options have different descriptions/tradeoffs than HR
- [ ] Complexity varies (data pipeline might be "medium", customer support might be "low")

---

## UC-9 — Viewing the Audit Log

**Goal:** Confirm the full audit trail is readable and complete.

**Steps:**
1. Run the biased rubric scenario (UC-2) and make a decision in the Flag Modal.
2. Navigate to the **Audit Log** screen (button or tab after the run).
3. Review the log entries.

**What to check:**
- [ ] Each gate check appears as a row (agent name, tool, decision, tier, score)
- [ ] Your HITL decision appears as a separate row (labelled "human decision" or similar)
- [ ] Timestamps are in chronological order
- [ ] The Export button downloads a JSON file
- [ ] JSON file contains both `gate_events` and `human_decisions` arrays
- [ ] The JSON is valid (you can open it in a JSON viewer without errors)

---

## UC-10 — Empty / Edge-Case Inputs

**Goal:** Confirm the app handles bad inputs gracefully (no crashes, clear error messages).

**Steps:**
1. Submit an **empty description** — click Build without typing anything.
2. Submit a **very short description** — just "agent".
3. Submit a **very long description** — paste 2000+ characters of gibberish.
4. Submit a description that is just symbols: `!@#$%^&*()`.

**What to check:**
- [ ] Empty description shows a validation message (not a white screen or 500 error)
- [ ] "agent" alone either asks for more info or produces a low-confidence classification
- [ ] Long input does not crash the page or the server
- [ ] Symbol-only input is handled without an unhandled exception in the browser console
- [ ] Error messages are in plain English (not raw JSON or stack traces)

---

## UC-11 — Sponsor Activity Feed

**Goal:** Confirm the live sponsor timeline shows the right technology at the right moment.

**Steps:**
1. Run any agent scenario.
2. While the run is active, watch the **Sponsor Log / Activity Feed** panel.

**What to check:**
- [ ] Anthropic logo/badge appears when a Claude model is called
- [ ] Redis badge appears when a cache lookup or gate event fires
- [ ] Arize badge appears when a trace is recorded
- [ ] Each entry has a timestamp and short description
- [ ] The feed updates in real time (not only at the end of the run)

---

## UC-12 — Mobile / Small Screen Layout

**Goal:** Confirm the UI is usable on a narrow viewport.

**Steps:**
1. Open browser DevTools → toggle device emulation → choose "iPhone 14" or similar.
2. Work through UC-1 on the narrow viewport.

**What to check:**
- [ ] Input box is full-width and readable
- [ ] Topology cards stack vertically (not cut off)
- [ ] Agent graph is scrollable or zoomable (not clipped)
- [ ] Flag Modal is not cut off at the bottom
- [ ] Proof Panel numbers are readable (not overflowing)

---

## Quick Reference — Customization Guide

You can adapt any use case above by swapping in a different description. Here are some useful variables to change:

| Variable | Example values to try |
|----------|-----------------------|
| Domain | HR, legal document review, financial fraud detection, code review |
| Bias type | university ranking, gender-coded language, age (years of experience as proxy) |
| Dangerous action | Delete all records, send email to everyone, drop database, override all scores |
| Volume | Single candidate vs. 1000 candidates (stress) |
| Decision type | Approve Fix, Override, Modify with custom values |
| Run frequency | Once, twice back-to-back (tests cache), 5x rapid (tests concurrency) |
