# مرصد (marsad) — Google Stitch Design Brief

> **How to use this document:** Paste **Block 0 (Master Identity)** into Stitch first to
> anchor the style, then generate each screen by pasting its block (S1–S6) **with the short
> style anchor included at the top of each block**. Keep all screens in one Stitch project
> so the theme stays consistent. §3 at the end is a checklist for verifying Stitch's output.
>
> Product: **مرصد (marsad)** — "observatory" — an Arabic (RTL) executive status-briefing
> tool for LTT's 4G/5G telecom rollout. Field reports flow in; a fleet of 11 AI agents
> turns them into an executive brief. The UI must feel like a **printed briefing on white
> paper**, not a SaaS dashboard.

---

## Block 0 — MASTER IDENTITY PROMPT (paste first)

```
Design the UI for "مرصد" (marsad), a professional Arabic-language (full RTL) desktop-class
web application: an executive status-briefing tool for LTT's 4G/5G network rollout. It
ingests field reports and turns them into a calm executive brief using AI agents. The
aesthetic is "Light Executive Report": a printed briefing on white paper — calm authority,
not a SaaS dashboard, not a startup landing page.

CANVAS & LAYOUT LAW
- Full RTL: <html dir="rtl" lang="ar">. Everything mirrors: the sidebar sits on the RIGHT,
  text aligns right, lists and flows run right-to-left.
- Desktop app window 1440×900. Right-hand sidebar (256px, white, separated from content by
  a 1px hairline #E4E8EC on its inner edge). Content is a centered reading column
  (max-width 840px) with generous margins.
- Structure comes from 1px hairline rules (#E4E8EC) and whitespace — NEVER from card boxes.
  No boxed panels, no walled sections, no metric tiles with borders. Sections are separated
  by hairlines and a small bold Arabic section label.
- Airy executive density: 30px gaps between sections, 12–14px between rows. Lots of white.

COLOR (exact hex — one accent only)
- Paper/surface: #FFFFFF. Subtle zebra fill: #F4F6F8. Hairlines: #E4E8EC (light),
  #CFD6DD (stronger, input borders).
- Ink (text): near-black #141A22 (primary), #5A6675 (secondary/labels), #8A94A1 (captions).
- Single accent: deep telecom teal-green #0E6E60 (hover #0B564B; soft wash #EEF6F4 for the
  active nav pill; tint #E6F1EF). Used sparingly: active nav, primary buttons, section
  ticks, ordered-item numerals.
- Status colors appear ONLY as small 7–8px dots or single words, never as tinted walls:
  good/safe #1E7A52, warning/medium #946200 (dark ochre), critical/late #B4232A, info #1F5F8B.
- No pure black anywhere. No gradients, no glows, no colored shadows.

TYPOGRAPHY (Arabic-first)
- Display/headings: "Noto Kufi Arabic", bold. Body: "Noto Sans Arabic".
  Numbers/dates/paths/emails/ports: "JetBrains Mono", always rendered LTR inside the RTL flow.
- Scale (px): page title 26 bold Kufi · section label 17 bold Kufi · sub-heading 20 ·
  body 14 · dense labels 13 · captions/meta 11.
- Use Arabic-Indic numerals (١ ٢ ٣ ٤ ٥) for ordered/stepped items.
- Arabic text is never truncated mid-word; wrap, right-aligned, line-height 1.5 for paragraphs.

ICONOGRAPHY
- No emojis, ever. No stock icon-font glyphs. Markers are minimal drawn geometric shapes
  (thin 1.5px strokes or tiny filled squares/diamonds/bars) in ink or accent.
- Status is a dot. Nav items have tiny abstract geometric marks (bars, diamond, grid,
  square, dial, trigram), monochrome ink, accent when active.

MOTION (subtle, professional)
- 140–300ms transitions, ease-out curves (cubic-bezier(0.16,1,0.3,1)); transform/opacity only.
- Nav active marker slides/grows 140ms; page switches crossfade 180ms; progress bars fill
  200ms; toasts slide up and fade; buttons compress slightly on press (scale 0.98).
- A "running" status dot breathes gently (opacity pulse, 1.6s). Nothing else loops.

HARD RULES (avoid)
- No emojis. No purple/blue "AI" gradients. No glassmorphism. No dark mode. No card grids.
- No centered hero text. No stock photos. No Inter or Latin-only typography. No fake round
  stats (use realistic operational numbers). No generic placeholder names.
- Component states are always designed: default / hover / pressed / disabled / loading
  (skeleton shapes, not spinners) / empty (composed, with guidance) / error (inline, Arabic).

BRAND
- Wordmark "مرصد" (34px bold Kufi, near-black) with a small square logo mark; subtitle
  "ذكاء المشاريع — LTT 4G/5G" in 11px caption gray. Footer tag "منظومة LTT-PMO".
```

