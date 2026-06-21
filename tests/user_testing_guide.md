# SafeAgent — User Testing Guide

> **How to use this guide:** Each use case below describes a scenario you can perform in the browser with no technical knowledge needed. Read the "What to do" steps, then check "What to expect" to confirm the app is working correctly. Note your observations in the "Your notes" column.

---

## Quick Start

1. Open the SafeAgent app in your browser
2. Make sure the backend is running (`http://localhost:8001` for local testing)
3. Work through the use cases in order (they build on each other)

---

## Use Case 1: Basic Hiring Agent (Golden Path)

**Goal:** Verify the core happy path works end-to-end.

**What to do:**
1. On the input screen, type this description:  
   > *"Build an agent to screen resumes, score candidates fairly on skills and experience, and email a shortlist to the hiring manager."*
2. Click **Submit** or press Enter
3. Wait for the two topology options to appear (may take 10–20 seconds)
4. Read both topology cards (Option A: Supervisor-Worker, Option B: ReAct)
5. Click **Select** on the recommended option (it should be highlighted)
6. Wait for the agent graph to appear (another 5–10 seconds)
7. Click **Run Agent**
8. Watch the agent cards update in real-time as agents execute
9. When the safety gate flags the scoring step, read the modal that appears
10. Click **Approve Fix** and wait for the run to complete
11. Review the Proof Panel metrics (cost, latency, cache hits)

**What to expect:**
- [ ] Loading indicators appear while calling AI APIs
- [ ] Both topology options display with different cost/latency estimates
- [ ] The recommended option is visually marked
- [ ] The agent graph shows Parser → Scorer → Email nodes connected with arrows
- [ ] The run screen shows each agent card (Parser, Scorer, Email) updating from idle → running → done
- [ ] A **safety gate modal** appears during the Scorer step, showing misalignment/oversight scores ≥ 70
- [ ] The modal shows an **Auto-Fix** with a safer rubric
- [ ] After approving the fix, the remaining agents complete
- [ ] The Proof Panel shows actual cost vs. predicted cost, cache hit rate, and safety gate summary

**Your notes:**
```
What worked:
What didn't:
Any confusion:
```

---

## Use Case 2: Different Domain — Customer Support

**Goal:** Test that SafeAgent works for a different use case, not just hiring.

**What to do:**
1. Reload the page (start fresh)
2. Type this description:  
   > *"Build an agent to handle customer support tickets, classify them by severity, look up the customer's order history, and draft personalized response emails."*
3. Submit and go through the full flow (topology → scaffold → run)
4. Compare the topology options with what you saw in Use Case 1
5. Run the agent and watch what happens

**What to expect:**
- [ ] Topology options appear with different cost/latency estimates than the hiring case
- [ ] The agent graph shows different agent names (e.g., Classifier, LookupAgent, Responder)
- [ ] The run may proceed differently (different agents, different gate behavior)
- [ ] Proof Panel shows telemetry specific to this run

**Your notes:**
```
How was this different from the hiring use case?
Did the topology recommendation make sense?
```

---

## Use Case 3: Topology Comparison (A vs B)

**Goal:** Understand what happens when you pick the non-recommended topology.

**What to do:**
1. Start a new session with the hiring description from Use Case 1
2. On the topology screen, **don't** pick the recommended option
3. Click **Select** on the other option instead (e.g., ReAct if Supervisor-Worker is recommended)
4. Complete the flow (scaffold, run, proof)
5. Compare the Proof Panel to what you saw in Use Case 1

**What to expect:**
- [ ] You can select either topology — both are clickable
- [ ] The scaffolded blueprint looks different (different agent structure or fewer/more nodes)
- [ ] The Proof Panel's A/B comparison chart shows both topology costs side by side
- [ ] The "A/B Winner" section at the bottom of the Proof Panel shows a recommendation

**Your notes:**
```
Did the non-recommended option produce a noticeably different result?
Was the comparison chart helpful?
```

---

