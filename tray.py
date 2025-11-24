"""System tray integration for Crypto Ticker."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QImage, QPainter, QFont, QColor, QPixmap
from PySide6.QtCore import Signal, Qt
from PySide6.QtSvg import QSvgRenderer
from typing import Dict

from settings import Settings
from version import __version__, __app_name__


class TrayIcon(QSystemTrayIcon):
    """System tray icon with price display."""

    settings_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()
    pause_toggled = Signal(bool)  # True = paused
    notifications_toggled = Signal(bool)  # True = enabled

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._current_price = 0.0
        self._secondary_prices: Dict[str, float] = {}
        self._paused = False
        self._notifications_enabled = settings.notifications_enabled

        self._setup_icon()
        self._setup_menu()

        self.activated.connect(self._on_activated)

    def _get_app_dir(self) -> Path:
        """Get the application directory."""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent

    def _setup_icon(self):
        """Set up the tray icon from logo file (ICO, PNG, or SVG)."""
        app_dir = self._get_app_dir()

        # Try ICO or PNG first (native format, better quality)
        for ext in ['ico', 'png']:
            icon_path = app_dir / f"logo.{ext}"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setIcon(icon)
                    self._update_tooltip()
                    return

        # Fallback to SVG rendering
        svg_path = app_dir / "logo.svg"
        if svg_path.exists():
            renderer = QSvgRenderer(str(svg_path))
            # Use 64x64 for tray icon (will be scaled by OS)
            image = QImage(64, 64, QImage.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            icon = QIcon(QPixmap.fromImage(image))
            self.setIcon(icon)
        self._update_tooltip()

    def _setup_menu(self):
        """Set up the context menu."""
        menu = QMenu()

        # Version at top (disabled)
        version_action = menu.addAction(f"{__app_name__} v{__version__}")
        version_action.setEnabled(False)

        menu.addSeparator()

        # Price display (disabled, just for info)
        self._price_action = menu.addAction("Loading...")
        self._price_action.setEnabled(False)

        menu.addSeparator()

        # Pause/Resume
        self._pause_action = menu.addAction("Pause")
        self._pause_action.triggered.connect(self._on_pause_clicked)

        # Notifications toggle
        self._notifications_action = menu.addAction("Notifications")
        self._notifications_action.setCheckable(True)
        self._notifications_action.setChecked(self._notifications_enabled)
        self._notifications_action.triggered.connect(self._on_notifications_clicked)

        menu.addSeparator()

        # Settings
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_requested.emit)

        # About
        about_action = menu.addAction("About")
        about_action.triggered.connect(self.about_requested.emit)

        menu.addSeparator()

        # Quit
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested.emit)

        self.setContextMenu(menu)

    def _on_pause_clicked(self):
        """Handle pause button click."""
        self._paused = not self._paused
        self._pause_action.setText("Resume" if self._paused else "Pause")
        self.pause_toggled.emit(self._paused)

    def _on_notifications_clicked(self):
        """Handle notifications toggle click."""
        self._notifications_enabled = self._notifications_action.isChecked()
        self.notifications_toggled.emit(self._notifications_enabled)

    def set_notifications_enabled(self, enabled: bool):
        """Set notifications state (called from outside)."""
        self._notifications_enabled = enabled
        self._notifications_action.setChecked(enabled)

    def set_paused(self, paused: bool):
        """Set paused state (called from outside)."""
        self._paused = paused
        self._pause_action.setText("Resume" if self._paused else "Pause")

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.settings_requested.emit()


    def _update_tooltip(self):
        """Update tooltip text."""
        symbol = self.settings.crypto_symbol.upper()
        currency = self.settings.vs_currency.upper()

        lines = [f"{__app_name__}"]

        if self._current_price > 0:
            lines.append(f"{symbol}: ${self._current_price:,.2f} {currency}")

        if self._paused:
            lines.append("[PAUSED]")

        self.setToolTip("\n".join(lines))

    def set_price(self, price: float):
        """Update the displayed price."""
        self._current_price = price

        # Update tooltip and menu (icon stays as logo)
        symbol = self.settings.crypto_symbol.upper()
        price_text = f"{symbol}: ${price:,.2f}"
        self._update_tooltip()
        self._price_action.setText(price_text)

    def set_secondary_prices(self, prices: Dict[str, float]):
        """Update secondary cryptocurrency prices."""
        self._secondary_prices = prices
        self._update_tooltip()

    def apply_settings(self, settings: Settings):
        """Apply new settings."""
        self.settings = settings
        self.set_price(self._current_price)
        self.set_notifications_enabled(settings.notifications_enabled)
