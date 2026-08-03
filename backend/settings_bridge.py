"""settings.json load / save — the single config the connectors + engine read.

Keys: ai_backend, ollama_url, ollama_model, claude_api_key, claude_model,
email_dept_map, whatsapp_groups (+ optional email/erp connector config).
"""
import json
import os
import tempfile

from core.paths import DATA_DIR, BUNDLE_DIR

SETTINGS_F  = DATA_DIR / "settings.json"       # writable per-user config
EXAMPLE_F   = BUNDLE_DIR / "settings.example.json"  # shipped template / seed

_DEFAULTS = {
    "ai_backend":       "ollama",
    "ollama_url":       "http://localhost:11434",
    "ollama_model":     "llama3.2",
    "claude_api_key":   "",
    "claude_model":     "claude-opus-4-5",
    # OpenAI + OpenAI-compatible (OpenRouter / Groq / Together / DeepSeek / LM Studio)
    "openai_api_key":   "",
    "openai_base_url":  "https://api.openai.com/v1",
    "openai_model":     "gpt-4o-mini",
    # Google Gemini
    "gemini_api_key":   "",
    "gemini_model":     "gemini-2.0-flash",
    # Azure OpenAI
    "azure_endpoint":    "",
    "azure_api_key":     "",
    "azure_deployment":  "",
    "azure_api_version": "2024-06-01",
    "ai_timeout":       180,
    # email / ERP connector config (settable from the Settings UI)
    "email_user":       "",
    "email_password":   "",
    "imap_host":        "imap.gmail.com",
    "smtp_host":        "smtp.gmail.com",
    "smtp_port":        587,
    "report_recipients": [],
    "erp_folder":       "",
    # whatsapp bridge
    "whatsapp_enabled": False,
    "whatsapp_port":    5051,
    "whatsapp_token":   "",
    "email_dept_map":   {},
    "whatsapp_groups":  {},
    # engine profiles — ملفات محرّك محفوظة قابلة للتبديل (الافتراضي Ollama)
    "engine_profiles":  [],
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


def save_settings(settings: dict, changed_keys=None) -> None:
    """Persist settings atomically with owner-only permissions.

    `changed_keys` limits the write to those keys, re-reading whatever is on
    disk first — so a second process editing a different key is not clobbered.
    """
    if changed_keys:
        merged = load_settings()
        for key in changed_keys:
            if key in settings:
                merged[key] = settings[key]
        settings = merged

    SETTINGS_F.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(SETTINGS_F.parent),
                               prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, SETTINGS_F)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