## Use Case 4: Safety Gate — HITL Options

**Goal:** Test all three Human-in-the-Loop (HITL) decision options when the gate fires.

**Sub-test A: Approve Fix**
1. Run the hiring agent (Use Case 1)
2. When the gate modal appears, read the "Auto-Fix" suggestion
3. Click **Approve Fix**
4. Observe: the flagged agent resumes with the safer parameters

**Sub-test B: Modify**
1. Run the hiring agent again
2. When the gate modal appears, look for a way to edit the parameters
3. Make a small change (e.g., reduce one rubric weight)
4. Click **Modify / Submit**
5. Observe: the agent continues with your custom parameters

**Sub-test C: Override (Bypass)**
1. Run the hiring agent again
2. When the gate modal appears, click **Override** (or "Proceed Anyway")
3. Observe: the original (potentially biased) parameters are used; a warning is noted in the audit log

**What to expect for all three:**
- [ ] Each HITL decision allows the run to continue (never crashes)
- [ ] The Audit Log (click "Audit" in the nav) reflects which decision was made
- [ ] The Proof Panel's "Safety Gate Summary" shows your decisions (Approved Fix / Modified / Overridden)

**Your notes:**
```
Was the auto-fix explanation clear and understandable?
Was modifying parameters intuitive?
Did the override warning feel appropriately prominent?
```

---

## Use Case 5: Export & Download

**Goal:** Verify the export functionality works correctly.

**What to do:**
1. Complete a full run (any use case above)
2. On the Proof Panel, click **Export Blueprint JSON**
3. Open the downloaded file in a text editor or browser
4. Read through the structure — it should contain agent definitions, gate events, and HITL decisions
5. Go back and click the **Download Code** button (if visible on the scaffold screen)
6. Open the `.py` file — it should contain runnable Python code

**What to expect:**
- [ ] A `.json` file downloads with an audit trail of the entire session
- [ ] The JSON includes: session ID, agents, edges, gate events, human decisions
- [ ] A `.py` file downloads containing Python code with `StateGraph` and agent definitions
- [ ] The Python code is readable and includes the blueprint topology as a comment

**Your notes:**
```
Was the JSON file readable and complete?
Could a developer use the Python file to run the agent independently?
```

---

## Use Case 6: Error Handling & Edge Cases

**Goal:** Test how the app handles bad inputs and edge cases gracefully.

**Sub-test A: Empty Input**
1. Click Submit with an empty description field
2. Observe: what error or feedback is shown?

**Sub-test B: Very Short Input**
1. Type just "help me" and submit
2. Observe: does classification still work? Does it make sense?

**Sub-test C: Very Long Input**
1. Paste a very long description (500+ words) about a complex agent system
2. Submit and go through the flow
3. Observe: does it handle long inputs without timing out?

**Sub-test D: Refresh During Run**
1. Start a run and immediately refresh the browser
2. Observe: what happens to the in-progress run?

**What to expect:**
- [ ] Empty input shows an error message, not a crash
- [ ] Short input like "help me" produces some classification (even if imprecise)
- [ ] Long input works (may be slower)
- [ ] Refresh during a run: the run is lost (in-memory state), but the app returns to a clean state without errors

**Your notes:**
```
Were error messages clear and helpful?
Any unexpected crashes?
```

---

## Use Case 7: Proof Panel Metrics Review

**Goal:** Verify the telemetry/metrics section is meaningful and accurate.

**What to do:**
1. Complete a full hiring agent run with the standard biased rubric
2. On the Proof Panel, review each section:
   - **Predicted vs Actual Cost** — are they in the same ballpark?
   - **Redis Cache Hits** — does the hit count go up on repeated runs with the same rubric?
   - **Auto-Fix Eval Score** — does it say the fix addressed the flag?
   - **Safety Drift Chart** — does it show a score drop after the fix was applied?
   - **A/B Topology Comparison** — are both bars visible with different heights?
   - **Per-Agent Breakdown** — are all three agents (Parser, Scorer, Email) shown?
