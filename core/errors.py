"""خريطة موحّدة لرسائل الأخطاء الظاهرة للمستخدم — UI-agnostic, no Qt.

friendly_error() يحوّل نصوص الأخطاء الخام (أكواد HTTP، استثناءات Python، ردود
المزوّدين) إلى رسالة عربية قصيرة قابلة للفهم والتصرّف. تستخدمه core/engine.py
و connectors.py — النصوص العربية الجاهزة تمرّ كما هي، والنص الخام لا يصل
الواجهة أبداً (يُسجَّل في logs/ عند الحاجة).
"""


def _has_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


# الترتيب مهم — الأكثر تحديداً أولاً. المفاتيح تُطابَق lowercase كنصوص فرعية.
_RULES = [
    (("authenticationfailed", "invalid credentials", "[alert]",
      "application-specific password", "app password"),
     "فشل تسجيل الدخول — تحقق من البريد وكلمة مرور التطبيق (App Password)، وليس كلمة المرور العادية"),
    (("429", "quota", "rate limit", "rate_limit", "resource_exhausted",
      "too many requests"),
     "تجاوزت حصة المزوّد — راجع خطتك والفوترة أو بدّل النموذج"),
    (("401", "403", "invalid api key", "unauthorized", "permission denied",
      "forbidden", "api key not valid"),
     "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح"),
    (("404", "not found", "no such model", "does not exist"),
     "النموذج أو العنوان غير موجود — تحقق من اسم النموذج والرابط"),
    (("400", "bad request"),
     "طلب مرفوض من المزوّد — راجع الإعدادات"),
    (("500", "502", "503", "504", "internal error", "unavailable",
      "bad gateway", "service unavailable"),
     "خلل في خادم المزوّد — حاول بعد قليل"),
    (("timed out", "timeout"),
     "انتهت مهلة الاتصال — الخادم لا يستجيب"),
    (("name resolution", "gaierror", "temporary failure", "errno -3", "errno -2"),
     "تعذّر حل اسم الخادم (DNS) — تحقق من اتصال الإنترنت"),
    (("connection refused", "name or service", "getaddrinfo", "nodename",
      "no route to host", "unreachable", "failed to establish", "eof occurred"),
     "تعذّر الوصول إلى الخادم — تحقق من العنوان والشبكة"),
    (("ssl", "certificate", "cert_verify"),
     "خطأ في شهادة الأمان (SSL)"),
    (("json_parse", "expecting value", "jsondecode"),
     "رد المزوّد غير مفهوم"),
]


def friendly_error(raw) -> str:
    """حوّل نص خطأ خام إلى رسالة عربية موجزة للواجهة.

    - النصوص العربية الجاهزة تمرّ دون تغيير.
    - الأنماط المعروفة (429، AUTHENTICATIONFAILED، timeouts…) تُترجم لرسالة قابلة للتصرّف.
    - أي نص آخر يُقصّ إلى سطر واحد ≤ ٨٠ حرفاً مع بادئة عربية.
    """
    text = str(raw or "").strip()
    if not text:
        return "خطأ غير معروف"
    if _has_arabic(text):
        return text
    low = text.lower()
    for keys, msg in _RULES:
        if any(k in low for k in keys):
            return msg
    flat = " ".join(text.split())
    return f"تعذّر الاتصال: {flat[:80]}"
