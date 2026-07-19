"""
marsad contacts data layer — org structure + employees, JSON-backed.

UI-agnostic (extracted verbatim from contacts_manager.py, minus the Tkinter
widgets). `export_to_config()` produces the email→dept / whatsapp→dept maps the
connectors use for routing.
"""
import json
from pathlib import Path

CONTACTS_FILE = Path(__file__).resolve().parent.parent / "data" / "contacts.json"

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
