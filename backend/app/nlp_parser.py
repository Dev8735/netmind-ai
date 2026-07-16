import spacy

nlp = spacy.load("en_core_web_sm")

DEVICE_KEYWORDS = [
    "switch", "router", "firewall", "access point", "ap", "server",
    "modem", "gateway", "load balancer", "core switch"
]

ISSUE_KEYWORDS = {
    "down": "connectivity", "no ping": "connectivity", "unreachable": "connectivity",
    "slow": "performance", "high cpu": "performance", "latency": "performance",
    "flapping": "connectivity", "drop": "connectivity", "drops": "connectivity",
    "no response": "connectivity", "not responding": "connectivity",
    "config": "configuration", "misconfigured": "configuration",
    "hardware": "hardware", "fault": "hardware", "power": "hardware"
}


def extract_device(text: str) -> str:
    text_lower = text.lower()
    for device in DEVICE_KEYWORDS:
        if device in text_lower:
            return device.title()
    return "Unknown"


def extract_category(text: str) -> str:
    text_lower = text.lower()
    for keyword, category in ISSUE_KEYWORDS.items():
        if keyword in text_lower:
            return category.title()
    return "Uncategorized"


def extract_keywords(text: str) -> list:
    doc = nlp(text)
    keywords = [token.text for token in doc if not token.is_stop and not token.is_punct and token.is_alpha]
    return keywords


def parse_incident(text: str) -> dict:
    return {
        "device": extract_device(text),
        "category": extract_category(text),
        "keywords": extract_keywords(text)
    }
import json
import urllib.request


def _call_ollama_for_parsing(text: str) -> dict:
    try:
        prompt = f"""Extract from this network incident text:
1. device (one of: switch, router, firewall, access point, server, modem, gateway, or "unknown")
2. category (one of: connectivity, performance, hardware, configuration, or "uncategorized")

Text: "{text}"

Respond with ONLY valid JSON like: {{"device": "switch", "category": "connectivity"}}"""

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
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
            llm_text = result.get("response", "").strip()
            parsed = json.loads(llm_text)
            return {
                "device": parsed.get("device", "unknown").title(),
                "category": parsed.get("category", "uncategorized").title()
            }
    except Exception as e:
        print(f"[nlp_parser] Ollama fallback unavailable: {e}")
        return None


def parse_incident_with_fallback(text: str) -> dict:
    result = parse_incident(text)

    if result["device"] == "Unknown" or result["category"] == "Uncategorized":
        llm_result = _call_ollama_for_parsing(text)
        if llm_result:
            if result["device"] == "Unknown":
                result["device"] = llm_result["device"]
            if result["category"] == "Uncategorized":
                result["category"] = llm_result["category"]

    return result