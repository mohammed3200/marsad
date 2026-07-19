"""settings.json load / save — the single config the connectors + engine read.

Keys: ai_backend, ollama_url, ollama_model, claude_api_key, claude_model,
email_dept_map, whatsapp_groups (+ optional email/erp connector config).
"""
import json

from core.paths import DATA_DIR, BUNDLE_DIR

SETTINGS_F  = DATA_DIR / "settings.json"       # writable per-user config
EXAMPLE_F   = BUNDLE_DIR / "settings.example.json"  # shipped template / seed

_DEFAULTS = {
    "ai_backend":      "ollama",
    "ollama_url":      "http://localhost:11434",
    "ollama_model":    "llama3.2",
    "claude_api_key":  "",
    "claude_model":    "claude-opus-4-5",
    "email_dept_map":  {},
    "whatsapp_groups": {},
}


def load_settings() -> dict:
    """Load settings.json, falling back to the example template, then defaults."""
    for path in (SETTINGS_F, EXAMPLE_F):
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                merged = dict(_DEFAULTS)
                merged.update(data)
                return merged
            except Exception:
                continue
    return dict(_DEFAULTS)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_F, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
