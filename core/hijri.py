"""تحويل التاريخ الميلادي إلى هجري (تقويم أم القرى التقريبي) وتنسيقه بالعربية.

مكتفٍ ذاتياً — لا تبعية خارجية (آمن في الحزمة المجمّدة). يُستخدم الخوارزمية
الجدولية القياسية للتحويل، وهي دقيقة بما يكفي للعرض.
"""
import datetime

_AR_MONTHS = [
    "محرّم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
    "رجب", "شعبان", "رمضان", "شوّال", "ذو القعدة", "ذو الحجة",
]
_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _ar(n) -> str:
    """أرقام عربية-هندية."""
    return str(n).translate(_AR_DIGITS)


def gregorian_to_hijri(y: int, m: int, d: int) -> tuple:
    """(سنة, شهر, يوم) هجري من تاريخ ميلادي — خوارزمية جدولية قياسية."""
    if m < 3:
        y -= 1
        m += 12
    a  = y // 100
    b  = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524
    l  = jd - 1948440 + 10632
    n  = (l - 1) // 10631
    l  = l - 10631 * n + 354
    j  = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
    l  = l - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
    im = (24 * l) // 709
    id_ = l - (709 * im) // 24
    iy = 30 * n + j - 30
    return iy, im, id_


def hijri_label(date: datetime.date = None) -> str:
    """«٥ صفر ١٤٤٨ هـ» للتاريخ المُعطى (أو اليوم)."""
    date = date or datetime.date.today()
    iy, im, idd = gregorian_to_hijri(date.year, date.month, date.day)
    month = _AR_MONTHS[max(0, min(11, im - 1))]
    return f"{_ar(idd)} {month} {_ar(iy)} هـ"


def dual_label(date: datetime.date = None) -> str:
    """«٥ صفر ١٤٤٨ هـ، 2026-07-21» — هجري + ميلادي.

    Separator is the Arabic comma (U+060C) rather than «·»: Qt falls back to a
    different bundled font per glyph for punctuation the active family lacks,
    and «·» is one of them. U+060C is present in every bundled Arabic family,
    so the permanently-visible sidebar date no longer mixes typefaces."""
    date = date or datetime.date.today()
    return f"{hijri_label(date)}، {date.isoformat()}"
