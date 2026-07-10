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