---

## Block 1 — APP SHELL (generate as the frame for every screen)

```
[Style anchor: same Light Executive Report identity — white paper, teal accent #0E6E60,
hairlines, RTL, Noto Kufi/Sans Arabic, JetBrains Mono for numbers, no cards, no emoji.]

Design the persistent application shell (1440×900, RTL):

RIGHT SIDEBAR (256px, white, 1px left hairline #E4E8EC):
- Brand block (top, 26px spacing): wordmark "مرصد" (34px bold Kufi, #141A22) beside a
  40px square logo mark; under it "ذكاء المشاريع — LTT 4G/5G" (11px, #8A94A1).
  Then a hairline.
- Navigation, 6 items, each a 46px row with 10px rounded pill:
    إدخال البيانات · التحليل والوكلاء · لوحة التحكم · التقارير · الإعدادات · جهات الاتصال
  Each row: small geometric mark on the trailing edge, label right-aligned (14px,
  #5A6675). ACTIVE state ("لوحة التحكم"): soft teal pill #EEF6F4, bold label in #0E6E60,
  and a 3px-wide rounded accent bar (22px tall) on the leading (right) edge of the row.
- Footer (bottom, above a hairline): a 7px status dot (green #1E7A52) + "Ollama — متصل"
  (11px, #5A6675); below it the dual date "٧ صفر ١٤٤٨ هـ · 2026-07-23" (11px, #8A94A1,
  the Gregorian part in JetBrains Mono, LTR); below that "منظومة LTT-PMO" (11px, #8A94A1).

CONTENT AREA: white, the active page's centered 840px column (see screen blocks).

GLOBAL ELEMENTS:
- Toast: bottom-center dark pill (#141A22, white 13px text, 10px radius), e.g.
  "حُفظت الإعدادات" — floats 78px above the bottom edge.
- Modal pattern (WhatsApp linking dialog): 30% ink scrim; centered 360px white card
  (12px radius, 1px border #CFD6DD, 24px padding): centered title "ربط واتساب" (17px bold
  Kufi), hairline, then a state — linked: green dot + "تم ربط بنجاح" (green, bold, 20px) +
  phone "+218 91 234 5678" in Mono; waiting: "بانتظار رمز الربط من الجسر…" (13px, #8A94A1,
  centered); QR state: a white square box (1px border, 8px radius, 16px padding) containing
  a crisp black-and-white QR matrix. Footer hint: "واتساب ← الأجهزة المرتبطة ← ربط جهاز ←
  امسح الرمز" (11px, #8A94A1, centered) and a ghost button "إغلاق".
```

---

## Block 2 — S1 · لوحة التحكم (Dashboard — landing screen)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "لوحة التحكم" inside the shell's 840px column. Design BOTH states:

