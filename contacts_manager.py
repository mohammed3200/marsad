"""
contacts_manager.py — إدارة جهات الاتصال
نظام LTT PM Intelligence Desktop
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
from pathlib import Path

BG_DARK  = "#0D1B2A"; BG_MID  = "#1E3A5F"; BG_CARD  = "#162032"
BG_INPUT = "#0f1e2e"; ACCENT  = "#2563EB"; ACCENT2  = "#38BDF8"
SUCCESS  = "#10B981"; WARNING = "#F59E0B"; DANGER   = "#EF4444"
TEXT_PRI = "#E2E8F0"; TEXT_SEC= "#94A3B8"; TEXT_DIM = "#475569"
WHITE    = "#FFFFFF"

FONT_HEAD  = ("Arial", 13, "bold")
FONT_BODY  = ("Arial", 11)
FONT_SMALL = ("Arial", 9)

CONTACTS_FILE = Path(__file__).parent / "data" / "contacts.json"

DEFAULT_STRUCTURE = {
    "الإدارة الفنية / التشغيلية": {
        "color": "#38bdf8",
        "subs": {
            "فريق شبكة الراديو RAN": [],
            "فريق شبكة النواة Core": [],
            "إدارة العمليات": [],
            "إدارة الجودة": [],
            "إدارة السلامة": [],
            "الإدارة الإنشائية": [],
        }
    },
    "الإدارة المالية": {
        "color": "#34d399",
        "subs": {
            "إدارة التكاليف": [],
            "إدارة العقود": [],
            "إدارة المشتريات": [],
            "المخازن وسلاسل التوريد والنقل": [],
        }
    },
    "الإدارة الإدارية": {
        "color": "#a78bfa",
        "subs": {
            "الموارد البشرية": [],
            "مكتب إدارة المشاريع PMO": [],
            "إدارة المخاطر": [],
            "تقنية المعلومات": [],
        }
    },
}

DEPT_KEY_MAP = {
    "فريق شبكة الراديو RAN"         : "ran",
    "فريق شبكة النواة Core"          : "core",
    "إدارة العمليات"                 : "ops",
    "إدارة الجودة"                   : "quality",
    "إدارة السلامة"                  : "safety",
    "الإدارة الإنشائية"              : "civil",
    "إدارة التكاليف"                 : "cost",
    "إدارة العقود"                   : "contract",
    "إدارة المشتريات"                : "procure",
    "المخازن وسلاسل التوريد والنقل"  : "supply",
    "الموارد البشرية"                : "hr",
    "مكتب إدارة المشاريع PMO"        : "pmo",
    "إدارة المخاطر"                  : "risk",
    "تقنية المعلومات"                : "it",
}


# ════════════════════════════════════════════════════
# قاعدة البيانات
# ════════════════════════════════════════════════════
class ContactsDB:
    def __init__(self):
        CONTACTS_FILE.parent.mkdir(exist_ok=True)
        self.data = self._load()

    def _load(self):
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        data = {"structure": DEFAULT_STRUCTURE, "employees": []}
        self._save_data(data)
        return data

    def _save_data(self, data=None):
        if data is None:
            data = self.data
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self):
        self._save_data()

    def get_employees(self, dept=None, sub_dept=None, active_only=False):
        emps = self.data.get("employees", [])
        if dept:
            emps = [e for e in emps if e.get("dept") == dept]
        if sub_dept:
            emps = [e for e in emps if e.get("sub_dept") == sub_dept]
        if active_only:
            emps = [e for e in emps if e.get("active", True)]
        return emps

    def add_employee(self, emp):
        emp["id"] = self._next_id()
        self.data["employees"].append(emp)
        self.save()
        return emp["id"]

    def update_employee(self, emp_id, fields):
        for e in self.data["employees"]:
            if e.get("id") == emp_id:
                e.update(fields)
                break
        self.save()

    def delete_employee(self, emp_id):
        self.data["employees"] = [
            e for e in self.data["employees"] if e.get("id") != emp_id
        ]
        self.save()

    def find_by_email(self, email):
        for e in self.data["employees"]:
            if e.get("email", "").lower() == email.lower():
                return e
        return None

    def find_by_whatsapp(self, number):
        clean = number.replace("+","").replace(" ","").replace("-","")
        for e in self.data["employees"]:
            wa = e.get("whatsapp","").replace("+","").replace(" ","").replace("-","")
            if wa == clean:
                return e
        return None

    def _next_id(self):
        ids = [e.get("id", 0) for e in self.data["employees"]]
        return max(ids, default=0) + 1

    def get_structure(self):
        return self.data.get("structure", DEFAULT_STRUCTURE)

    def get_depts(self):
        return list(self.get_structure().keys())

    def get_sub_depts(self, dept):
        return list(self.get_structure().get(dept, {}).get("subs", {}).keys())

    def add_dept(self, name):
        if name not in self.data["structure"]:
            self.data["structure"][name] = {"color": "#64748b", "subs": {}}
            self.save()

    def add_sub_dept(self, dept, name):
        if dept in self.data["structure"]:
            self.data["structure"][dept]["subs"][name] = []
            self.save()

    def delete_dept(self, name):
        self.data["structure"].pop(name, None)
        self.data["employees"] = [
            e for e in self.data["employees"] if e.get("dept") != name
        ]
        self.save()

    def delete_sub_dept(self, dept, sub):
        if dept in self.data["structure"]:
            self.data["structure"][dept]["subs"].pop(sub, None)
        self.data["employees"] = [
            e for e in self.data["employees"]
            if not (e.get("dept") == dept and e.get("sub_dept") == sub)
        ]
        self.save()

    def _dept_to_key(self, dept_name):
        return DEPT_KEY_MAP.get(dept_name, "admin")

    def export_to_config(self):
        email_map = {}
        wa_map    = {}
        for e in self.data["employees"]:
            if not e.get("active", True):
                continue
            sub = e.get("sub_dept", e.get("dept", "admin"))
            key = self._dept_to_key(sub)
            if e.get("email"):
                email_map[e["email"].lower()] = key
            if e.get("whatsapp"):
                wa_map[e["whatsapp"]] = key
        return {"email_dept_map": email_map, "whatsapp_groups": wa_map}


# ════════════════════════════════════════════════════
# نافذة إضافة / تعديل موظف
# ════════════════════════════════════════════════════
class EmployeeDialog(tk.Toplevel):
    def __init__(self, parent, db, emp=None):
        super().__init__(parent)
        self.db     = db
        self.emp    = emp
        self.result = None
        self.title("إضافة موظف" if emp is None else "تعديل بيانات الموظف")
        self.configure(bg=BG_DARK)
        self.geometry("520x580")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if emp:
            self._fill(emp)

    def _build(self):
        tk.Label(self,
                 text="👤 " + ("موظف جديد" if self.emp is None else "تعديل الموظف"),
                 bg=BG_DARK, fg=ACCENT2, font=FONT_HEAD).pack(pady=(16,12))

        form = tk.Frame(self, bg=BG_DARK)
        form.pack(fill="both", expand=True, padx=24)

        self._vars = {}
        fields = [
            ("name",     "الاسم الكامل *",               "محمد الورفلي"),
            ("title",    "المسمى الوظيفي",                "مهندس شبكات"),
            ("email",    "البريد الإلكتروني",             "name@example.com"),
            ("whatsapp", "رقم الواتساب (مع كود الدولة)", "+218900000000"),
            ("notes",    "ملاحظات",                       ""),
        ]
        for key, label, placeholder in fields:
            tk.Label(form, text=label, bg=BG_DARK, fg=TEXT_SEC,
                     font=FONT_SMALL, anchor="w").pack(fill="x", pady=(6,2))
            var = tk.StringVar()
            self._vars[key] = var
            ent = tk.Entry(form, textvariable=var, bg=BG_INPUT, fg=TEXT_PRI,
                           font=FONT_BODY, bd=1, relief="solid",
                           insertbackground=TEXT_PRI)
            ent.pack(fill="x", ipady=5)
            # placeholder simulation
            if not self.emp and placeholder:
                ent.insert(0, placeholder)
                ent.config(fg=TEXT_DIM)
                def _in(ev, e=ent, ph=placeholder):
                    if e.get() == ph:
                        e.delete(0, "end"); e.config(fg=TEXT_PRI)
                def _out(ev, e=ent, ph=placeholder):
                    if not e.get():
                        e.insert(0, ph); e.config(fg=TEXT_DIM)
                ent.bind("<FocusIn>",  _in)
                ent.bind("<FocusOut>", _out)

        # الإدارة الرئيسية
        tk.Label(form, text="الإدارة الرئيسية *", bg=BG_DARK, fg=TEXT_SEC,
                 font=FONT_SMALL, anchor="w").pack(fill="x", pady=(6,2))
        self._dept_var = tk.StringVar()
        self._dept_cb  = ttk.Combobox(form, textvariable=self._dept_var,
                                       values=self.db.get_depts(),
                                       state="readonly", font=FONT_BODY)
        self._dept_cb.pack(fill="x", ipady=4)
        self._dept_cb.bind("<<ComboboxSelected>>", self._on_dept_change)

        # القسم الفرعي
        tk.Label(form, text="القسم / الوحدة *", bg=BG_DARK, fg=TEXT_SEC,
                 font=FONT_SMALL, anchor="w").pack(fill="x", pady=(6,2))
        self._sub_var = tk.StringVar()
        self._sub_cb  = ttk.Combobox(form, textvariable=self._sub_var,
                                      state="readonly", font=FONT_BODY)
        self._sub_cb.pack(fill="x", ipady=4)

        # نشط
        self._active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form, text="الموظف نشط (يستقبل الإشعارات)",
                       variable=self._active_var,
                       bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_MID,
                       activebackground=BG_DARK, activeforeground=TEXT_PRI,
                       font=FONT_BODY).pack(anchor="w", pady=(10,0))

        # أزرار
        btn_row = tk.Frame(self, bg=BG_DARK)
        btn_row.pack(fill="x", padx=24, pady=(12,16))
        tk.Button(btn_row, text="💾 حفظ",
                  bg=SUCCESS, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=20, pady=8, cursor="hand2",
                  command=self._save).pack(side="right", padx=(8,0))
        tk.Button(btn_row, text="إلغاء",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=20, pady=8, cursor="hand2",
                  command=self.destroy).pack(side="right")

    def _on_dept_change(self, event=None):
        subs = self.db.get_sub_depts(self._dept_var.get())
        self._sub_cb.config(values=subs)
        if subs:
            self._sub_var.set(subs[0])

    def _fill(self, emp):
        for key, var in self._vars.items():
            var.set(emp.get(key, ""))
        self._dept_var.set(emp.get("dept", ""))
        self._on_dept_change()
        self._sub_var.set(emp.get("sub_dept", ""))
        self._active_var.set(emp.get("active", True))

    def _save(self):
        name = self._vars["name"].get().strip()
        if not name or name == "محمد الورفلي":
            messagebox.showwarning("تنبيه", "يرجى إدخال اسم الموظف", parent=self)
            return
        dept = self._dept_var.get()
        if not dept:
            messagebox.showwarning("تنبيه", "يرجى اختيار الإدارة", parent=self)
            return

        phs = {"title":"مهندس شبكات","email":"name@example.com","whatsapp":"+100000000000"}
        def clean(k):
            v = self._vars[k].get().strip()
            return "" if v == phs.get(k,"") else v

        self.result = {
            "name"     : name,
            "title"    : clean("title"),
            "email"    : clean("email"),
            "whatsapp" : clean("whatsapp"),
            "dept"     : dept,
            "sub_dept" : self._sub_var.get(),
            "active"   : self._active_var.get(),
            "notes"    : self._vars["notes"].get().strip(),
        }
        if self.emp:
            self.result["id"] = self.emp["id"]
        self.destroy()


# ════════════════════════════════════════════════════
# تبويب جهات الاتصال
# ════════════════════════════════════════════════════
class ContactsTab(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG_DARK)
        self.db = db
        self._current_filter = {"dept": None, "sub_dept": None}
        self._build()

    def _build(self):
        # ── شريط الأدوات ──
        toolbar = tk.Frame(self, bg=BG_MID, height=48)
        toolbar.pack(fill="x", padx=8, pady=(8,4))
        toolbar.pack_propagate(False)
        tk.Label(toolbar, text="👥 إدارة جهات الاتصال والفرق",
                 bg=BG_MID, fg=ACCENT2, font=FONT_HEAD).pack(side="left", padx=12, pady=10)
        for text, color, cmd in [
            ("📤 تصدير للنظام", WARNING,  self._export_to_system),
            ("📁 إضافة قسم",   BG_CARD,  self._add_sub_dept),
            ("🏢 إضافة إدارة", ACCENT,   self._add_dept),
            ("➕ موظف جديد",   SUCCESS,  self._add_employee),
        ]:
            tk.Button(toolbar, text=text, bg=color, fg=WHITE,
                      font=FONT_SMALL, bd=0, padx=10, pady=4,
                      cursor="hand2", command=cmd).pack(side="right", padx=4, pady=8)

        # ── منطقة المحتوى ──
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # ── شجرة الهيكل ──
        left = tk.Frame(main, bg=BG_DARK, width=260)
        left.pack(side="left", fill="y", padx=(0,6))
        left.pack_propagate(False)
        tk.Label(left, text="🏛️ الهيكل التنظيمي",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_BODY).pack(anchor="w", pady=(0,4))
        tree_f = tk.Frame(left, bg=BG_CARD, bd=1)
        tree_f.pack(fill="both", expand=True)
        sb1 = tk.Scrollbar(tree_f); sb1.pack(side="right", fill="y")
        self._tree = ttk.Treeview(tree_f, yscrollcommand=sb1.set,
                                   show="tree", selectmode="browse")
        self._tree.pack(fill="both", expand=True)
        sb1.config(command=self._tree.yview)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-3>", self._tree_right_click)
        self._refresh_tree()

        # ── جانب الموظفين ──
        right = tk.Frame(main, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)

        # شريط بحث
        sr = tk.Frame(right, bg=BG_DARK)
        sr.pack(fill="x", pady=(0,6))
        tk.Label(sr, text="🔍", bg=BG_DARK, fg=TEXT_SEC,
                 font=("Arial",14)).pack(side="left", padx=(0,4))
        self._search_var = tk.StringVar()
        self._search_var.trace("w", self._on_search)
        ph_text = "بحث باسم أو بريد أو واتساب..."
        se = tk.Entry(sr, textvariable=self._search_var,
                      bg=BG_INPUT, fg=TEXT_DIM, font=FONT_BODY,
                      bd=1, relief="solid", insertbackground=TEXT_PRI)
        se.insert(0, ph_text)
        se.pack(side="left", fill="x", expand=True, ipady=5)
        def ph_in(ev):
            if se.get() == ph_text:
                se.delete(0, "end"); se.config(fg=TEXT_PRI)
        def ph_out(ev):
            if not se.get():
                se.insert(0, ph_text); se.config(fg=TEXT_DIM)
        se.bind("<FocusIn>",  ph_in)
        se.bind("<FocusOut>", ph_out)
        self._count_lbl = tk.Label(sr, text="", bg=BG_DARK,
                                    fg=TEXT_DIM, font=FONT_SMALL)
        self._count_lbl.pack(side="right", padx=8)

        # جدول الموظفين
        tbl_f = tk.Frame(right, bg=BG_CARD)
        tbl_f.pack(fill="both", expand=True)
        cols = ("name","title","email","whatsapp","dept","sub_dept","status")
        self._tbl = ttk.Treeview(tbl_f, columns=cols,
                                  show="headings", selectmode="browse")
        headers = [
            ("name",     "الاسم",              180),
            ("title",    "المسمى الوظيفي",      130),
            ("email",    "البريد الإلكتروني",   200),
            ("whatsapp", "رقم الواتساب",         130),
            ("dept",     "الإدارة",             140),
            ("sub_dept", "القسم / الوحدة",       150),
            ("status",   "الحالة",               60),
        ]
        for col, hdr, w in headers:
            self._tbl.heading(col, text=hdr,
                              command=lambda c=col: self._sort_by(c))
            # anchor must be: n/ne/e/se/s/sw/w/nw/center
            self._tbl.column(col, width=w, minwidth=50, anchor="center")

        sb2 = tk.Scrollbar(tbl_f, command=self._tbl.yview)
        sb2.pack(side="right", fill="y")
        self._tbl.config(yscrollcommand=sb2.set)
        self._tbl.pack(fill="both", expand=True)
        self._tbl.bind("<Double-Button-1>", lambda e: self._edit_employee())
        self._tbl.bind("<Button-3>", self._tbl_right_click)

        # أزرار أسفل الجدول
        br = tk.Frame(right, bg=BG_DARK)
        br.pack(fill="x", pady=(6,0))
        for text, color, cmd in [
            ("✏️ تعديل",      ACCENT,  self._edit_employee),
            ("🗑️ حذف",       DANGER,  self._delete_employee),
            ("📋 نسخ بريد",   BG_MID,  self._copy_email),
            ("📱 نسخ واتساب", BG_MID,  self._copy_whatsapp),
        ]:
            tk.Button(br, text=text, bg=color, fg=WHITE,
                      font=FONT_SMALL, bd=0, padx=10, pady=6,
                      cursor="hand2", command=cmd).pack(side="left", padx=(0,6))

        self._refresh_table()

    # ── شجرة الهيكل ──
    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        total = len(self.db.get_employees())
        self._tree.insert("", "end", iid="__all__",
                          text=f"👥 جميع الموظفين  ({total})",
                          values=["",""])
        for dept, info in self.db.get_structure().items():
            cnt = len(self.db.get_employees(dept=dept))
            did = self._tree.insert("", "end",
                                    text=f"🏛️ {dept}  ({cnt})",
                                    values=[dept,""], open=True)
            for sub in info.get("subs", {}):
                sc = len(self.db.get_employees(dept=dept, sub_dept=sub))
                self._tree.insert(did, "end",
                                  text=f"    📁 {sub}  ({sc})",
                                  values=[dept, sub])

    def _on_tree_select(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], "values")
        dept = vals[0] if vals else ""
        sub  = vals[1] if len(vals) > 1 else ""
        self._current_filter = {
            "dept":     dept or None,
            "sub_dept": sub  or None
        }
        self._refresh_table()

    def _tree_right_click(self, event):
        item = self._tree.identify_row(event.y)
        if not item or item == "__all__":
            return
        vals = self._tree.item(item, "values")
        dept = vals[0] if vals else ""
        sub  = vals[1] if len(vals) > 1 else ""
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT_PRI,
                       activebackground=ACCENT, activeforeground=WHITE)
        if sub:
            menu.add_command(label="➕ إضافة موظف لهذا القسم",
                             command=lambda: self._add_employee(dept, sub))
            menu.add_separator()
            menu.add_command(label="🗑️ حذف القسم",
                             command=lambda: self._delete_sub_dept(dept, sub))
        else:
            menu.add_command(label="📁 إضافة قسم فرعي",
                             command=lambda: self._add_sub_dept(dept))
            menu.add_separator()
            menu.add_command(label="🗑️ حذف الإدارة",
                             command=lambda: self._delete_dept(dept))
        menu.post(event.x_root, event.y_root)

    # ── جدول الموظفين ──
    def _refresh_table(self, search=""):
        self._tbl.delete(*self._tbl.get_children())
        dept   = self._current_filter.get("dept")
        sub    = self._current_filter.get("sub_dept")
        emps   = self.db.get_employees(dept=dept, sub_dept=sub)
        q      = (search or self._search_var.get()).strip().lower()
        if q and q != "بحث باسم أو بريد أو واتساب...":
            emps = [e for e in emps if
                    q in e.get("name","").lower()     or
                    q in e.get("email","").lower()    or
                    q in e.get("whatsapp","").lower() or
                    q in e.get("title","").lower()    or
                    q in e.get("sub_dept","").lower()]
        for e in emps:
            status = "نشط" if e.get("active", True) else "موقوف"
            tag    = "active" if e.get("active", True) else "inactive"
            self._tbl.insert("", "end", iid=str(e["id"]),
                             values=(e.get("name",""), e.get("title",""),
                                     e.get("email",""), e.get("whatsapp",""),
                                     e.get("dept",""), e.get("sub_dept",""),
                                     status),
                             tags=(tag,))
        self._tbl.tag_configure("active",   foreground=TEXT_PRI, background=BG_CARD)
        self._tbl.tag_configure("inactive", foreground=TEXT_DIM, background=BG_DARK)
        self._count_lbl.config(text=f"{len(emps)} موظف")

    def _on_search(self, *args):
        self._refresh_table()

    def _sort_by(self, col):
        items = [(self._tbl.set(k, col), k) for k in self._tbl.get_children("")]
        items.sort()
        for i, (_, k) in enumerate(items):
            self._tbl.move(k, "", i)

    def _tbl_right_click(self, event):
        row = self._tbl.identify_row(event.y)
        if not row:
            return
        self._tbl.selection_set(row)
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT_PRI,
                       activebackground=ACCENT, activeforeground=WHITE)
        menu.add_command(label="✏️ تعديل",       command=self._edit_employee)
        menu.add_command(label="📋 نسخ البريد",   command=self._copy_email)
        menu.add_command(label="📱 نسخ الواتساب", command=self._copy_whatsapp)
        menu.add_separator()
        menu.add_command(label="⏸ تغيير الحالة", command=self._toggle_active)
        menu.add_separator()
        menu.add_command(label="🗑️ حذف",          command=self._delete_employee)
        menu.post(event.x_root, event.y_root)

    # ── CRUD الموظفين ──
    def _add_employee(self, dept=None, sub=None):
        dlg = EmployeeDialog(self, self.db)
        if dept:
            dlg._dept_var.set(dept)
            dlg._on_dept_change()
        if sub:
            dlg._sub_var.set(sub)
        self.wait_window(dlg)
        if dlg.result:
            self.db.add_employee(dlg.result)
            self._refresh_tree()
            self._refresh_table()
            messagebox.showinfo("تم", f"تمت إضافة {dlg.result['name']}")

    def _edit_employee(self):
        sel = self._tbl.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر موظفاً أولاً")
            return
        emp_id = int(sel[0])
        emp    = next((e for e in self.db.data["employees"]
                       if e.get("id") == emp_id), None)
        if not emp:
            return
        dlg = EmployeeDialog(self, self.db, emp)
        self.wait_window(dlg)
        if dlg.result:
            self.db.update_employee(emp_id, dlg.result)
            self._refresh_tree()
            self._refresh_table()

    def _delete_employee(self):
        sel = self._tbl.selection()
        if not sel:
            return
        emp_id = int(sel[0])
        emp    = next((e for e in self.db.data["employees"]
                       if e.get("id") == emp_id), None)
        name   = emp.get("name","الموظف") if emp else "الموظف"
        if messagebox.askyesno("تأكيد الحذف", f"هل تريد حذف [{name}]؟"):
            self.db.delete_employee(emp_id)
            self._refresh_tree()
            self._refresh_table()

    def _toggle_active(self):
        sel = self._tbl.selection()
        if not sel:
            return
        emp_id = int(sel[0])
        emp    = next((e for e in self.db.data["employees"]
                       if e.get("id") == emp_id), None)
        if emp:
            self.db.update_employee(emp_id, {"active": not emp.get("active", True)})
            self._refresh_table()

    def _copy_email(self):
        sel = self._tbl.selection()
        if not sel:
            return
        emp_id = int(sel[0])
        emp    = next((e for e in self.db.data["employees"]
                       if e.get("id") == emp_id), None)
        if emp and emp.get("email"):
            self.clipboard_clear()
            self.clipboard_append(emp["email"])
            messagebox.showinfo("تم النسخ", emp["email"])

    def _copy_whatsapp(self):
        sel = self._tbl.selection()
        if not sel:
            return
        emp_id = int(sel[0])
        emp    = next((e for e in self.db.data["employees"]
                       if e.get("id") == emp_id), None)
        if emp and emp.get("whatsapp"):
            self.clipboard_clear()
            self.clipboard_append(emp["whatsapp"])
            messagebox.showinfo("تم النسخ", emp["whatsapp"])

    # ── إدارة الهيكل ──
    def _add_dept(self, _=None):
        name = simpledialog.askstring("إضافة إدارة",
                                       "اسم الإدارة الجديدة:", parent=self)
        if name and name.strip():
            self.db.add_dept(name.strip())
            self._refresh_tree()

    def _add_sub_dept(self, dept=None):
        if not dept:
            depts = self.db.get_depts()
            if not depts:
                messagebox.showwarning("تنبيه", "أضف إدارة أولاً")
                return
            win = tk.Toplevel(self)
            win.title("اختر الإدارة")
            win.configure(bg=BG_DARK)
            win.geometry("300x160")
            win.grab_set()
            tk.Label(win, text="الإدارة الرئيسية:", bg=BG_DARK,
                     fg=TEXT_PRI, font=FONT_BODY).pack(pady=(16,4))
            dv  = tk.StringVar(value=depts[0])
            ttk.Combobox(win, textvariable=dv, values=depts,
                         state="readonly").pack(fill="x", padx=16)
            chosen = [None]
            def ok():
                chosen[0] = dv.get(); win.destroy()
            tk.Button(win, text="التالي", bg=ACCENT, fg=WHITE,
                      bd=0, padx=16, pady=6, command=ok).pack(pady=12)
            win.wait_window()
            dept = chosen[0]
            if not dept:
                return
        name = simpledialog.askstring("إضافة قسم",
                                       f"اسم القسم الجديد في [{dept}]:",
                                       parent=self)
        if name and name.strip():
            self.db.add_sub_dept(dept, name.strip())
            self._refresh_tree()

    def _delete_dept(self, dept):
        cnt = len(self.db.get_employees(dept=dept))
        msg = f"هل تريد حذف إدارة [{dept}]؟"
        if cnt:
            msg += f"\nسيتم حذف {cnt} موظف معها!"
        if messagebox.askyesno("تأكيد الحذف", msg):
            self.db.delete_dept(dept)
            self._refresh_tree()
            self._refresh_table()

    def _delete_sub_dept(self, dept, sub):
        cnt = len(self.db.get_employees(dept=dept, sub_dept=sub))
        msg = f"هل تريد حذف قسم [{sub}]؟"
        if cnt:
            msg += f"\nسيتم حذف {cnt} موظف معه!"
        if messagebox.askyesno("تأكيد الحذف", msg):
            self.db.delete_sub_dept(dept, sub)
            self._refresh_tree()
            self._refresh_table()

    # ── تصدير ──
    def _export_to_system(self):
        cfg = self.db.export_to_config()
        out = Path(__file__).parent / "data" / "config_contacts.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        ne = len(cfg["email_dept_map"])
        nw = len(cfg["whatsapp_groups"])
        messagebox.showinfo(
            "تم التصدير",
            f"تم تصدير جهات الاتصال:\n\n"
            f"  البريد الإلكتروني: {ne} عنوان\n"
            f"  الواتساب: {nw} رقم\n\n"
            f"محفوظ في: data/config_contacts.json\n"
            f"النظام سيستخدمها تلقائياً."
        )
