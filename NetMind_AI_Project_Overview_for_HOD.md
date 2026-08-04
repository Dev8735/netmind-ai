# NetMind AI  Project Overview for HOD Presentation

## One-line positioning

**NetMind AI is an Explainable AI Decision Support System for network fault
diagnosis**  it doesn't just guess a root cause, it shows the evidence, the
confidence, the alternatives it ruled out, and lets an engineer question it directly,
before anyone has to act on its output.

## Why "decision support" and not "autonomous AI"

This is a deliberate framing choice, not a limitation to apologize for. A tool that
hands a network engineer a single confident-sounding answer with no way to verify it is
actually *less* useful in a production environment than one that shows its reasoning 
because the engineer has to trust it blindly or independently re-verify everything
anyway, which defeats the purpose. NetMind AI is built so the second option is never
necessary: every output is auditable on its own.

The one exception is auto-remediation, which *is* fully autonomous  but only for a
narrow, explicitly whitelisted set of safe, config-only fault types, and only when
confidence is high. Everything else is decision support, not decision replacement.

## What the system actually does (in order of a typical incident's lifecycle)

1. **Ingests** a real network event  either via genuine UDP Syslog (RFC 5424, the same
   protocol real Cisco/Juniper hardware uses) or a manually typed report
2. **Parses** it with spaCy NLP, with an LLM fallback for messy or unusual phrasing
3. **Diagnoses** it by comparing against a 165-entry knowledge base using sentence-
   embedding similarity, combined with keyword and device/category correlation
4. **Scores confidence** (high / medium / low)  and this score gates what happens next
5. **Shows its work**: ranked candidate causes with similarity scores and matched
   keywords, business impact, and  critically  the causes it *considered and ruled
   out*, with the specific reason each was rejected
6. **Acts automatically** only if confidence is high AND the top cause is a known-safe,
   config-only fault type on an explicit whitelist (e.g. an administratively shut down
   port)  everything else goes to an engineer for review
7. **Answers questions** about that specific incident on demand  either via one-click
   canned questions or free text, grounded only in that incident's own diagnosis data
8. **Learns from mistakes**  if an engineer marks a diagnosis wrong, they specify the
   actual cause, and it's logged visibly in a Corrections Log rather than silently
   discarded

## Why not a "real" ML model (Random Forest, XGBoost, GNN, RL, RAG)?

Because none of them would actually be better here, given what data exists. All of
those approaches need labeled training data at production scale to outperform a
well-tuned similarity-and-rules system  and that data doesn't exist for this problem
yet (165 hand-curated KB entries and a session's worth of test incidents is nowhere
near enough to train a model that wouldn't just overfit or hallucinate). The embedding-
similarity approach used here is also inherently more explainable: a Random Forest's
decision boundary isn't inspectable by a network engineer in the room; a "this incident
is 0.87 similar to a known port-shutdown pattern, matching these three keywords" is.

This is explicitly documented as a scope decision, not an oversight  see "Future
Scope" in the README.

## Demo walkthrough (suggested order)

1. **Submit an incident** with genuinely ambiguous phrasing  show it still gets a
   ranked diagnosis, with an honest low-confidence label rather than a false-confident
   guess
2. **Open a high-confidence incident**  point out the evidence chips (similarity,
   matched keywords, business impact), then expand "Other causes considered and ruled
   out" to show the negative reasoning is visible too
3. **Show an auto-resolved incident**  the remediation log proves exactly what command
   was run and why it was safe to run automatically
4. **Click "Ask NetMind AI"** on that same incident  ask "Why this cause?" and then a
   free-form question, showing the answers stay grounded in that incident specifically
5. **Open the AI Performance Dashboard**  show measured accuracy by confidence tier 
   this is real data from engineer feedback, not a claimed number
6. **Open the Corrections Log**  show a logged mistake, framed as evidence the system
   is auditable and improvable, not perfect and hidden
7. **Open the Admin Panel** (separate password)  walk through the Decision Tree
   Explorer for a symptom group, and the Knowledge Graph showing which fault types span
   multiple device types in real incident history

## Anticipated questions and honest answers

**"How accurate is it really?"**
Check the live AI Performance Dashboard rather than quoting a fixed number  it's
computed from actual engineer feedback and updates as more incidents are rated.

**"What happens when it's wrong?"**
It gets logged in the Corrections Log with what the AI said versus what was actually
correct. This is visible, not swept away  and it's the intended mechanism for
eventually improving the knowledge base.

**"Could this replace an engineer?"**
No, and it's not built to. Auto-remediation only covers a narrow, safe whitelist. Every
other diagnosis is explicitly framed as "pending engineer confirmation."

**"Why only 165 knowledge base entries  is that enough?"**
It's enough to demonstrate the architecture and explainability approach end-to-end.
Only ~15 entries currently have a `fault_type` tag (needed for cross-referencing
features like similarity search and the knowledge graph)  expanding that tagging is
the single highest-leverage next step for making those features more useful, and
requires no architecture changes, just more curated data.

**"What would it take to connect this to real hardware?"**
No architecture change  see `docs/protocol.md`. Real devices would point their Syslog
output at the listener's address (port 514 in production instead of the current 5140,
which is only used to avoid needing admin/root privileges during development).

## Current build status (Phase 3, Explainable AI)

Days 1-15 of a 20-day plan are complete: the core diagnosis/remediation bug fixes,
full explainability (evidence, rejected causes, business impact) across the dashboard
and PDF reports, an AI performance dashboard, incident similarity search, a decision
tree explorer and knowledge graph (moved into a separate password-gated Admin Panel),
Learning Mode with a visible Corrections Log, and Scoped AI Conversation. Remaining:
finishing this repositioning pass, a full stress-test/bug-buffer pass, and final
presentation prep.
