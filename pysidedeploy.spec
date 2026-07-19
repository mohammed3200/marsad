[app]
title = marsad
project_dir = .
input_file = app.py
project_file =
exec_directory = dist
icon =

[python]
python_path =
android_packages =

[qt]
# QML files are shipped as data (see nuitka extra_args); the app loads qml/Main.qml
qml_files = qml/Main.qml
excluded_qml_plugins =
modules = Core, Gui, Quick, Qml, QuickControls2, Network
plugins = platforms, imageformats, iconengines

[nuitka]
mode = onefile
macos.permissions =
# bundle the QML tree + fonts, and force-include the lazily-imported exporter deps
extra_args = --quiet --noinclude-qt-translations
    --include-data-dir=qml=qml
    --include-data-dir=assets=assets
    --include-data-files=settings.example.json=settings.example.json
    --include-data-files=sample_reports.json=sample_reports.json
    --include-package=core --include-package=backend
    --include-package=reportlab --include-package=openpyxl --include-package=PyPDF2
    --include-module=connectors

[buildozer]
mode = release
