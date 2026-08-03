import json
import urllib.request


def _call_ollama(prompt: str, timeout: int = 45) -> str:
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
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        print(f"[conversation_engine] Ollama unavailable, using template fallback: {e}")
        return None


def _build_context_summary(incident, diagnosis, similar_incidents):
    """Plain-text summary of everything the conversation is scoped to -
    used both as the Ollama prompt context and as raw material for the
    template fallback answers."""
    lines = [
        f"Device: {incident.device_type}",
        f"Issue reported: {incident.incident_description}",
        f"Severity: {incident.priority}",
        f"Status: {incident.status}",
    ]

    if diagnosis and diagnosis.get("matched"):
        confidence = diagnosis.get("confidence", "unknown")
        confidence_score = diagnosis.get("confidence_score", 0)
        lines.append(f"Diagnosis confidence: {confidence} (score: {confidence_score})")
        for i, c in enumerate(diagnosis["causes"], 1):
            kw = ", ".join(c.get("matched_keywords", [])) or "semantic match only"
            lines.append(
                f"Cause {i}: {c['cause']} ({c['probability']}% probability) - "
                f"similarity {c.get('similarity_score', 0)}, matched keywords: {kw}. "
                f"Verify with: {c['verification_command']}. Steps: {c['troubleshooting_steps']}. "
                f"Business impact: {c.get('business_impact') or 'not specified'}."
            )
        rejected = diagnosis.get("rejected_causes") or []
        if rejected:
            for r in rejected:
                lines.append(f"Ruled out: {r['cause']} - {r['reason']}")
    else:
        lines.append("No confident diagnosis match was found in the knowledge base.")

    if incident.remediation_log:
        lines.append(f"Automated remediation log: {incident.remediation_log}")

    if similar_incidents:
        statuses = [s["status"] for s in similar_incidents]
        resolved_count = sum(1 for s in statuses if s in ("Resolved", "Auto-Resolved"))
        lines.append(
            f"Similar past incidents with the same diagnosed cause: {len(similar_incidents)} found, "
            f"{resolved_count} of which were resolved."
        )
    else:
        lines.append("No similar past incidents found with the same diagnosed cause.")

    return "\n".join(lines)


def _template_answer(question: str, incident, diagnosis, similar_incidents):
    """Rule-based canned answers for common question patterns - always
    available even when Ollama is down or times out."""
    q = question.lower()

    if not diagnosis or not diagnosis.get("matched"):
        return (
            "No confident diagnosis was reached for this incident, so I don't have a "
            "specific cause to explain. This one needs manual engineer review."
        )

    top_cause = diagnosis["causes"][0]

    if any(kw in q for kw in ["why", "cause", "reason"]):
        kw = ", ".join(top_cause.get("matched_keywords", [])) or "semantic similarity alone (no exact keyword overlap)"
        return (
            f"The top diagnosed cause is \"{top_cause['cause']}\" at {top_cause['probability']}% "
            f"probability. This was matched with a similarity score of {top_cause.get('similarity_score', 0)}, "
            f"based on: {kw}. Overall confidence in this diagnosis is "
            f"{diagnosis.get('confidence', 'unknown')} ({diagnosis.get('confidence_score', 0)})."
        )

    if any(kw in q for kw in ["fail", "doesn't work", "does not work", "if it doesn't", "wrong"]):
        return (
            f"If \"{top_cause['cause']}\" turns out not to be the actual cause, the next step is to "
            f"check the other ranked and ruled-out causes in this incident's diagnosis panel, or escalate "
            f"to manual review. You can also mark this diagnosis unhelpful with the correct cause - that "
            f"gets logged in the Corrections Log for future reference."
        )

    if any(kw in q for kw in ["confiden", "sure", "certain"]):
        return (
            f"Confidence is {diagnosis.get('confidence', 'unknown')} "
            f"(score: {diagnosis.get('confidence_score', 0)}). High confidence generally means the top "
            f"cause scored decisively above the alternatives; medium or low confidence means the ranked "
            f"causes were closer together and worth reviewing manually before acting."
        )

    if any(kw in q for kw in ["similar", "before", "past", "happened"]):
        if similar_incidents:
            resolved = sum(1 for s in similar_incidents if s["status"] in ("Resolved", "Auto-Resolved"))
            return (
                f"There are {len(similar_incidents)} past incidents diagnosed with the same cause, "
                f"{resolved} of which were resolved. Check the \"Similar Past Incidents\" section in this "
                f"modal for the full list."
            )
        return "No similar past incidents have been diagnosed with the same cause yet."

    if any(kw in q for kw in ["verify", "check", "command"]):
        return f"To verify this diagnosis, run: {top_cause['verification_command']}"

    if any(kw in q for kw in ["fix", "step", "resolve", "solution"]):
        return f"Recommended steps: {top_cause['troubleshooting_steps']}"

    return (
        f"I can answer specific questions about this incident using what's already known: the "
        f"diagnosed cause ({top_cause['cause']}), confidence level, verification command, "
        f"remediation steps, and similar past incidents. Try asking about one of those, or use the "
        f"suggested questions above."
    )


def answer_question(question, incident, diagnosis, similar_incidents=None):
    context = _build_context_summary(incident, diagnosis, similar_incidents)
    template = _template_answer(question, incident, diagnosis, similar_incidents)

    prompt = f"""You are a network operations assistant. Answer the engineer's question using
ONLY the information below. Do not invent facts, numbers, or commands not present here.
Keep the answer to 2-4 sentences. If the question can't be answered from this information,
say so plainly.

Known information about this incident:
{context}

Engineer's question: {question}

Answer:"""

    llm_response = _call_ollama(prompt)
    return llm_response if llm_response else template