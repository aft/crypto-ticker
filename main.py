"""Crypto Ticker - Desktop cryptocurrency price widget."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon

from settings import Settings
from widget import PriceWidget
from tray import TrayIcon
from settings_dialog import SettingsDialog
from about_dialog import AboutDialog
from api import init_api, get_api
from notifications import NotificationManager
from price_worker import PriceWorker, PriceFetchThread


class CryptoTicker:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Set application icon (cross-platform)
        self._set_app_icon()

        # Load settings
        self.settings = Settings.load()

        # Initialize API with cache directory
        self._api = init_api(Settings.get_cache_dir())
        self._api.update_retry_settings(
            self.settings.retry_attempts,
            self.settings.retry_wait
        )
        self._api.on_state_change = self._on_api_state_change

        # Create components
        self._widget = PriceWidget(self.settings)
        self._tray = TrayIcon(self.settings)
        self._notification_manager = NotificationManager(self.settings)
        self._settings_dialog = None
        self._about_dialog = None
        self._current_price = 0.0
        self._fetch_thread = None

        # Create price worker for background fetching
        self._price_worker = PriceWorker()
        self._price_worker.price_fetched.connect(self._on_price_fetched)
        self._price_worker.secondary_fetched.connect(self._on_secondary_fetched)
        self._price_worker.fetch_error.connect(self._on_fetch_error)
        self._price_worker.fetch_success.connect(self._on_fetch_success)

        # Connect signals
        self._widget.settings_requested.connect(self._show_settings)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.about_requested.connect(self._show_about)
        self._tray.quit_requested.connect(self._quit)
        self._tray.pause_toggled.connect(self._on_pause_toggled)
        self._tray.notifications_toggled.connect(self._on_notifications_toggled)

        # Price update timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_price)
        self._timer.start(self.settings.update_interval * 1000)

        # Auto-resume timer (checks every minute)
        self._auto_resume_timer = QTimer()
        self._auto_resume_timer.timeout.connect(self._check_auto_resume)
        self._auto_resume_timer.start(60000)

        # Initial price fetch
        QTimer.singleShot(100, self._update_price)

    def _set_app_icon(self):
        """Set application icon (cross-platform)."""
        # Get app directory
        if getattr(sys, 'frozen', False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).parent

        # Try formats in order: ICO (Windows), PNG, SVG
        for ext in ['ico', 'png', 'svg']:
            icon_path = app_dir / f"logo.{ext}"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.app.setWindowIcon(icon)
                    break

    def _on_api_state_change(self, state):
        """Handle API state changes."""
        self._tray.set_paused(state.should_skip())

    def _on_pause_toggled(self, paused: bool):
        """Handle pause toggle from tray."""
        if paused:
            self._api.pause()
        else:
            self._api.resume()
            # Fetch immediately on resume
            QTimer.singleShot(100, self._update_price)

    def _on_notifications_toggled(self, enabled: bool):
        """Handle notifications toggle from tray."""
        self.settings.notifications_enabled = enabled
        self.settings.save()
        self._notification_manager.apply_settings(self.settings)

    def _check_auto_resume(self):
        """Check if auto-pause period has expired."""
        remaining = self._api.state.get_auto_resume_remaining()
        if remaining is not None and remaining <= 0:
            self._api.resume()
            QTimer.singleShot(100, self._update_price)

    def _update_price(self):
        """Start background fetch for prices."""
        if self._api.is_paused():
            return

        # Don't start new fetch if one is already running
        if self._fetch_thread and self._fetch_thread.isRunning():
            return

        # Update worker config
        self._price_worker.set_config(
            self.settings.crypto_symbol,
            self.settings.vs_currency,
            self.settings.secondary_cryptos
        )

        # Start background fetch
        self._fetch_thread = PriceFetchThread(self._price_worker)
        self._fetch_thread.start()

    def _on_price_fetched(self, price: float):
        """Handle price fetched from background thread."""
        self._current_price = price
        self._widget.set_price(price)
        self._tray.set_price(price)
        # Check for price change notification
        self._notification_manager.check_price_change(price, self.settings.crypto_symbol)

    def _on_secondary_fetched(self, prices: dict):
        """Handle secondary prices fetched from background thread."""
        self._widget.set_secondary_prices(prices)
        self._tray.set_secondary_prices(prices)

    def _on_fetch_error(self, error: str):
        """Handle fetch error."""
        self._widget.set_connection_error(True)

    def _on_fetch_success(self):
        """Handle successful fetch."""
        self._widget.set_connection_error(False)

    def _show_settings(self):
        """Show the settings dialog."""
        if self._settings_dialog is None or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsDialog(self.settings)
            self._settings_dialog.settings_changed.connect(self._on_settings_changed)
            self._settings_dialog.finished.connect(self._on_settings_closed)
            self._settings_dialog.show()

    def _show_about(self):
        """Show the about dialog."""
        if self._about_dialog is None or not self._about_dialog.isVisible():
            self._about_dialog = AboutDialog()
            self._about_dialog.show()

    def _on_settings_changed(self, new_settings: Settings):
        """Handle live preview of settings changes."""
        # Check if crypto/currency changed to refetch price
        crypto_changed = (
            new_settings.crypto_symbol != self.settings.crypto_symbol or
            new_settings.vs_currency != self.settings.vs_currency
        )

        # Update our settings object with all values from new_settings
        self.settings.font_name = new_settings.font_name
        self.settings.font_size = new_settings.font_size
        self.settings.font_weight = new_settings.font_weight
        self.settings.text_r = new_settings.text_r
        self.settings.text_g = new_settings.text_g
        self.settings.text_b = new_settings.text_b
        self.settings.text_alpha = new_settings.text_alpha
        self.settings.bg_r = new_settings.bg_r
        self.settings.bg_g = new_settings.bg_g
        self.settings.bg_b = new_settings.bg_b
        self.settings.bg_alpha = new_settings.bg_alpha
        self.settings.crypto_symbol = new_settings.crypto_symbol
        self.settings.vs_currency = new_settings.vs_currency
        self.settings.show_prefix = new_settings.show_prefix
        self.settings.secondary_cryptos = new_settings.secondary_cryptos.copy()
        self.settings.secondary_display = new_settings.secondary_display
        self.settings.secondary_font_scale = new_settings.secondary_font_scale
        self.settings.badge_font_name = new_settings.badge_font_name
        self.settings.badge_font_weight = new_settings.badge_font_weight
        self.settings.badge_bg_r = new_settings.badge_bg_r
        self.settings.badge_bg_g = new_settings.badge_bg_g
        self.settings.badge_bg_b = new_settings.badge_bg_b
        self.settings.badge_bg_alpha = new_settings.badge_bg_alpha
        self.settings.badge_text_r = new_settings.badge_text_r
        self.settings.badge_text_g = new_settings.badge_text_g
        self.settings.badge_text_b = new_settings.badge_text_b
        self.settings.badge_text_alpha = new_settings.badge_text_alpha
        self.settings.indicator_enabled = new_settings.indicator_enabled
        self.settings.indicator_flash_enabled = new_settings.indicator_flash_enabled
        self.settings.indicator_up_r = new_settings.indicator_up_r
        self.settings.indicator_up_g = new_settings.indicator_up_g
        self.settings.indicator_up_b = new_settings.indicator_up_b
        self.settings.indicator_up_alpha = new_settings.indicator_up_alpha
        self.settings.indicator_down_r = new_settings.indicator_down_r
        self.settings.indicator_down_g = new_settings.indicator_down_g
        self.settings.indicator_down_b = new_settings.indicator_down_b
        self.settings.indicator_down_alpha = new_settings.indicator_down_alpha
        self.settings.notifications_enabled = new_settings.notifications_enabled
        self.settings.notification_threshold = new_settings.notification_threshold
        self.settings.notification_direction = new_settings.notification_direction
        self.settings.notification_sound = new_settings.notification_sound
        self.settings.notification_cooldown = new_settings.notification_cooldown
        self.settings.always_on_top = new_settings.always_on_top
        self.settings.launch_on_startup = new_settings.launch_on_startup
        self.settings.update_interval = new_settings.update_interval
        self.settings.retry_attempts = new_settings.retry_attempts
        self.settings.retry_wait = new_settings.retry_wait

        # Apply to widget, tray, and notification manager
        self._widget.apply_settings(self.settings)
        self._tray.apply_settings(self.settings)
        self._notification_manager.apply_settings(self.settings)

        # Reset notification price tracking if crypto changed
        if crypto_changed:
            self._notification_manager.reset_last_price()

        # Update API retry settings
        self._api.update_retry_settings(
            self.settings.retry_attempts,
            self.settings.retry_wait
        )

        # Update timer interval
        self._timer.setInterval(self.settings.update_interval * 1000)

        # Refetch price if crypto changed
        if crypto_changed:
            self._update_price()
        elif self._current_price > 0:
            # Just update the display format (prefix changed)
            self._widget.set_price(self._current_price)
            self._tray.set_price(self._current_price)

    def _on_settings_closed(self, result):
        """Handle settings dialog closed."""
        if result == SettingsDialog.Accepted:
            # Settings were saved - reload from file
            self.settings = Settings.load()
            self._widget.settings = self.settings
            self._tray.settings = self.settings
            self._widget.apply_settings(self.settings)
            self._tray.apply_settings(self.settings)
            self._api.update_retry_settings(
                self.settings.retry_attempts,
                self.settings.retry_wait
            )
            self._timer.setInterval(self.settings.update_interval * 1000)
            self._update_price()
        else:
            # Cancelled - reload original settings from file
            self.settings = Settings.load()
            self._widget.settings = self.settings
            self._tray.settings = self.settings
            self._widget.apply_settings(self.settings)
            self._tray.apply_settings(self.settings)
            if self._current_price > 0:
                self._widget.set_price(self._current_price)
                self._tray.set_price(self._current_price)

    def _quit(self):
        """Quit the application."""
        self._tray.hide()
        self.app.quit()

    def run(self) -> int:
        """Run the application."""
        self._widget.show()
        self._tray.show()
        return self.app.exec()


def main():
    """Entry point."""
    ticker = CryptoTicker()
    sys.exit(ticker.run())


if __name__ == "__main__":
    main()