3. Run the agent a second time with the same prompt
4. Compare the cache hit rate — it should be higher on the second run

**What to expect:**
- [ ] Cost variance is shown with a clear label (+X% or −X%)
- [ ] Cache hit rate increases on repeat runs
- [ ] Auto-fix eval score ≥ 80% (green highlight)
- [ ] Safety drift chart shows three data points (run 1, 2, 3)
- [ ] Per-agent breakdown identifies Parser, Scorer, or Email as the bottleneck

**Your notes:**
```
Were the charts legible?
Did any numbers seem wrong or confusing?
```

---

## Use Case 8: Audit Log Review

**Goal:** Verify the audit trail captures all events accurately.

**What to do:**
1. Complete a full run with at least one HITL decision
2. Click **Audit** in the top navigation bar
3. Review the list of events:
   - Gate events (each tool call the gate checked)
   - HITL decisions (what you clicked: Approve Fix, Modify, Override)
   - Agent actions (start/complete for each agent)
4. Verify the timestamps are in order
5. Try downloading the audit export from the Proof Panel

**What to expect:**
- [ ] Gate events show the tool name, decision (ALLOW/WARN/BLOCK), and score
- [ ] HITL events show your decision and which agent it applied to
- [ ] Events are in chronological order
- [ ] The downloaded JSON matches what the audit log shows

**Your notes:**
```
Was it clear what each audit event meant?
Any events missing that you'd expect to see?
```

---

## Use Case 9: Research / General Use Case

**Goal:** Test SafeAgent with a completely different domain to check generalizability.

**What to do:**
1. Try this description:  
   > *"Build a research agent that searches academic papers, summarizes findings, identifies conflicting studies, and generates a literature review draft."*
2. Go through the full flow
3. Note how the agent graph differs from hiring and customer support

**What to expect:**
- [ ] Classification identifies this as a "research" domain
- [ ] Topology options still appear (may have different reasoning)
- [ ] Agent graph has research-appropriate names (Searcher, Summarizer, Analyzer, Writer — or similar)
- [ ] Gate may or may not fire depending on the tools used

**Your notes:**
```
Did the agent design make sense for research use cases?
Were the tool names and agent roles appropriate?
```

---

## Use Case 10: Sponsor/Activity Log

**Goal:** Verify the real-time activity log shows which AI services are being used.

**What to do:**
1. Start a run from the scaffold screen
2. While the run is in progress, look at the **Activity Log** panel (bottom or side panel)
3. Watch new entries appear in real time as each step completes
4. Identify entries from: Anthropic (Claude), Redis, Arize, and (if configured) Deepgram

**What to expect:**
- [ ] New log entries appear in real time (not all at once)
- [ ] Entries mention Claude Haiku 4.5 for fast classification steps
- [ ] Entries mention Claude Sonnet 4.6 for safety gate T3 scoring
- [ ] Redis cache entries show T1/T2/T3 tier and latency
- [ ] Arize entries show trace events for each agent

**Your notes:**
```
Was it clear which AI service was being used at each step?
Did the real-time updates feel smooth?
```

---

## Summary Scorecard

After completing your testing, fill in this quick scorecard:

| Area | Works (✓) | Partial (⚠) | Broken (✗) | Notes |
|------|-----------|-------------|------------|-------|
| Input & Classification | | | | |
| Topology Picker | | | | |
| Agent Graph Display | | | | |
| Run Execution & SSE | | | | |
| Safety Gate Modal | | | | |
| HITL: Approve Fix | | | | |
| HITL: Modify | | | | |
| HITL: Override | | | | |
| Proof Panel Metrics | | | | |
| Audit Log | | | | |
| Blueprint JSON Export | | | | |
| Python Code Export | | | | |
| Activity Log | | | | |
| Error Handling | | | | |

**Overall impression:** ___/10

**Biggest issue:** 

**Most impressive feature:**

**Suggested improvement:**
