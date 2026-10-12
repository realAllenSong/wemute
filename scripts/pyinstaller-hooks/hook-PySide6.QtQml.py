"""Collect only the QML modules Wemute imports.

PyInstaller's stock QtQml hook collects every module shipped in the PySide6
wheel, including WebEngine and Quick3D. That adds hundreds of megabytes to a
small converter which uses neither. Keep this list aligned with the output of
qmlimportscanner for src/wemute/qml while the Basic controls style is selected.
"""

from pathlib import Path, PurePath

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

_QML_MODULES = (
    "QtQml",
    "QtQml/Models",
    "QtQml/WorkerScript",
    "QtQuick",
    "QtQuick/Window",
    "QtQuick/Layouts",
    "QtQuick/Shapes",
    "QtQuick/Effects",
    "QtQuick/Templates",
    "QtQuick/Controls",
    "QtQuick/Controls/impl",
    "QtQuick/Controls/Basic",
    "QtQuick/Controls/Basic/impl",
    "QtQuick/Dialogs",
    "QtQuick/Dialogs/quickimpl",
    "Qt/labs/folderlistmodel",
    "Qt/labs/qmlmodels",
)

qml_root = Path(pyside6_library_info.location["QmlImportsPath"]).resolve()
qml_destination = PurePath(pyside6_library_info.qt_rel_dir) / "qml"


def _destination(source: Path) -> str:
    relative = source.relative_to(qml_root)
    return str(qml_destination / (relative if source.is_dir() else relative.parent))


for module in _QML_MODULES:
    qmldir = qml_root / module / "qmldir"
    if not qmldir.is_file():
        continue
    module_binaries, module_datas = pyside6_library_info._process_qml_plugin(qmldir)
    binaries += [(str(source), _destination(source)) for source in module_binaries]
    datas += [(str(source), _destination(source)) for source in module_datas]
