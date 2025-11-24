"""Notification module for price change alerts."""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QSoundEffect

from settings import Settings


class NotificationManager(QObject):
    """Manages price change notifications with rate limiting."""

    notification_triggered = Signal(str, str)  # title, message

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._last_price: Optional[float] = None
        self._last_notification_time: Optional[datetime] = None
        self._sound_effect: Optional[QSoundEffect] = None
        self._setup_sound()

    def _setup_sound(self):
        """Set up sound effect for notifications."""
        self._sound_effect = QSoundEffect(self)

    def _get_sound_path(self) -> Optional[Path]:
        """Get the full path to the notification sound file."""
        if not self.settings.notification_sound:
            return None

        sound_path = Path(self.settings.notification_sound)

        # If relative path, resolve from app directory
        if not sound_path.is_absolute():
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                app_dir = Path(sys.executable).parent
            else:
                # Running as script
                app_dir = Path(__file__).parent
            sound_path = app_dir / sound_path

        if sound_path.exists():
            return sound_path
        return None

    def _play_sound(self):
        """Play notification sound if configured."""
        sound_path = self._get_sound_path()
        if sound_path and self._sound_effect:
            url = QUrl.fromLocalFile(str(sound_path))
            self._sound_effect.setSource(url)
            self._sound_effect.play()

    def _can_notify(self) -> bool:
        """Check if enough time has passed since last notification."""
        if self._last_notification_time is None:
            return True

        cooldown = timedelta(minutes=self.settings.notification_cooldown)
        return datetime.now() - self._last_notification_time >= cooldown

    def _send_system_notification(self, title: str, message: str):
        """Send OS-level notification."""
        try:
            if sys.platform == "win32":
                self._send_windows_notification(title, message)
            elif sys.platform == "darwin":
                self._send_macos_notification(title, message)
            else:
                self._send_linux_notification(title, message)
        except Exception as e:
            print(f"Notification error: {e}")

    def _send_windows_notification(self, title: str, message: str):
        """Send Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
        except ImportError:
            # Fallback to system tray notification (handled by tray.py)
            self.notification_triggered.emit(title, message)

    def _send_macos_notification(self, title: str, message: str):
        """Send macOS notification."""
        try:
            os.system(f'''osascript -e 'display notification "{message}" with title "{title}"' ''')
        except Exception:
            self.notification_triggered.emit(title, message)

    def _send_linux_notification(self, title: str, message: str):
        """Send Linux notification."""
        try:
            os.system(f'notify-send "{title}" "{message}"')
        except Exception:
            self.notification_triggered.emit(title, message)

    def check_price_change(self, current_price: float, symbol: str) -> bool:
        """
        Check if price change warrants a notification.
        Returns True if notification was sent.
        """
        if not self.settings.notifications_enabled:
            return False

        if self._last_price is None or self._last_price == 0:
            self._last_price = current_price
            return False

        # Calculate percentage change
        change_percent = ((current_price - self._last_price) / self._last_price) * 100

        # Check if change meets threshold
        if abs(change_percent) < self.settings.notification_threshold:
            self._last_price = current_price
            return False

        # Check direction
        direction = self.settings.notification_direction
        if direction == "up" and change_percent < 0:
            self._last_price = current_price
            return False
        if direction == "down" and change_percent > 0:
            self._last_price = current_price
            return False

        # Check cooldown
        if not self._can_notify():
            return False

        # Send notification
        self._last_price = current_price
        self._last_notification_time = datetime.now()

        # Format message
        direction_emoji = "+" if change_percent > 0 else ""
        title = f"{symbol.upper()} Price Alert"
        message = f"${current_price:,.2f} ({direction_emoji}{change_percent:.2f}%)"

        self._send_system_notification(title, message)
        self._play_sound()
        self.notification_triggered.emit(title, message)

        return True

    def reset_last_price(self):
        """Reset last price (call when switching cryptocurrencies)."""
        self._last_price = None

    def apply_settings(self, settings: Settings):
        """Apply new settings."""
        self.settings = settings
