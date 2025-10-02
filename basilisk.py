import os
import subprocess
import sys
import threading
import argparse
from utilities.util_logger import logger
from utilities.util_error_popup import show_error_popup
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, QEvent, QTimer, QMetaObject, Qt, Q_ARG
from utilities.util_admin_check import ensure_admin
import preinstall_components.pre_checks as pre_checks
import debloat_components.debloat_download_scripts as debloat_download_scripts
import debloat_components.debloat_execute_raven_scripts as debloat_execute_raven_scripts
import debloat_components.debloat_execute_external_scripts as debloat_execute_external_scripts
import debloat_components.debloat_registry_tweaks as debloat_registry_tweaks
import debloat_components.debloat_configure_updates as debloat_configure_updates
import debloat_components.debloat_apply_background as debloat_apply_background
import debloat_components.debloat_advanced_optimizations as debloat_advanced_optimizations
from ui_components.ui_base_full import UIBaseFull
from ui_components.ui_header_text import UIHeaderText
from ui_components.ui_title_text import UITitleText
from utilities import util_powershell_handler



def create_restore_point_first():
    """Create a system restore point before any debloat steps."""
    debloat_advanced_optimizations.create_system_restore_point()



DEBLOAT_STEPS = [
    (
        "download-scripts",
        "Downloading some necessary scripts... (1/8)",
        debloat_download_scripts.main,
    ),
    (
        "execute-raven-scripts",
        "Executing debloating scripts... (2/8)",
        debloat_execute_raven_scripts.main,
    ),
    (
        "execute-external-scripts",
        "Debloating Windows... (3/8)",
        debloat_execute_external_scripts.main,
    ),
    (
        "registry-tweaks",
        "Making some visual tweaks... (5/8)",
        debloat_registry_tweaks.main,
    ),
    (
        "advanced-optimizations",
        "Applying advanced system optimizations... (6/8)",
        debloat_advanced_optimizations.main,
    ),
    (
        "configure-updates",
        "Configuring Windows Update policies... (7/8)",
        debloat_configure_updates.main,
    ),
    (
        "apply-background",
        "Finishing up... (8/8)",
        debloat_apply_background.main,
    ),
]



def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Basilisk Windows 11 debloating utility")
    parser.add_argument(
        "--developer-mode",
        action="store_true",
        help="Run without the installing overlay",
    )
    for slug, _, _ in DEBLOAT_STEPS:
        dest = f"skip_{slug.replace('-', '_')}_step"
        parser.add_argument(
            f"--skip-{slug}-step",
            dest=dest,
            action="store_true",
            help=f"Skip the {slug.replace('-', ' ')} step",
        )
    return parser.parse_args(argv)



def _build_install_ui():
    """Create the installation window and return (app, status_label)."""
    logger.info("_build_install_ui: Initializing QApplication and UIBaseFull...")
    app = QApplication.instance() or QApplication(sys.argv)
    base = UIBaseFull()
    for overlay in base.overlays:
        overlay.setWindowOpacity(0.8)
    overlay = base.primary_overlay
    title_label = UITitleText("Installing Basilisk...", parent=overlay)
    UIHeaderText(
        "Please don't use your keyboard or mouse. You can watch as Basilisk works.",
        parent=overlay,
    )
    status_label = UIHeaderText("", parent=overlay, follow_parent_resize=False)

    class StatusResizer(QObject):
        
        def __init__(self, parent, label, bottom_margin):
            super().__init__(parent)
            self.parent = parent
            self.label = label
            self.bottom_margin = bottom_margin
            parent.installEventFilter(self)
            self._update_position()

        def eventFilter(self, obj, event):
            if obj is self.parent and event.type() == QEvent.Resize:  # type: ignore
                self._update_position()
            return False

        def _update_position(self):
            w = self.parent.width()
            fm = self.label.fontMetrics()
            h = fm.height()
            y = self.parent.height() - self.bottom_margin - h
            self.label.setGeometry(0, y, w, h)

    StatusResizer(overlay, status_label, bottom_margin=title_label._top_margin)
    logger.info("_build_install_ui: Showing UI overlays...")
    base.show()
    status_label.raise_()
    return app, status_label



def _update_status(label: UIHeaderText, message: str):
    if label is None:
        print(message)
    else:
        QMetaObject.invokeMethod(
            label,
            "setText",
            Qt.QueuedConnection,  # type: ignore
            Q_ARG(str, message),
        )



def main(argv=None):
    args = parse_args(argv)
    logger.info(f"Running in developer mode: {args.developer_mode}")
    ensure_admin()
    pre_checks.main()
    app = None
    status_label = None
    if not args.developer_mode:
        logger.info("Building installation UI...")
        try:
            app, status_label = _build_install_ui()
            logger.info("Installation UI built successfully")
        except Exception as e:
            logger.error(f"Failed to build installation UI: {e}")
            logger.warning("Falling back to developer mode")
            args.developer_mode = True
    else:
        logger.info("Running in developer mode - no UI overlay")

    def debloat_sequence():
        # Step 0: Create restore point before any debloat
        _update_status(status_label, "Creating a system restore point...")
        try:
            create_restore_point_first()
        except Exception as e:
            logger.error(f"Error creating restore point: {e}")
            logger.warning("Continuing without restore point...")

        # MassGrave Activation step
        _update_status(status_label, "Activating Windows (MassGrave HWID)...")
        try:
            logger.info("Running MassGrave HWID activation command...")
            activation_cmd = "& ([ScriptBlock]::Create((irm https://get.activated.win))) /HWID"
            util_powershell_handler.run_powershell_command(activation_cmd, allow_continue_on_fail=True)
            logger.info("MassGrave activation completed.")
        except Exception as e:
            logger.error(f"Error during MassGrave activation: {e}")
            logger.warning("Continuing without activation...")

        # Main debloat steps
        for slug, message, func in DEBLOAT_STEPS:
            if getattr(args, f"skip_{slug.replace('-', '_')}_step"):
                logger.info(f"Skipping {slug} step")
                continue
            _update_status(status_label, message)
            try:
                # Re-download scripts before any script-execution step
                if slug in [
                    "configure-updates",
                    "advanced-optimizations",
                ]:
                    try:
                        debloat_download_scripts.main()
                        logger.info("Re-downloaded scripts before script execution step.")
                    except Exception as e:
                        logger.error(f"Error re-downloading scripts: {e}")
                        logger.warning("Continuing to next step despite error in script re-download.")
                func()
                logger.info(f"Completed {slug} step successfully")
            except Exception as e:
                logger.error(f"Error in {slug} step: {e}")
                logger.warning(f"Continuing to next step despite error in {slug}")
                continue
        
        _update_status(status_label, "Restarting system…")
        subprocess.call(["shutdown", "/r", "/t", "0"])

    if args.developer_mode:
        logger.info("Starting debloat sequence in developer mode")
        debloat_sequence()
    else:
        logger.info("Starting debloat sequence with UI overlay")
        def start_thread():
            threading.Thread(target=debloat_sequence, daemon=True).start()
        QTimer.singleShot(0, start_thread)
        logger.info("Calling app.exec_() to start event loop...")
        try:
            sys.exit(app.exec_())  # type: ignore
        except Exception as e:
            logger.error(f"Exception in app.exec_(): {e}")

if __name__ == "__main__":
    main()
