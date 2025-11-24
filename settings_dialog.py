"""Settings dialog for Crypto Ticker."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QSlider, QColorDialog, QFontDialog, QFileDialog,
    QWidget, QLineEdit, QCompleter, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QFontDatabase

from settings import Settings, FONT_WEIGHTS
from api import get_api


class SearchableFontComboBox(QComboBox):
    """Font combo box with search/filter capability."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

        # Get all system fonts
        font_db = QFontDatabase()
        families = font_db.families()
        self.addItems(families)

        # Setup completer for search
        completer = QCompleter(families, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.setCompleter(completer)

    def setCurrentFont(self, font: QFont):
        """Set current font by QFont object."""
        idx = self.findText(font.family())
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setEditText(font.family())

    def currentFont(self) -> QFont:
        """Get current font as QFont object."""
        return QFont(self.currentText())


class SettingsDialog(QDialog):
    """Settings dialog with live preview."""

    settings_changed = Signal(Settings)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._original_settings = settings.copy()
        self._settings = settings.copy()
        self._updating_ui = False

        self.setWindowTitle("Crypto Ticker Settings")
        self.setMinimumWidth(480)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the dialog UI with compact layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        main_layout.addWidget(self._create_font_group())
        main_layout.addWidget(self._create_color_group())
        main_layout.addWidget(self._create_crypto_group())
        main_layout.addWidget(self._create_secondary_group())
        main_layout.addWidget(self._create_indicator_group())
        main_layout.addWidget(self._create_notification_group())
        main_layout.addWidget(self._create_api_group())
        main_layout.addWidget(self._create_system_group())
        main_layout.addStretch()
        main_layout.addWidget(self._create_buttons())

    def _create_font_group(self) -> QGroupBox:
        """Create font settings group."""
        group = QGroupBox("Font")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: Font name with picker
        layout.addWidget(QLabel("Font:"), 0, 0)
        self._font_combo = SearchableFontComboBox()
        self._font_combo.currentTextChanged.connect(self._on_font_changed)
        layout.addWidget(self._font_combo, 0, 1, 1, 3)

        font_picker_btn = QPushButton("...")
        font_picker_btn.setFixedWidth(30)
        font_picker_btn.clicked.connect(self._open_font_picker)
        layout.addWidget(font_picker_btn, 0, 4)

        # Row 1: Size and Weight on same row
        layout.addWidget(QLabel("Size:"), 1, 0)
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 200)
        self._font_size.valueChanged.connect(self._on_font_size_changed)
        layout.addWidget(self._font_size, 1, 1)

        layout.addWidget(QLabel("Weight:"), 1, 2)
        self._font_weight = QComboBox()
        for name in FONT_WEIGHTS.keys():
            self._font_weight.addItem(name)
        self._font_weight.currentTextChanged.connect(self._on_font_weight_changed)
        layout.addWidget(self._font_weight, 1, 3, 1, 2)

        return group

    def _create_color_group(self) -> QGroupBox:
        """Create color settings group."""
        group = QGroupBox("Colors")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("Text Color:"), 0, 0)
        self._text_color_btn = QPushButton()
        self._text_color_btn.setFixedSize(60, 25)
        self._text_color_btn.clicked.connect(self._pick_text_color)
        layout.addWidget(self._text_color_btn, 0, 1)

        layout.addWidget(QLabel("Opacity:"), 0, 2)
        self._text_alpha = QSlider(Qt.Horizontal)
        self._text_alpha.setRange(0, 100)
        self._text_alpha.valueChanged.connect(self._on_text_alpha_changed)
        layout.addWidget(self._text_alpha, 0, 3)
        self._text_alpha_label = QLabel("100%")
        layout.addWidget(self._text_alpha_label, 0, 4)

        layout.addWidget(QLabel("Background:"), 1, 0)
        self._bg_color_btn = QPushButton()
        self._bg_color_btn.setFixedSize(60, 25)
        self._bg_color_btn.clicked.connect(self._pick_bg_color)
        layout.addWidget(self._bg_color_btn, 1, 1)

        layout.addWidget(QLabel("Opacity:"), 1, 2)
        self._bg_alpha = QSlider(Qt.Horizontal)
        self._bg_alpha.setRange(0, 100)
        self._bg_alpha.valueChanged.connect(self._on_bg_alpha_changed)
        layout.addWidget(self._bg_alpha, 1, 3)
        self._bg_alpha_label = QLabel("0%")
        layout.addWidget(self._bg_alpha_label, 1, 4)

        return group

    def _create_crypto_group(self) -> QGroupBox:
        """Create main crypto settings group."""
        group = QGroupBox("Main Crypto")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: Main crypto and Currency on same row
        layout.addWidget(QLabel("Crypto:"), 0, 0)
        self._crypto_combo = QComboBox()
        self._crypto_combo.setEditable(True)
        self._load_crypto_options()
        self._crypto_combo.currentTextChanged.connect(self._on_crypto_changed)
        layout.addWidget(self._crypto_combo, 0, 1)

        layout.addWidget(QLabel("Currency:"), 0, 2)
        self._currency_combo = QComboBox()
        self._load_currency_options()
        self._currency_combo.currentTextChanged.connect(self._on_currency_changed)
        layout.addWidget(self._currency_combo, 0, 3)

        # Row 1: Show prefix checkbox
        self._show_prefix = QCheckBox("Show prefix (e.g., BTC:)")
        self._show_prefix.stateChanged.connect(self._on_show_prefix_changed)
        layout.addWidget(self._show_prefix, 1, 0, 1, 4)

        return group

    def _create_secondary_group(self) -> QGroupBox:
        """Create secondary prices popup settings group."""
        group = QGroupBox("Secondary Prices (Popup)")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: Secondary cryptos
        layout.addWidget(QLabel("Coins:"), 0, 0)
        self._secondary_cryptos = QLineEdit()
        self._secondary_cryptos.setPlaceholderText("eth, sol, ada")
        self._secondary_cryptos.textChanged.connect(self._on_secondary_changed)
        layout.addWidget(self._secondary_cryptos, 0, 1, 1, 3)

        # Row 1: Display and Size on same row
        layout.addWidget(QLabel("Display:"), 1, 0)
        self._secondary_display = QComboBox()
        self._secondary_display.addItem("On Hover", "hover")
        self._secondary_display.addItem("Always", "always")
        self._secondary_display.currentIndexChanged.connect(self._on_secondary_display_changed)
        layout.addWidget(self._secondary_display, 1, 1)

        layout.addWidget(QLabel("Size:"), 1, 2)
        size_layout = QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)
        self._secondary_font_scale = QSlider(Qt.Horizontal)
        self._secondary_font_scale.setRange(10, 300)
        self._secondary_font_scale.valueChanged.connect(self._on_secondary_font_scale_changed)
        size_layout.addWidget(self._secondary_font_scale)
        self._secondary_font_scale_label = QLabel("0.7x")
        self._secondary_font_scale_label.setFixedWidth(32)
        size_layout.addWidget(self._secondary_font_scale_label)
        layout.addLayout(size_layout, 1, 3)

        # Row 2: Badge font and weight on same row
        layout.addWidget(QLabel("Badge Font:"), 2, 0)
        self._badge_font_combo = SearchableFontComboBox()
        self._badge_font_combo.currentTextChanged.connect(self._on_badge_font_changed)
        layout.addWidget(self._badge_font_combo, 2, 1)

        layout.addWidget(QLabel("Weight:"), 2, 2)
        self._badge_font_weight = QComboBox()
        for name in FONT_WEIGHTS.keys():
            self._badge_font_weight.addItem(name)
        self._badge_font_weight.currentTextChanged.connect(self._on_badge_font_weight_changed)
        layout.addWidget(self._badge_font_weight, 2, 3)

        # Row 3: Badge colors (background and text on same row)
        layout.addWidget(QLabel("Badge BG:"), 3, 0)
        badge_bg_layout = QHBoxLayout()
        badge_bg_layout.setContentsMargins(0, 0, 0, 0)
        self._badge_bg_btn = QPushButton()
        self._badge_bg_btn.setFixedSize(40, 20)
        self._badge_bg_btn.clicked.connect(self._pick_badge_bg_color)
        badge_bg_layout.addWidget(self._badge_bg_btn)
        self._badge_bg_alpha = QSlider(Qt.Horizontal)
        self._badge_bg_alpha.setRange(0, 100)
        self._badge_bg_alpha.valueChanged.connect(self._on_badge_bg_alpha_changed)
        badge_bg_layout.addWidget(self._badge_bg_alpha)
        layout.addLayout(badge_bg_layout, 3, 1)

        layout.addWidget(QLabel("Badge Text:"), 3, 2)
        badge_text_layout = QHBoxLayout()
        badge_text_layout.setContentsMargins(0, 0, 0, 0)
        self._badge_text_btn = QPushButton()
        self._badge_text_btn.setFixedSize(40, 20)
        self._badge_text_btn.clicked.connect(self._pick_badge_text_color)
        badge_text_layout.addWidget(self._badge_text_btn)
        self._badge_text_alpha = QSlider(Qt.Horizontal)
        self._badge_text_alpha.setRange(0, 100)
        self._badge_text_alpha.valueChanged.connect(self._on_badge_text_alpha_changed)
        badge_text_layout.addWidget(self._badge_text_alpha)
        layout.addLayout(badge_text_layout, 3, 3)

        return group

    def _create_indicator_group(self) -> QGroupBox:
        """Create price change indicator settings group."""
        group = QGroupBox("Price Change Indicator")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: Enable checkbox and flash toggle
        self._indicator_enabled = QCheckBox("Show arrow indicator")
        self._indicator_enabled.stateChanged.connect(self._on_indicator_enabled_changed)
        layout.addWidget(self._indicator_enabled, 0, 0, 1, 2)

        self._indicator_flash_enabled = QCheckBox("Flash price on change")
        self._indicator_flash_enabled.stateChanged.connect(self._on_indicator_flash_changed)
        layout.addWidget(self._indicator_flash_enabled, 0, 2, 1, 2)

        # Row 1: Up color and Down color
        layout.addWidget(QLabel("Up Color:"), 1, 0)
        up_layout = QHBoxLayout()
        up_layout.setContentsMargins(0, 0, 0, 0)
        self._indicator_up_btn = QPushButton()
        self._indicator_up_btn.setFixedSize(40, 20)
        self._indicator_up_btn.clicked.connect(self._pick_indicator_up_color)
        up_layout.addWidget(self._indicator_up_btn)
        self._indicator_up_alpha = QSlider(Qt.Horizontal)
        self._indicator_up_alpha.setRange(0, 100)
        self._indicator_up_alpha.valueChanged.connect(self._on_indicator_up_alpha_changed)
        up_layout.addWidget(self._indicator_up_alpha)
        layout.addLayout(up_layout, 1, 1)

        layout.addWidget(QLabel("Down Color:"), 1, 2)
        down_layout = QHBoxLayout()
        down_layout.setContentsMargins(0, 0, 0, 0)
        self._indicator_down_btn = QPushButton()
        self._indicator_down_btn.setFixedSize(40, 20)
        self._indicator_down_btn.clicked.connect(self._pick_indicator_down_color)
        down_layout.addWidget(self._indicator_down_btn)
        self._indicator_down_alpha = QSlider(Qt.Horizontal)
        self._indicator_down_alpha.setRange(0, 100)
        self._indicator_down_alpha.valueChanged.connect(self._on_indicator_down_alpha_changed)
        down_layout.addWidget(self._indicator_down_alpha)
        layout.addLayout(down_layout, 1, 3)

        return group

    def _create_notification_group(self) -> QGroupBox:
        """Create notification settings group."""
        group = QGroupBox("Notifications")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: Enable checkbox and direction
        self._notifications_enabled = QCheckBox("Enable price alerts")
        self._notifications_enabled.stateChanged.connect(self._on_notifications_enabled_changed)
        layout.addWidget(self._notifications_enabled, 0, 0, 1, 2)

        layout.addWidget(QLabel("Direction:"), 0, 2)
        self._notification_direction = QComboBox()
        self._notification_direction.addItem("Up", "up")
        self._notification_direction.addItem("Down", "down")
        self._notification_direction.addItem("Both", "both")
        self._notification_direction.currentIndexChanged.connect(self._on_notification_direction_changed)
        layout.addWidget(self._notification_direction, 0, 3)

        # Row 1: Threshold and cooldown
        layout.addWidget(QLabel("Threshold:"), 1, 0)
        threshold_layout = QHBoxLayout()
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        self._notification_threshold = QDoubleSpinBox()
        self._notification_threshold.setRange(0.1, 100.0)
        self._notification_threshold.setSingleStep(0.5)
        self._notification_threshold.setSuffix("%")
        self._notification_threshold.valueChanged.connect(self._on_notification_threshold_changed)
        threshold_layout.addWidget(self._notification_threshold)
        layout.addLayout(threshold_layout, 1, 1)

        layout.addWidget(QLabel("Cooldown:"), 1, 2)
        cooldown_layout = QHBoxLayout()
        cooldown_layout.setContentsMargins(0, 0, 0, 0)
        self._notification_cooldown = QSpinBox()
        self._notification_cooldown.setRange(1, 60)
        self._notification_cooldown.setSuffix(" min")
        self._notification_cooldown.valueChanged.connect(self._on_notification_cooldown_changed)
        cooldown_layout.addWidget(self._notification_cooldown)
        layout.addLayout(cooldown_layout, 1, 3)

        # Row 2: Sound file
        layout.addWidget(QLabel("Sound:"), 2, 0)
        sound_layout = QHBoxLayout()
        sound_layout.setContentsMargins(0, 0, 0, 0)
        self._notification_sound = QLineEdit()
        self._notification_sound.setPlaceholderText("sounds/alert.mp3")
        self._notification_sound.textChanged.connect(self._on_notification_sound_changed)
        sound_layout.addWidget(self._notification_sound)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse_notification_sound)
        sound_layout.addWidget(browse_btn)
        layout.addLayout(sound_layout, 2, 1, 1, 3)

        return group

    def _create_api_group(self) -> QGroupBox:
        """Create API settings group."""
        group = QGroupBox("API Settings")
        layout = QGridLayout(group)

        # Row 0: Update interval
        layout.addWidget(QLabel("Update:"), 0, 0)
        self._update_interval = QSpinBox()
        self._update_interval.setRange(60, 3600)
        self._update_interval.setSuffix("s")
        self._update_interval.valueChanged.connect(self._on_interval_changed)
        layout.addWidget(self._update_interval, 0, 1)

        # Row 0: Retry attempts and wait on same row
        layout.addWidget(QLabel("Retries:"), 0, 2)
        self._retry_attempts = QSpinBox()
        self._retry_attempts.setRange(1, 10)
        self._retry_attempts.valueChanged.connect(self._on_retry_attempts_changed)
        layout.addWidget(self._retry_attempts, 0, 3)

        layout.addWidget(QLabel("Wait:"), 0, 4)
        self._retry_wait = QSpinBox()
        self._retry_wait.setRange(1, 60)
        self._retry_wait.setSuffix("s")
        self._retry_wait.valueChanged.connect(self._on_retry_wait_changed)
        layout.addWidget(self._retry_wait, 0, 5)

        return group

    def _create_system_group(self) -> QGroupBox:
        """Create system settings group."""
        group = QGroupBox("System")
        layout = QHBoxLayout(group)

        self._always_on_top = QCheckBox("Always on top")
        self._always_on_top.stateChanged.connect(self._on_always_on_top_changed)
        layout.addWidget(self._always_on_top)

        self._launch_on_startup = QCheckBox("Launch on startup")
        self._launch_on_startup.stateChanged.connect(self._on_launch_on_startup_changed)
        layout.addWidget(self._launch_on_startup)

        layout.addStretch()

        return group

    def _create_buttons(self) -> QWidget:
        """Create dialog buttons."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        return widget

    def _load_crypto_options(self):
        """Load crypto options from API or defaults."""
        api = get_api()
        default_symbols = ["btc", "eth", "sol", "ada", "doge", "xrp", "dot", "avax"]

        if api:
            coin_list = api.get_coin_list()
            # Add top coins first
            for sym in default_symbols:
                self._crypto_combo.addItem(sym.upper(), sym)
            # Add some popular others
            added = set(default_symbols)
            for coin in coin_list[:100]:
                sym = coin.get("symbol", "").lower()
                if sym and sym not in added:
                    self._crypto_combo.addItem(f"{sym.upper()} - {coin.get('name', '')}", sym)
                    added.add(sym)
        else:
            for sym in default_symbols:
                self._crypto_combo.addItem(sym.upper(), sym)

    def _load_currency_options(self):
        """Load currency options from API or defaults."""
        api = get_api()
        default_currencies = ["usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "cny"]

        if api:
            currencies = api.get_supported_currencies()
            for curr in currencies:
                self._currency_combo.addItem(curr.upper(), curr)
        else:
            for curr in default_currencies:
                self._currency_combo.addItem(curr.upper(), curr)

    def _load_settings(self):
        """Load settings into UI controls."""
        self._updating_ui = True

        # Font
        self._font_combo.setCurrentFont(QFont(self._settings.font_name))
        self._font_size.setValue(self._settings.font_size)

        weight_name = "Bold"
        for name, value in FONT_WEIGHTS.items():
            if value == self._settings.font_weight:
                weight_name = name
                break
        self._font_weight.setCurrentText(weight_name)

        # Colors
        self._update_color_button(
            self._text_color_btn,
            QColor(self._settings.text_r, self._settings.text_g, self._settings.text_b)
        )
        self._text_alpha.setValue(self._settings.text_alpha)
        self._text_alpha_label.setText(f"{self._settings.text_alpha}%")

        self._update_color_button(
            self._bg_color_btn,
            QColor(self._settings.bg_r, self._settings.bg_g, self._settings.bg_b)
        )
        self._bg_alpha.setValue(self._settings.bg_alpha)
        self._bg_alpha_label.setText(f"{self._settings.bg_alpha}%")

        # Crypto
        idx = self._crypto_combo.findData(self._settings.crypto_symbol)
        if idx >= 0:
            self._crypto_combo.setCurrentIndex(idx)
        else:
            self._crypto_combo.setEditText(self._settings.crypto_symbol.upper())

        idx = self._currency_combo.findData(self._settings.vs_currency)
        if idx >= 0:
            self._currency_combo.setCurrentIndex(idx)

        self._show_prefix.setChecked(self._settings.show_prefix)
        self._secondary_cryptos.setText(",".join(self._settings.secondary_cryptos))

        idx = self._secondary_display.findData(self._settings.secondary_display)
        if idx >= 0:
            self._secondary_display.setCurrentIndex(idx)

        scale_int = int(self._settings.secondary_font_scale * 100)
        self._secondary_font_scale.setValue(scale_int)
        self._secondary_font_scale_label.setText(f"{self._settings.secondary_font_scale:.1f}x")

        # Badge font, weight, and colors
        self._badge_font_combo.setCurrentFont(QFont(self._settings.badge_font_name))

        badge_weight_name = "Regular"
        for name, value in FONT_WEIGHTS.items():
            if value == self._settings.badge_font_weight:
                badge_weight_name = name
                break
        self._badge_font_weight.setCurrentText(badge_weight_name)

        self._update_color_button(
            self._badge_bg_btn,
            QColor(self._settings.badge_bg_r, self._settings.badge_bg_g, self._settings.badge_bg_b)
        )
        self._badge_bg_alpha.setValue(self._settings.badge_bg_alpha)

        self._update_color_button(
            self._badge_text_btn,
            QColor(self._settings.badge_text_r, self._settings.badge_text_g, self._settings.badge_text_b)
        )
        self._badge_text_alpha.setValue(self._settings.badge_text_alpha)

        # Indicator
        self._indicator_enabled.setChecked(self._settings.indicator_enabled)
        self._indicator_flash_enabled.setChecked(self._settings.indicator_flash_enabled)
        self._update_color_button(
            self._indicator_up_btn,
            QColor(self._settings.indicator_up_r, self._settings.indicator_up_g, self._settings.indicator_up_b)
        )
        self._indicator_up_alpha.setValue(self._settings.indicator_up_alpha)
        self._update_color_button(
            self._indicator_down_btn,
            QColor(self._settings.indicator_down_r, self._settings.indicator_down_g, self._settings.indicator_down_b)
        )
        self._indicator_down_alpha.setValue(self._settings.indicator_down_alpha)

        # Notifications
        self._notifications_enabled.setChecked(self._settings.notifications_enabled)
        self._notification_threshold.setValue(self._settings.notification_threshold)
        idx = self._notification_direction.findData(self._settings.notification_direction)
        if idx >= 0:
            self._notification_direction.setCurrentIndex(idx)
        self._notification_cooldown.setValue(self._settings.notification_cooldown)
        self._notification_sound.setText(self._settings.notification_sound)
        self._update_notification_controls_state()

        # API
        self._update_interval.setValue(self._settings.update_interval)
        self._retry_attempts.setValue(self._settings.retry_attempts)
        self._retry_wait.setValue(self._settings.retry_wait)

        # System
        self._always_on_top.setChecked(self._settings.always_on_top)
        self._launch_on_startup.setChecked(self._settings.launch_on_startup)

        self._updating_ui = False

    def _update_color_button(self, button: QPushButton, color: QColor):
        """Update a color button's background."""
        button.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()});"
        )

    def _emit_changes(self):
        """Emit settings changed signal for live preview."""
        if not self._updating_ui:
            self.settings_changed.emit(self._settings.copy())

    # Individual change handlers
    def _on_font_changed(self, font_name: str):
        if not self._updating_ui:
            self._settings.font_name = font_name
            self._emit_changes()

    def _on_font_size_changed(self, value: int):
        if not self._updating_ui:
            self._settings.font_size = value
            self._emit_changes()

    def _on_font_weight_changed(self, name: str):
        if not self._updating_ui:
            self._settings.font_weight = FONT_WEIGHTS.get(name, 700)
            self._emit_changes()

    def _on_text_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.text_alpha = value
            self._text_alpha_label.setText(f"{value}%")
            self._emit_changes()

    def _on_bg_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.bg_alpha = value
            self._bg_alpha_label.setText(f"{value}%")
            self._emit_changes()

    def _on_crypto_changed(self, text: str):
        if not self._updating_ui:
            # Extract symbol from "SYM - Name" format or use as-is
            sym = text.split(" - ")[0].strip().lower() if " - " in text else text.lower()
            self._settings.crypto_symbol = sym
            self._emit_changes()

    def _on_currency_changed(self, text: str):
        if not self._updating_ui:
            self._settings.vs_currency = text.lower()
            self._emit_changes()

    def _on_show_prefix_changed(self, state):
        if not self._updating_ui:
            self._settings.show_prefix = self._show_prefix.isChecked()
            self._emit_changes()

    def _on_secondary_changed(self, text: str):
        if not self._updating_ui:
            symbols = [s.strip().lower() for s in text.split(",") if s.strip()]
            self._settings.secondary_cryptos = symbols
            self._emit_changes()

    def _on_secondary_display_changed(self, index: int):
        if not self._updating_ui:
            self._settings.secondary_display = self._secondary_display.currentData()
            self._emit_changes()

    def _on_secondary_font_scale_changed(self, value: int):
        if not self._updating_ui:
            scale = value / 100.0  # Convert to 0.1-3.0 range
            self._settings.secondary_font_scale = scale
            self._secondary_font_scale_label.setText(f"{scale:.1f}x")
            self._emit_changes()

    def _on_badge_font_changed(self, font_name: str):
        if not self._updating_ui:
            self._settings.badge_font_name = font_name
            self._emit_changes()

    def _on_badge_font_weight_changed(self, name: str):
        if not self._updating_ui:
            self._settings.badge_font_weight = FONT_WEIGHTS.get(name, 400)
            self._emit_changes()

    def _on_badge_bg_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.badge_bg_alpha = value
            self._emit_changes()

    def _on_badge_text_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.badge_text_alpha = value
            self._emit_changes()

    def _pick_badge_bg_color(self):
        """Open color picker for badge background."""
        current = QColor(self._settings.badge_bg_r, self._settings.badge_bg_g, self._settings.badge_bg_b)
        color = QColorDialog.getColor(current, self, "Select Badge Background")
        if color.isValid():
            self._settings.badge_bg_r = color.red()
            self._settings.badge_bg_g = color.green()
            self._settings.badge_bg_b = color.blue()
            self._update_color_button(self._badge_bg_btn, color)
            self._emit_changes()

    def _pick_badge_text_color(self):
        """Open color picker for badge text."""
        current = QColor(self._settings.badge_text_r, self._settings.badge_text_g, self._settings.badge_text_b)
        color = QColorDialog.getColor(current, self, "Select Badge Text Color")
        if color.isValid():
            self._settings.badge_text_r = color.red()
            self._settings.badge_text_g = color.green()
            self._settings.badge_text_b = color.blue()
            self._update_color_button(self._badge_text_btn, color)
            self._emit_changes()

    def _on_interval_changed(self, value: int):
        if not self._updating_ui:
            self._settings.update_interval = value
            self._emit_changes()

    def _on_retry_attempts_changed(self, value: int):
        if not self._updating_ui:
            self._settings.retry_attempts = value
            self._emit_changes()

    def _on_retry_wait_changed(self, value: int):
        if not self._updating_ui:
            self._settings.retry_wait = value
            self._emit_changes()

    def _on_always_on_top_changed(self, state):
        if not self._updating_ui:
            self._settings.always_on_top = self._always_on_top.isChecked()
            self._emit_changes()

    def _on_launch_on_startup_changed(self, state):
        if not self._updating_ui:
            self._settings.launch_on_startup = self._launch_on_startup.isChecked()
            self._emit_changes()

    def _on_indicator_enabled_changed(self, state):
        if not self._updating_ui:
            self._settings.indicator_enabled = self._indicator_enabled.isChecked()
            self._emit_changes()

    def _on_indicator_flash_changed(self, state):
        if not self._updating_ui:
            self._settings.indicator_flash_enabled = self._indicator_flash_enabled.isChecked()
            self._emit_changes()

    def _on_indicator_up_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.indicator_up_alpha = value
            self._emit_changes()

    def _on_indicator_down_alpha_changed(self, value: int):
        if not self._updating_ui:
            self._settings.indicator_down_alpha = value
            self._emit_changes()

    def _pick_indicator_up_color(self):
        """Open color picker for up indicator color."""
        current = QColor(self._settings.indicator_up_r, self._settings.indicator_up_g, self._settings.indicator_up_b)
        color = QColorDialog.getColor(current, self, "Select Up Color")
        if color.isValid():
            self._settings.indicator_up_r = color.red()
            self._settings.indicator_up_g = color.green()
            self._settings.indicator_up_b = color.blue()
            self._update_color_button(self._indicator_up_btn, color)
            self._emit_changes()

    def _pick_indicator_down_color(self):
        """Open color picker for down indicator color."""
        current = QColor(self._settings.indicator_down_r, self._settings.indicator_down_g, self._settings.indicator_down_b)
        color = QColorDialog.getColor(current, self, "Select Down Color")
        if color.isValid():
            self._settings.indicator_down_r = color.red()
            self._settings.indicator_down_g = color.green()
            self._settings.indicator_down_b = color.blue()
            self._update_color_button(self._indicator_down_btn, color)
            self._emit_changes()

    def _update_notification_controls_state(self):
        """Enable/disable notification controls based on enabled state."""
        enabled = self._notifications_enabled.isChecked()
        self._notification_threshold.setEnabled(enabled)
        self._notification_direction.setEnabled(enabled)
        self._notification_cooldown.setEnabled(enabled)
        self._notification_sound.setEnabled(enabled)

    def _on_notifications_enabled_changed(self, state):
        if not self._updating_ui:
            self._settings.notifications_enabled = self._notifications_enabled.isChecked()
            self._update_notification_controls_state()
            self._emit_changes()

    def _on_notification_threshold_changed(self, value: float):
        if not self._updating_ui:
            self._settings.notification_threshold = value
            self._emit_changes()

    def _on_notification_direction_changed(self, index: int):
        if not self._updating_ui:
            self._settings.notification_direction = self._notification_direction.currentData()
            self._emit_changes()

    def _on_notification_cooldown_changed(self, value: int):
        if not self._updating_ui:
            self._settings.notification_cooldown = value
            self._emit_changes()

    def _on_notification_sound_changed(self, text: str):
        if not self._updating_ui:
            self._settings.notification_sound = text
            self._emit_changes()

    def _browse_notification_sound(self):
        """Open file dialog to select notification sound."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Notification Sound",
            "", "Audio Files (*.mp3 *.wav *.ogg);;All Files (*)"
        )
        if file_path:
            self._notification_sound.setText(file_path)

    def _open_font_picker(self):
        """Open the system font picker dialog."""
        current_font = QFont(self._settings.font_name, self._settings.font_size)
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            self._updating_ui = True
            self._font_combo.setCurrentFont(font)
            self._font_size.setValue(font.pointSize())
            self._updating_ui = False

            self._settings.font_name = font.family()
            self._settings.font_size = font.pointSize()
            self._emit_changes()

    def _pick_text_color(self):
        """Open color picker for text color."""
        current = QColor(self._settings.text_r, self._settings.text_g, self._settings.text_b)
        color = QColorDialog.getColor(current, self, "Select Text Color")
        if color.isValid():
            self._settings.text_r = color.red()
            self._settings.text_g = color.green()
            self._settings.text_b = color.blue()
            self._update_color_button(self._text_color_btn, color)
            self._emit_changes()

    def _pick_bg_color(self):
        """Open color picker for background color."""
        current = QColor(self._settings.bg_r, self._settings.bg_g, self._settings.bg_b)
        color = QColorDialog.getColor(current, self, "Select Background Color")
        if color.isValid():
            self._settings.bg_r = color.red()
            self._settings.bg_g = color.green()
            self._settings.bg_b = color.blue()
            self._update_color_button(self._bg_color_btn, color)
            self._emit_changes()

    def _on_cancel(self):
        """Cancel and restore original settings."""
        self.settings_changed.emit(self._original_settings.copy())
        self.reject()

    def _on_save(self):
        """Save settings and close."""
        # Apply launch on startup to registry
        self._settings.set_launch_on_startup(self._settings.launch_on_startup)
        self._settings.save()
        self.accept()

    def get_settings(self) -> Settings:
        """Get the current settings."""
        return self._settings.copy()
