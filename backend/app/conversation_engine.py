import json
import urllib.request


def _call_ollama(prompt: str) -> str:
    """Same pattern as alert_generator._call_ollama: template is always
    computed first and used as ground truth; Ollama, if available, only
    rewrites/answers using that ground truth. Shorter timeout than the
    alert generator since this is used interactively."""
    try:
        data = json.dumps({
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        print(f"[conversation_engine] Ollama unavailable, using template fallback: {e}")
        return None


def _top_cause(diagnosis):
    if not diagnosis or not diagnosis.get("matched") or not diagnosis.get("causes"):
        return None
    return diagnosis["causes"][0]


# ---------- Canned questions: always answered deterministically from the
# incident's own diagnosis data, no Ollama needed. Fast and reliable for
# a live demo, and the exact button label is the dict key so the frontend
# can send it verbatim. ----------

def _answer_why_this_cause(diagnosis, similar_incidents):
    cause = _top_cause(diagnosis)
    if not cause:
        return "No confident cause was identified for this incident, so there's no top cause to explain - it needs manual engineer review."

    matched_kw = cause.get("matched_keywords") or []
    match_text = f"matching keywords: {', '.join(matched_kw)}" if matched_kw else "a semantic match with no exact keyword overlap"

    return (
        f"\"{cause['cause']}\" was ranked as the top cause because it scored a similarity of "
        f"{cause.get('similarity_score', 'n/a')} against the knowledge base, with {match_text}. "
        f"That gives it a {cause['probability']}% probability among the candidates considered. "
        f"Business impact: {cause.get('business_impact') or 'not specified'}."
    )


def _answer_confidence(diagnosis, similar_incidents):
    if not diagnosis or not diagnosis.get("matched"):
        return "No confident match was found in the knowledge base for this incident, so it falls back to manual engineer review rather than an automated diagnosis."

    confidence = diagnosis.get("confidence", "unknown")
    score = diagnosis.get("confidence_score", "n/a")

    if confidence == "high":
        note = "High confidence means the top cause is well-supported and, if its fault type is on the auto-remediation whitelist, it may be fixed automatically with no engineer action."
    elif confidence == "medium":
        note = "Medium confidence means the top cause is a reasonable candidate, but it's worth verifying against the suggested command before acting."
    else:
        note = "Low confidence means the match is weak - treat the ranked causes as starting points for investigation, not a firm diagnosis."

    return f"This diagnosis has {confidence.upper()} confidence (score: {score}). {note}"


def _answer_remediation_fallback(diagnosis, similar_incidents):
    cause = _top_cause(diagnosis)
    if not cause:
        return "There's no confident diagnosis here to base a remediation on - start with manual investigation."

    causes = diagnosis.get("causes", [])
    if len(causes) > 1:
        next_cause_note = (
            f" is \"{causes[1]['cause']}\" ({causes[1]['probability']}% likely) - check that next."
        )
    else:
        next_cause_note = " isn't available here - escalate to manual engineer review at that point."

    return (
        f"If the suggested fix doesn't resolve it: first re-run the verification command "
        f"(`{cause['verification_command']}`) to confirm the fault is actually still present. "
        f"If it is, the next most likely cause" + next_cause_note
    )


def _answer_what_to_check_first(diagnosis, similar_incidents):
    cause = _top_cause(diagnosis)
    if not cause:
        return "No confident cause was identified, so start with general troubleshooting: check device connectivity, recent config changes, and logs."

    return (
        f"Start by running: `{cause['verification_command']}`. "
        f"Then: {cause['troubleshooting_steps']}"
    )


def _answer_similar_incidents(diagnosis, similar_incidents):
    if not similar_incidents:
        return "No past incidents share this diagnosed cause yet - this appears to be a new pattern, or the cause isn't tagged with a fault_type for cross-referencing."

    count = len(similar_incidents)
    devices = sorted(set(i["device"] for i in similar_incidents))
    resolved = sum(1 for i in similar_incidents if i["status"] in ("Resolved", "Auto-Resolved"))

    return (
        f"Yes - {count} past incident{'s' if count != 1 else ''} share this same diagnosed cause, "
        f"across device{'s' if len(devices) != 1 else ''}: {', '.join(devices)}. "
        f"{resolved} of them {'have' if resolved != 1 else 'has'} already been resolved."
    )


CANNED_QUESTIONS = {
    "Why this cause?": _answer_why_this_cause,
    "How confident is this?": _answer_confidence,
    "What if remediation fails?": _answer_remediation_fallback,
    "What should I check first?": _answer_what_to_check_first,
    "Are there similar past incidents?": _answer_similar_incidents,
}


def _build_context_summary(diagnosis, similar_incidents):
    """Plain-text summary of everything known about this incident, used
    as grounding context for both the free-form Ollama prompt and its
    template fallback."""
    if not diagnosis or not diagnosis.get("matched"):
        return "No confident diagnosis is available for this incident."

    lines = [f"Confidence: {diagnosis.get('confidence', 'unknown')} (score: {diagnosis.get('confidence_score', 'n/a')})"]
    for idx, c in enumerate(diagnosis.get("causes", []), 1):
        lines.append(
            f"{idx}. {c['cause']} ({c['probability']}% likely) - verify with `{c['verification_command']}`, "
            f"then: {c['troubleshooting_steps']}"
        )
    if diagnosis.get("rejected_causes"):
        lines.append("Ruled out: " + "; ".join(r["cause"] for r in diagnosis["rejected_causes"]))
    if similar_incidents:
        lines.append(f"{len(similar_incidents)} past incidents share this diagnosed cause.")

    return "\n".join(lines)


def answer_question(question: str, diagnosis: dict, similar_incidents: list) -> str:
    canned = CANNED_QUESTIONS.get(question.strip())
    if canned:
        return canned(diagnosis, similar_incidents)

    # Free-form question: try Ollama grounded in the incident's actual
    # data, fall back to a template summary if unavailable.
    context = _build_context_summary(diagnosis, similar_incidents)
    prompt = f"""You are a network operations assistant. Answer the engineer's question using
ONLY the incident information below. Do not invent facts not present here. If the
information doesn't answer the question, say so plainly. Keep the answer to 2-4 sentences.

Incident diagnosis:
{context}

Engineer's question: {question}

Answer:"""

    llm_response = _call_ollama(prompt)
    if llm_response:
        return llm_response

    return (
        f"(Ollama unavailable - showing what's known about this incident instead)\n\n{context}\n\n"
        f"Try one of the suggested questions above for a more specific answer, "
        f"or check back once Ollama is running for free-form questions."
    )