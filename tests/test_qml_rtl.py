"""RTL rendering guards.

The written value and the rendered value disagree by design here, which is
what made this bug class survive so long. `qml/Main.qml` sets
`LayoutMirroring.enabled: true`, and Qt mirrors an *explicitly set*
`horizontalAlignment` while leaving an unset one alone. So a component that
reads `horizontalAlignment: Text.AlignRight` in the source renders
`AlignLeft` on screen.

Every assertion below is therefore on `effectiveHorizontalAlignment`, never on
`horizontalAlignment`. A test that read the written property would have passed
against the broken code.

These run headless via QQmlComponent — no window, no event loop.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QUrl                      # noqa: E402
from PySide6.QtGui import QGuiApplication                        # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine              # noqa: E402

ALIGN_LEFT, ALIGN_RIGHT = 1, 2

_app = QGuiApplication.instance() or QGuiApplication([])

# Module-level, deliberately: a QQmlEngine built inline as
# `QQmlComponent(QQmlEngine())` is a temporary that Python collects before the
# component is used, and every create() then fails with an empty error list.
_engine = QQmlEngine()


def build(body: str, props: str = ""):
    """Instantiate a mirrored root holding `body`; expose ints via `props`."""
    qml = (
        "import QtQuick\n"
        "import QtQuick.Controls.Basic\n"
        "import QtQuick.Layouts\n"
        "Item {\n"
        "    LayoutMirroring.enabled: true\n"      # exactly what Main.qml does
        "    LayoutMirroring.childrenInherit: true\n"
        "    width: 400; height: 200\n"
        f"{props}\n{body}\n"
        "}\n"
    )
    comp = QQmlComponent(_engine)
    comp.setData(QByteArray(qml.encode("utf-8")), QUrl("inline"))
    obj = comp.create()
    if obj is None:                                   # pragma: no cover
        raise AssertionError("; ".join(e.toString() for e in comp.errors()))
    obj._component = comp        # keep the component alive alongside the object
    return obj


class MirroringSemanticsTests(unittest.TestCase):
    """Pins the Qt behaviour the fix depends on. If a Qt upgrade changes any
    of these, the fix's reasoning is void and this fails first — which is the
    point of asserting a framework behaviour we did not write."""

    def test_explicit_alignright_is_mirrored_to_left(self):
        o = build(
            'Text { id: t; text: "نص"; horizontalAlignment: Text.AlignRight }',
            "property int eff: t.effectiveHorizontalAlignment",
        )
        self.assertEqual(o.property("eff"), ALIGN_LEFT)

    def test_unset_alignment_is_not_mirrored(self):
        o = build(
            'Text { id: t; text: "نص" }',
            "property int eff: t.effectiveHorizontalAlignment",
        )
        self.assertEqual(o.property("eff"), ALIGN_RIGHT)

    def test_unset_alignment_follows_the_content_not_the_locale(self):
        """Why the fix pins alignment explicitly instead of deleting it: with
        no explicit value, Latin content flips the element left."""
        o = build(
            'Text { id: t; text: "Ahmed" }',
            "property int eff: t.effectiveHorizontalAlignment",
        )
        self.assertEqual(o.property("eff"), ALIGN_LEFT)

    def test_explicit_alignright_survives_when_mirroring_is_off(self):
        """The shape of the fix: explicit + mirroring off holds right even for
        Latin content the user typed."""
        o = build(
            'Text { id: t; text: "Ahmed"; horizontalAlignment: Text.AlignRight;'
            " LayoutMirroring.enabled: false }",
            "property int eff: t.effectiveHorizontalAlignment",
        )
        self.assertEqual(o.property("eff"), ALIGN_RIGHT)


class FormPrimitiveSourceTests(unittest.TestCase):
    """The shared primitives, checked at the source level.

    Instantiating FormField here would be the stronger test, but a component
    reached through a directory import from an inline root does not resolve the
    `Theme` context property, so it comes up half-initialised and the assertion
    would be made against a component the app never builds that way. The real
    components are checked where they actually render: the offscreen pass in
    tools/capture_qt.py, which is a release gate.
    """

    QML_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "qml")

    def _read(self, name):
        with open(os.path.join(self.QML_DIR, name), encoding="utf-8") as fh:
            return fh.read()

    def test_form_field_never_enables_mirroring(self):
        """It used to set `LayoutMirroring.enabled: !field.ltr`, which turned
        mirroring ON for the Arabic branch and flipped its AlignRight to
        AlignLeft — the defect behind every left-hugging Arabic field."""
        src = self._read("FormField.qml")
        self.assertIn("LayoutMirroring.enabled: false", src)
        self.assertNotIn("LayoutMirroring.enabled: !field.ltr", src)

    def test_form_field_keeps_both_branches(self):
        """The ltr branch must survive: URLs, keys and ports read left."""
        src = self._read("FormField.qml")
        self.assertIn("field.ltr ? Text.AlignLeft : Text.AlignRight", src)

    def test_form_combo_value_is_guarded(self):
        src = self._read("FormCombo.qml")
        self.assertIn("LayoutMirroring.enabled: false", src)


class NoUnguardedAlignRightTests(unittest.TestCase):
    """Source guard. Any explicit AlignRight under mirroring renders left, so
    each one must be paired with `LayoutMirroring.enabled: false` — except
    inside a Popup, which does not inherit mirroring at all."""

    QML_DIR = FormPrimitiveSourceTests.QML_DIR

    def test_every_alignright_is_paired_or_inside_a_popup(self):
        offenders = []
        for name in sorted(os.listdir(self.QML_DIR)):
            if not name.endswith(".qml"):
                continue
            path = os.path.join(self.QML_DIR, name)
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().split("\n")
            in_popup = 0
            for i, line in enumerate(lines):
                if "popup:" in line or "Popup {" in line:
                    in_popup = i
                if "horizontalAlignment: Text.AlignRight" not in line:
                    continue
                if line.lstrip().startswith("//"):
                    continue
                # paired within the preceding few lines?
                window = "\n".join(lines[max(0, i - 6):i])
                if "LayoutMirroring.enabled: false" in window:
                    continue
                # inside the popup block that opened above?
                if in_popup and 0 < i - in_popup < 40:
                    continue
                offenders.append(f"{name}:{i + 1}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "explicit AlignRight with no `LayoutMirroring.enabled: false` "
            "nearby renders as AlignLeft:\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
