"""Settings management for Crypto Ticker."""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class Settings:
    """Application settings."""

    # Font settings
    font_name: str = "Segoe UI"
    font_size: int = 24
    font_weight: int = 700

    # Text color (RGBA)
    text_r: int = 255
    text_g: int = 255
    text_b: int = 255
    text_alpha: int = 100  # 0-100

    # Background color (RGBA)
    bg_r: int = 0
    bg_g: int = 0
    bg_b: int = 0
    bg_alpha: int = 0  # 0-100 (0 = fully transparent)

    # Crypto settings
    crypto_symbol: str = "btc"  # Using symbol instead of id
    vs_currency: str = "usd"
    show_prefix: bool = True
    secondary_cryptos: List[str] = field(default_factory=list)  # Additional symbols to track
    secondary_display: str = "hover"  # "hover" or "always"
    secondary_font_scale: float = 0.7  # 0.1-3.0 multiplier of main font size

    # Symbol badge settings (for popup)
    badge_font_name: str = "Segoe UI"  # Badge symbol font
    badge_font_weight: int = 400  # Badge text weight (100-900)
    badge_bg_r: int = 255
    badge_bg_g: int = 255
    badge_bg_b: int = 255
    badge_bg_alpha: int = 100  # 0-100

    badge_text_r: int = 0
    badge_text_g: int = 0
    badge_text_b: int = 0
    badge_text_alpha: int = 100  # 0-100

    # Price change indicator settings
    indicator_enabled: bool = True
    indicator_flash_enabled: bool = True
    indicator_up_r: int = 0
    indicator_up_g: int = 255
    indicator_up_b: int = 0
    indicator_up_alpha: int = 100  # 0-100
    indicator_down_r: int = 255
    indicator_down_g: int = 0
    indicator_down_b: int = 0
    indicator_down_alpha: int = 100  # 0-100

    # Notification settings
    notifications_enabled: bool = False
    notification_threshold: float = 5.0  # Percentage change (0.1-100.0)
    notification_direction: str = "both"  # "up", "down", "both"
    notification_sound: str = "sounds/alert.mp3"  # Path to sound file (optional)
    notification_cooldown: int = 1  # Minimum minutes between notifications

    # System settings
    launch_on_startup: bool = False
    always_on_top: bool = True

    # Update settings
    update_interval: int = 60  # seconds (min 60 to avoid rate limiting)

    # API retry settings (tenacity)
    retry_attempts: int = 3
    retry_wait: int = 5  # seconds between retries

    # Window position (corner-relative)
    window_corner: str = "top_left"  # top_left, top_right, bottom_left, bottom_right
    window_offset_x: int = 100
    window_offset_y: int = 100

    @staticmethod
    def get_settings_path() -> Path:
        """Get the path to the settings file."""
        return Path.home() / "btcticker_settings.json"

    @staticmethod
    def get_cache_dir() -> Path:
        """Get the cache directory."""
        cache_dir = Path.home() / ".btcticker_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from file."""
        path = cls.get_settings_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                # Handle migration from old settings
                if "crypto_id" in data:
                    # Map old id to symbol
                    old_id = data.pop("crypto_id")
                    id_to_symbol = {
                        "bitcoin": "btc", "ethereum": "eth", "solana": "sol",
                        "cardano": "ada", "dogecoin": "doge", "ripple": "xrp",
                        "polkadot": "dot", "avalanche-2": "avax"
                    }
                    data["crypto_symbol"] = id_to_symbol.get(old_id, "btc")
                if "transparent" in data:
                    data.pop("transparent")  # Remove old field
                if "start_with_windows" in data:
                    data["launch_on_startup"] = data.pop("start_with_windows")
                # Migrate old window_x/window_y to corner-relative
                if "window_x" in data or "window_y" in data:
                    # Keep as top_left with x/y as offsets
                    data["window_corner"] = "top_left"
                    data["window_offset_x"] = data.pop("window_x", 100)
                    data["window_offset_y"] = data.pop("window_y", 100)
                # Filter out unknown fields
                valid_fields = set(cls.__dataclass_fields__.keys())
                data = {k: v for k, v in data.items() if k in valid_fields}
                return cls(**data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading settings: {e}")
        return cls()

    def save(self) -> None:
        """Save settings to file."""
        path = self.get_settings_path()
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def copy(self) -> "Settings":
        """Create a copy of settings."""
        return Settings(**asdict(self))

    def set_launch_on_startup(self, enabled: bool) -> bool:
        """Configure launch on startup (cross-platform)."""
        if sys.platform == "win32":
            return self._set_startup_windows(enabled)
        elif sys.platform == "darwin":
            return self._set_startup_macos(enabled)
        else:  # Linux and others
            return self._set_startup_linux(enabled)

    def _get_app_path(self) -> str:
        """Get the application path for startup."""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return f'"{sys.executable}" "{Path(__file__).parent / "main.py"}"'

    def _set_startup_windows(self, enabled: bool) -> bool:
        """Configure Windows registry for launch on startup."""
        try:
            import winreg
            app_path = self._get_app_path()
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "CryptoTicker"

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Windows startup error: {e}")
            return False

    def _set_startup_macos(self, enabled: bool) -> bool:
        """Configure macOS LaunchAgent for launch on startup."""
        try:
            app_path = self._get_app_path()
            plist_dir = Path.home() / "Library" / "LaunchAgents"
            plist_path = plist_dir / "com.cryptoticker.app.plist"

            if enabled:
                plist_dir.mkdir(parents=True, exist_ok=True)
                plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptoticker.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>{app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
                plist_path.write_text(plist_content)
            else:
                if plist_path.exists():
                    plist_path.unlink()
            return True
        except Exception as e:
            print(f"macOS startup error: {e}")
            return False

    def _set_startup_linux(self, enabled: bool) -> bool:
        """Configure Linux autostart desktop file."""
        try:
            app_path = self._get_app_path()
            autostart_dir = Path.home() / ".config" / "autostart"
            desktop_path = autostart_dir / "cryptoticker.desktop"

            if enabled:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                desktop_content = f'''[Desktop Entry]
Type=Application
Name=Crypto Ticker
Exec={app_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
'''
                desktop_path.write_text(desktop_content)
            else:
                if desktop_path.exists():
                    desktop_path.unlink()
            return True
        except Exception as e:
            print(f"Linux startup error: {e}")
            return False


# Font weight options
FONT_WEIGHTS = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}
