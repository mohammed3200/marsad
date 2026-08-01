"""خريطة موحّدة لرسائل الأخطاء الظاهرة للمستخدم — UI-agnostic, no Qt.

friendly_error() يحوّل نصوص الأخطاء الخام (أكواد HTTP، استثناءات Python، ردود
المزوّدين) إلى رسالة عربية قصيرة قابلة للفهم والتصرّف. تستخدمه core/engine.py
و connectors.py — النصوص العربية الجاهزة تمرّ كما هي، والنص الخام لا يصل
الواجهة أبداً (يُسجَّل في logs/ عند الحاجة).

friendly_error() مبنية لأخطاء مزوّدي الذكاء الاصطناعي (HTTP/JSON عبر الشبكة) —
تطبيق قواعدها (401→"مفتاح API"، 404→"اسم النموذج"…) على OSError محلي (قرص
ممتلئ، صلاحيات، منفذ مستخدَم) يعطي تشخيصاً مضللاً تماماً لأنها تبحث عن أنماط
نصية فرعية بلا أي وعي بالسياق. friendly_fs_error() أدناه مخصّصة لذلك — تُستخدم
لأي OSError (أو استثناء آخر) من نظام الملفات أو ربط منفذ، وليس من طلب شبكي.
"""

import errno


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


_FS_RULES = {
    errno.EACCES:    "تعذّر الوصول — تحقق من صلاحيات المجلد/الملف",
    errno.EPERM:     "تعذّر الوصول — تحقق من صلاحيات المجلد/الملف",
    errno.ENOSPC:    "لا مساحة تخزين كافية على القرص",
    errno.EROFS:     "المجلد للقراءة فقط — تحقق من صلاحيات القرص",
    errno.ENOENT:    "المسار غير موجود — تحقق من مجلد الحفظ",
    errno.EADDRINUSE: "المنفذ مستخدَم بالفعل — غيّر المنفذ في الإعدادات",
}


def friendly_fs_error(exc) -> str:
    """رسالة عربية لأخطاء نظام الملفات المحلي أو ربط منفذ (OSError وما شابهها) —
    استخدمها بدلاً من friendly_error() لأي خطأ ليس رد مزوّد عبر الشبكة، حتى لا
    يُترجَم EACCES/ENOSPC خطأً كـ"مفتاح API غير صالح" أو "اسم النموذج والرابط".
    """
    code = getattr(exc, "errno", None)
    if code in _FS_RULES:
        return _FS_RULES[code]
    text = str(exc).strip()
    if _has_arabic(text):
        return text
    flat = " ".join(text.split())
    return f"خطأ في النظام: {flat[:80]}" if flat else "خطأ غير معروف"