STATE A — EMPTY (first run), vertically centered, max 560px:
- "مرحباً بك في مرصد" (26px bold Kufi, centered) and under it
  "لا يوجد تقرير حالة بعد — ابدأ بثلاث خطوات:" (13px, #5A6675, centered).
- Three steps, hairline-separated rows (74px each). Each: a 34px circle in #EEF6F4 holding
  an Arabic-Indic numeral (١، ٢، ٣) in bold teal; bold title (14px) + one-line description
  (11px, #8A94A1); a button on the trailing edge:
  ١ "اضبط محرّك الذكاء الاصطناعي" / "اختر المزوّد وأدخِل المفاتيح" [primary button "الإعدادات"]
  ٢ "أضِف تقارير ميدانية" / "يدوياً أو ارفع ملفات أو اجمع من المصادر" [ghost "إدخال البيانات"]
  ٣ "شغّل التحليل الذكي" / "الوكلاء يحلّلون ويولّدون ملخّص الحالة" [ghost "التحليل"]

STATE B — POPULATED EXECUTIVE BRIEF (the core screen):
- Header row: "تقرير حالة المشروع" (26px bold Kufi); trailing edge: date "2026-07-23 14:05"
  (11px Mono, LTR, #8A94A1) and a small ghost button "مسح اللوحة".
- Health line: "الحالة العامة" (14px, #5A6675) + an 8px dot (#946200) + the word "متوسط"
  (17px bold Kufi, #946200). Below: a full-width 2px rule in #0E6E60.
- Section "المؤشرات الرئيسية": a 2-column grid (48px column gap, 13px row gap) of metric
  rows — each row: label (14px, #5A6675), value (17px bold Kufi, #141A22), status dot.
  Data: التقدّم العام 80% (جيد، أخضر) · إنفاق الميزانية 60% (متوسط، كهرماني) ·
  درجة السلامة 87% (جيد) · جاهزية المخزون 72% (متوسط) · المحطات المفحوصة 8/10 (جيد) ·
  انحراف الجدول 18 يوم (متوسط).
- Section "الملخص التنفيذي": one justified-right paragraph (14px, line-height 1.5):
  "التقدم العام في حدود 60–80% مع تعثّر توريد وحدات Massive MIMO في جمارك مصراتة؛
  المرحلة الثانية متأخرة 18 يوماً والتوقع الجديد سبتمبر 2026. فرق سرت جاهزة للتركيب فور
  وصول المعدات، ولا حوادث سلامة مؤثرة هذا الشهر."
- Section "خطة العمل الفورية": numbered action rows (hairline between, 13px vertical
  rhythm). Each: Arabic-Indic numeral in bold teal (17px), action text (14px bold-ish ink),
  meta line (13px, #5A6675) "owner · deadline · impact":
  ١ تسريع الإفراج الجمركي عن شحنة Massive MIMO في ميناء مصراتة — المشتريات · 2026-06-01 · يحرّر المسار الحرج لتركيب سرت
  ٢ معالجة ضعف ترددات الباك هول بين سرت والجفرة — فريق النواة · 3 أيام · يمنع تدهور جودة URLLC
  ٣ استكمال تصاريح البلدية لأربع قواعد معلّقة في سرت — الإدارة الإنشائية · أسبوعان · يعيد التقدم المدني إلى المسار
```

---

## Block 3 — S2 · إدخال البيانات (Data Input)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "إدخال البيانات". Page header: title (26px bold Kufi) + subtitle (13px, #8A94A1):
"أضف تقارير ميدانية أو حمّل النماذج، ثم انتقل إلى «التحليل والوكلاء»".

ACTION ROW (top): three ghost buttons "تحميل نماذج تجريبية" · "رفع ملفات" · "جمع من المصادر"
on the right; a quiet ghost "مسح الكل" on the far trailing edge.

Section "التقارير الجاهزة للتحليل" with caption "٨ تقارير في القائمة" (11px, #8A94A1).
QUEUE LIST — hairline-separated rows (no boxes), each row 3 zones:
- Trailing 120px: source in bold 13px (بريد إلكتروني / واتساب / ERP / يدوي) over the
  department in 11px gray (شبكة الراديو RAN).
- Middle (flex): "من: م. أحمد الورفلي — فريق RAN · 2026-05-15" (11px, #5A6675), then a
  2-line clamped excerpt (14px, ink):
  "اكتملت عملية تركيب 14 برجاً من أصل 23 في منطقة سرت. تأخر في توريد وحدات Massive MIMO
  بسبب مشكلة جمركية في ميناء مصراتة…"
- Leading edge: small ghost "حذف".
Second example row: source "ERP", dept "التكاليف", from "إدارة المالية — نظام ERP ·
2026-05-17", excerpt "إجمالي المصروف 4.2 مليون دينار من أصل 7 مليون (60%)…"
EMPTY STATE (when count is 0): centered composed block — "لا توجد تقارير بعد" (14px,
#5A6675) over "حمّل النماذج أو أضف تقريراً من النموذج بالأسفل" (11px, #8A94A1).

Section "إضافة تقرير يدوي" — form (labels always above inputs, 8px gaps):
- Row of two dropdowns: "المصدر" (يدوي / بريد إلكتروني / واتساب / ERP) and "الإدارة"
  (شبكة الراديو RAN / شبكة النواة Core / العمليات / الجودة / السلامة / الأعمال الإنشائية /
  التكاليف / العقود / المشتريات / المخازن والتوريد).
- Field "المُرسِل" placeholder "اسم المرسل أو الجهة".
- Textarea "نص التقرير" (120px tall) placeholder "الصق أو اكتب محتوى التقرير الميداني هنا…".
- Trailing-aligned primary button "إضافة إلى القائمة".
INPUT CHROME: 38px height, 8px radius, 1px border #CFD6DD, white bg, 12px padding; focus =
2px border #0E6E60; placeholder #8A94A1. Dropdowns identical chrome with a thin chevron.
```

---

## Block 4 — S3 · التحليل والوكلاء (Analysis & Agents — the live screen)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "التحليل والوكلاء" — subtitle "تشغيل أسطول الوكلاء على التقارير المُجمَّعة وإنتاج تقرير الحالة".

RUN CONTROL ROW: primary teal button "بدء التحليل" (busy state: disabled, text
"جارٍ التحليل…"); then a full-width progress track (6px, fully rounded, #F4F6F8 bg) with a
teal fill at 64%; then "64%" in 13px JetBrains Mono (LTR).

Section "حالة الوكلاء": eleven hairline-separated rows (46px), each: agent name (14px ink)
on the right; on the trailing edge a state word (13px) with a 7px dot when active:
  العمليات الميدانية — تم (green #1E7A52)
  الجودة والامتثال — تم
  السلامة المهنية — تم
  الأعمال الإنشائية — قيد التشغيل (amber #946200, bold; dot gently pulsing)
  التكاليف والميزانية — بالانتظار (#8A94A1, no dot)
  العقود والشؤون القانونية — بالانتظار
  المشتريات والموردين — بالانتظار
  المخازن وسلاسل التوريد — بالانتظار
  إدارة المخاطر — بالانتظار
  الجدول الزمني — بالانتظار
  التنسيق المركزي — بالانتظار
Also design one "خطأ" example state (red #B4232A) as a variant note.

Section "سجل التشغيل": a 160px-tall log panel — the ONLY filled area on the page
(#F4F6F8 bg, 8px radius, 1px border #E4E8EC, 10px padding), small 13px #5A6675 lines,
right-aligned, latest at bottom, one line per agent start/finish:
  ops…
  ops — اكتمل
  quality…
  quality — اكتمل
  safety…
  civil…
Empty state inside the panel: "لم يبدأ التشغيل بعد." (#8A94A1).
```

---

## Block 5 — S4 · التقارير (Reports & Export)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "التقارير" — subtitle "عاين التقرير الحالي، صدّره بصيغة PDF أو Excel، أرسله بالبريد، أو ارجع لملفات سابقة".

EMPTY STATE variant: "لا يوجد تقرير للتصدير" + hint "شغّل التحليل من «التحليل والوكلاء»
أولاً" + primary button "الانتقال إلى «التحليل والوكلاء»".

Section "التقرير الحالي": meta line — "الحالة العامة" + amber dot + "متوسط" (bold Kufi,
amber) + quiet caption "6 مؤشرات أداء · 3 إجراءات عاجلة" (11px, #8A94A1); trailing edge
date in Mono. Under it a 3-line clamped excerpt of the executive summary (13px, #5A6675).
Actions: primary "تصدير PDF", ghost "تصدير Excel". Under them an inline result line
(success): "حُفظ الملف: marsad_20260723_140522.pdf" (13px, #5A6675; filename in Mono) —
and an error variant in #B4232A.

Section "التقارير السابقة": hairline rows, all Mono (LTR): filename
"marsad_20260721_224502.xlsx" · "8 KB" (#8A94A1) · "2026-07-21 22:45" (#8A94A1);
second row "marsad_20260721_224501.pdf" · "4 KB" · "2026-07-21 22:45".
Empty text variant: "لا توجد ملفات مُصدَّرة بعد — أول تصدير يظهر هنا."

Section "الإرسال بالبريد": line "سيُرسَل إلى:" (13px, #5A6675) + recipients in Mono (LTR):
"pmo@ltt.example.ly، director@ltt.example.ly". Ghost button "إرسال تقرير بالبريد".
WARNING variant (no recipients configured): amber dot + "لا يوجد مستلمون مضبوطون —
اضبط «مستلمو التقرير» في الإعدادات أولاً" + ghost "فتح الإعدادات".
```

---

## Block 6 — S5 · الإعدادات (Settings — the densest screen)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "الإعدادات" — subtitle "اضبط محرّك الذكاء الاصطناعي ومصادر البيانات ثم احفظ — زرّا
الاختبار يحفظان تلقائياً قبل الفحص". Sections separated by hairlines; each section label
(17px bold Kufi) may carry a small trailing status note (11px).

SECTION "محرّك الذكاء الاصطناعي" (note: "المفتاح مضبوط", or amber "المفتاح غير مضبوط";
"محلي — بلا مفتاح" for Ollama):
- Row: dropdown "ملف المحرّك" showing "الافتراضي (Ollama)" + ghost "حذف الملف".
- Row: field "احفظ الإعداد الحالي كملف" (placeholder "مثال: Gemini العمل") + ghost "حفظ كملف".
- Dropdown "المزوّد": Ollama — محلي / Claude API / OpenAI / متوافق / Google Gemini / Azure OpenAI.
- Field "مهلة الاستجابة (ثانية)" value 180 (Mono, narrow).
- Provider field group (show the OpenAI/متوافق variant as the designed state):
  dropdown "الخدمة" (OpenAI / OpenRouter / Groq / Together / DeepSeek / LM Studio (محلي) /
  مخصّص), field "عنوان الخدمة (Base URL)" (Mono, LTR), password field "مفتاح API" (masked
  bullets, Mono, with a drawn eye visibility toggle inside the input's trailing edge),
  field "اسم النموذج" value "gpt-4o-mini".
- Row: ghost "جلب قائمة النماذج" + a dropdown of fetched models.
- Row: ghost "اختبار المحرّك" + inline result: amber dot + "جارٍ الفحص…" — variants:
  green dot "الاتصال ناجح" / red dot "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح".

SECTION "البريد الإلكتروني" (note: amber "ينقصه: كلمة المرور"): fields "البريد",
"كلمة المرور / App Password" (password), row of "خادم IMAP" + "خادم SMTP" + narrow
"منفذ SMTP" (587), field "مستلمو التقرير (افصل بينهم بفاصلة)". Row: ghost "اختبار البريد"
+ inline dot+message (same pattern as engine test).

SECTION "مجلد ERP" (note "غير مضبوط"): caption "أي ملف (Excel / PDF / CSV / Word…) يوضع
في هذا المجلد يُقرأ عند «جمع من المصادر»." Row: field "المسار" (Mono, LTR) + ghost "استعراض".

SECTION "واتساب" (note "معطّل"): checkbox "تفعيل استقبال واتساب" + narrow field
"منفذ المستقبِل" (5051, Mono). Then four numbered setup steps (Mono numerals 1–4 in
#8A94A1, 13px descriptions, buttons on the trailing edge):
  1 تحقق من Node.js على هذا الجهاز [ghost "فحص Node.js" + green dot + caption "مثبّت: v24.18.0"]
  2 إن لم يكن مثبّتاً، ثبّته من الموقع الرسمي [ghost "تثبيت Node.js"]
  3 ولّد ملف الجسر في مجلد البيانات [ghost "توليد ملف الجسر"]
  4 اعرض رمز الربط داخل التطبيق وامسحه بواتساب — يصلك تأكيد فور الربط [primary "عرض رمز الربط"]
  Below step 4, Mono hint (LTR): "أو يدوياً من مجلد البيانات: npm install && node whatsapp_bridge.js"

STICKY SAVE BAR (bottom of the page, hairline above it): primary "حفظ الإعدادات" + amber
dot + "تغييرات غير محفوظة" (13px, #5A6675) — saved variant: green dot + "كل الإعدادات محفوظة".
```

---

## Block 7 — S6 · جهات الاتصال (Contacts)

```
[Style anchor: same identity — white paper, teal #0E6E60, hairlines, RTL, no cards.]

Screen "جهات الاتصال" — subtitle "الهيكل التنظيمي والموظفون — يزامَن مع خرائط التوجيه في الإعدادات".

SECTION "الهيكل التنظيمي": two dropdowns side by side — "الإدارة"
(الإدارة الفنية / التشغيلية · الإدارة المالية · الإدارة الإدارية) and "القسم"
(فريق شبكة الراديو RAN · فريق شبكة النواة Core · إدارة العمليات · إدارة الجودة ·
إدارة السلامة · الإدارة الإنشائية). Under them: ghost "مزامنة مع الإعدادات" + caption
"ينسخ توجيه البريد وواتساب ← الأقسام إلى الإعدادات" (11px, #8A94A1).

SECTION "الموظفون": hairline rows — name in bold 14px ("م. أحمد الورفلي") over position in
11px gray ("مهندس راديو أول — فريق RAN"); middle: email "a.werfalli@ltt.example.ly" and
phone "+218 91 234 5678" in 13px Mono (LTR, left-aligned); trailing: small danger-ghost
"حذف" (red #B4232A text). Second row: "م. فاطمة الدغيلي" / "مديرة الجودة" /
"f.dghaily@ltt.example.ly" / "+218 92 881 4402".
EMPTY variant: "لا يوجد موظفون في هذا القسم" + "أضف موظفاً من النموذج بالأسفل".

SECTION "إضافة موظف": two field rows — "الاسم" (placeholder "الاسم الكامل") + "المنصب"
(placeholder "المسمّى الوظيفي"); "البريد الإلكتروني" (placeholder "name@example.com",
Mono) + "واتساب" (placeholder "+2189XXXXXXX", Mono). Trailing primary "إضافة الموظف".
```

---

## §3 — Output verification checklist (apply to Stitch results before exporting)

1. **RTL everywhere**: sidebar on the right, Arabic right-aligned, Mono runs (numbers,
   paths, emails) stayed LTR inside the RTL flow. Nothing mirrored incorrectly (chevrons,
   progress fill starts from the RIGHT).
2. **No cards**: sections separated by hairlines only. If Stitch boxed anything, remove it.
3. **One accent**: only #0E6E60 + the three status colors as dots/words. Kill any purple,
   blue, or gradient that crept in.
4. **No emoji**: replace any emoji/symbol glyph with a drawn geometric mark or remove it.
5. **Fonts**: Kufi for headings, Sans for body, Mono for numbers — not a single Latin
   UI font. Sizes follow the 26/17/14/13/11 scale.
6. **Arabic strings verbatim**: compare against the blocks — Stitch sometimes "improves"
   wording; restore the exact strings (they are product copy, not suggestions).
7. **States present**: empty, loading (skeleton), error, disabled — per block.
8. **Density**: generous whitespace, 840px column, 30px section gaps. If it looks cramped
   or cockpit-like, re-prompt with "airier, printed-briefing spacing".

## Notes for the implementation phase (post-Stitch)

- Export per screen to Figma for review, then to code (the app's web frontend will be built
  separately; treat Stitch output as the visual source of truth, this brief as the contract).
- The dashboard's data shapes (KPIs, actions, agent states) are fixed by the backend —
  see `docs/PROJECT_DEFINITION.md` §6 — don't let the visuals invent fields that don't exist.
- Motion stays CSS-only (transform/opacity, ≤300ms); no animation libraries are needed to
  implement this design.
