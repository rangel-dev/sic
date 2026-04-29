"""
SIC — System Intelligence Commerce
Entry point for the application.
"""
import os
import sys
import warnings

# Suppress openpyxl warnings about missing default styles and unsupported extensions
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def _fix_qt_plugin_path() -> None:
    """
    Set QT_QPA_PLATFORM_PLUGIN_PATH before Qt initializes.

    On macOS with PySide6 in a venv, the platform plugin path is sometimes
    empty at startup (QT_QPA_PLATFORM_PLUGIN_PATH=""), causing the cocoa
    plugin not to be found. We resolve it dynamically from the installed
    PySide6 package location so it works regardless of venv path.

    NOTE: We do NOT pre-load Qt frameworks via ctypes — that causes symbol
    conflicts because ctypes and PySide6's own loader create separate dylib
    handles for the same frameworks, breaking weak symbol resolution.
    """
    if sys.platform != "darwin":
        return

    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return  # Already set externally (e.g. via run.sh)

    try:
        import importlib.util
        spec = importlib.util.find_spec("PySide6")
        if spec is None or spec.origin is None:
            return

        pyside6_dir = os.path.dirname(spec.origin)
        plugins_dir = os.path.join(pyside6_dir, "Qt", "plugins", "platforms")

        if os.path.isdir(plugins_dir):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_dir

    except Exception:
        pass


_fix_qt_plugin_path()

from src.main_app import main  # noqa: E402

if __name__ == "__main__":
    main()
