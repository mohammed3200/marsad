"""Single source of truth for the fixed Arabic status literals.

Every surface — the PDF, the Excel workbook, the emailed HTML and the Qt theme
— must agree on which tier a literal belongs to. Before this module they did
not: `متوسط` was amber in the PDF and red in Excel and in email, and the
`غير محدد` value that `_ensure_chief_schema` writes when the coordinator agent
fails was rendered as a critical-red banner instead of a neutral one.
"""

_GOOD = {"جيد", "مكتمل", "آمن", "منخفضة", "منخفض", "ناجح"}
_WARN = {"متوسط", "متوسطة", "تحذير", "في الموعد", "قيد التنفيذ"}
_BAD  = {"متأخر", "خطر", "عالية", "عالٍ", "حرج", "فشل"}


def tier(literal) -> str:
    """Map a status literal to good / warn / bad / neutral.

    Anything unrecognised — including empty and `غير محدد` — is neutral, never
    critical: an unknown status is missing information, not an alarm.

    `literal` is whatever the model actually returned, which is not
    guaranteed to be a string — `_ensure_chief_schema` only guarantees the
    *keys* exist, never their value types. A list-wrapped string
    (`["جيد"]`), a dict (`{"v": "متأخر"}`) or a bare int (`1`) must not
    raise here: `str(x)` turns each into something that simply won't match
    any tier and falls through to neutral, exactly like any other unknown
    value.
    """
    s = str(literal or "").strip()
    if s in _GOOD:
        return "good"
    if s in _WARN:
        return "warn"
    if s in _BAD:
        return "bad"
    return "neutral"
