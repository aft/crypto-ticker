"""Custom popup widget for secondary cryptocurrency prices."""

from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QFontMetrics, QFontDatabase

from settings import Settings
from typing import Dict

# Layout constants (must match widget.py)
MOVE_BUTTON_SIZE = 24
MOVE_BUTTON_OVERLAP = 8
PADDING_H = 24
PADDING_V = 8

# Badge constants
BADGE_PADDING_H = 8  # Horizontal padding inside badge
BADGE_PADDING_V = 4  # Vertical padding inside badge
BADGE_SIZE_SCALE = 0.95  # 5% smaller badge (text and rectangle)
BADGE_RECT_SIZE_SCALE = 0.85 # 15% smaller rectangle (overall)
BADGE_CORNER_SCALE = 1.1  # 10% bigger corner radius


class SymbolBadge(QWidget):
    """A rounded rectangle badge displaying a crypto symbol."""

    def __init__(self, symbol: str, settings: Settings, target_height: int, parent=None):
        super().__init__(parent)
        self.symbol = symbol.upper()
        self.settings = settings
        self.target_height = target_height

        self.setAttribute(Qt.WA_TranslucentBackground)
        self._calculate_size()

    def _calculate_size(self):
        """Calculate badge size based on target height (5% smaller)."""
        # Apply 5% size reduction
        scaled_height = int(self.target_height * BADGE_SIZE_SCALE * BADGE_RECT_SIZE_SCALE)

        # Text font is smaller to fit with padding
        font = self._get_font()
        fm = QFontMetrics(font)

        text_width = fm.horizontalAdvance(self.symbol)

        # Badge size: text + padding, scaled down 5%
        badge_width = text_width + (BADGE_PADDING_H * 2)
        badge_height = scaled_height

        self.setFixedSize(int(badge_width), int(badge_height))

    def _get_font(self) -> QFont:
        """Get font sized to fit in badge with padding."""
        # Start with base font, scale down to fit target height with padding
        scale = max(0.1, min(3.0, self.settings.secondary_font_scale))
        base_size = max(8, int(self.settings.font_size * scale * BADGE_SIZE_SCALE))

        # Reduce font size to account for vertical padding
        scaled_height = int(self.target_height * BADGE_SIZE_SCALE)
        available_height = scaled_height - (BADGE_PADDING_V * 2)

        # Use badge-specific font and weight
        font = QFont(self.settings.badge_font_name, base_size)
        font.setWeight(self._qt_font_weight(self.settings.badge_font_weight))

        # Iteratively reduce font size until it fits
        fm = QFontMetrics(font)
        while fm.height() > available_height and font.pointSize() > 6:
            font.setPointSize(font.pointSize() - 1)
            fm = QFontMetrics(font)

        return font

    def _get_corner_radius(self) -> float:
        """Get corner radius (10% bigger than base)."""
        base_radius = min(self.width(), self.height()) / 4
        return base_radius * BADGE_CORNER_SCALE

    def _qt_font_weight(self, weight: int) -> QFont.Weight:
        """Convert numeric weight to Qt weight."""
        if weight <= 100:
            return QFont.Thin
        elif weight <= 200:
            return QFont.ExtraLight
        elif weight <= 300:
            return QFont.Light
        elif weight <= 400:
            return QFont.Normal
        elif weight <= 500:
            return QFont.Medium
        elif weight <= 600:
            return QFont.DemiBold
        elif weight <= 700:
            return QFont.Bold
        elif weight <= 800:
            return QFont.ExtraBold
        else:
            return QFont.Black

    def _get_bg_color(self) -> QColor:
        """Get badge background color."""
        return QColor(
            self.settings.badge_bg_r,
            self.settings.badge_bg_g,
            self.settings.badge_bg_b,
            int(self.settings.badge_bg_alpha * 2.55)
        )

    def _get_text_color(self) -> QColor:
        """Get badge text color."""
        return QColor(
            self.settings.badge_text_r,
            self.settings.badge_text_g,
            self.settings.badge_text_b,
            int(self.settings.badge_text_alpha * 2.55)
        )

    def paintEvent(self, event):
        """Paint the badge with rounded rectangle background and text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        corner_radius = self._get_corner_radius()

        # Draw rounded rectangle background
        bg_color = self._get_bg_color()
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect, corner_radius, corner_radius)

        # Draw text centered
        text_color = self._get_text_color()
        painter.setPen(text_color)
        font = self._get_font()
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.symbol)

        painter.end()


class PricePopup(QWidget):
    """Floating popup showing secondary crypto prices."""

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self._prices: Dict[str, float] = {}
        self._labels: list[QLabel] = []
        self._anchor_widget = None
        self._show_above = False  # Track if popup should be above anchor
        self._direction = 0  # Test direction: 1=up, -1=down, 0=none

        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Allow mouse events to pass through to main window
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def _setup_ui(self):
        """Set up the layout."""
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(PADDING_H, PADDING_V, PADDING_H, PADDING_V)
        self._layout.setHorizontalSpacing(8)
        self._layout.setVerticalSpacing(2)

    def _get_text_color(self) -> QColor:
        """Get text color from settings."""
        return QColor(
            self.settings.text_r,
            self.settings.text_g,
            self.settings.text_b,
            int(self.settings.text_alpha * 2.55)
        )

    def _get_bg_color(self) -> QColor:
        """Get background color from settings (matches main window)."""
        return QColor(
            self.settings.bg_r,
            self.settings.bg_g,
            self.settings.bg_b,
            int(self.settings.bg_alpha * 2.55)
        )

    def _get_font(self) -> QFont:
        """Get font from settings with scale applied."""
        scale = max(0.1, min(3.0, self.settings.secondary_font_scale))
        size = max(8, int(self.settings.font_size * scale))
        font = QFont(self.settings.font_name, size)
        font.setWeight(self._qt_font_weight(self.settings.font_weight))
        return font

    def _get_corner_radius(self) -> float:
        """Get corner radius equal to main window's corner radius."""
        if self._anchor_widget:
            # Main window uses pill_height / 2 = widget_height / 2
            return self._anchor_widget.height() / 2
        return self.height() / 2

    def _qt_font_weight(self, weight: int) -> QFont.Weight:
        """Convert numeric weight to Qt weight."""
        if weight <= 100:
            return QFont.Thin
        elif weight <= 200:
            return QFont.ExtraLight
        elif weight <= 300:
            return QFont.Light
        elif weight <= 400:
            return QFont.Normal
        elif weight <= 500:
            return QFont.Medium
        elif weight <= 600:
            return QFont.DemiBold
        elif weight <= 700:
            return QFont.Bold
        elif weight <= 800:
            return QFont.ExtraBold
        else:
            return QFont.Black

    def set_prices(self, prices: Dict[str, float]):
        """Update the displayed prices."""
        self._prices = prices
        self._rebuild_labels()

    def _get_arrow_color(self) -> QColor:
        """Get arrow color based on direction."""
        if self._direction > 0:
            return QColor(
                self.settings.indicator_up_r,
                self.settings.indicator_up_g,
                self.settings.indicator_up_b,
                int(self.settings.indicator_up_alpha * 2.55)
            )
        else:
            return QColor(
                self.settings.indicator_down_r,
                self.settings.indicator_down_g,
                self.settings.indicator_down_b,
                int(self.settings.indicator_down_alpha * 2.55)
            )

    def _rebuild_labels(self):
        """Rebuild price labels in aligned columns."""
        # Clear existing widgets
        for widget in self._labels:
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self._labels.clear()

        if not self._prices:
            self.hide()
            return

        font = self._get_font()
        color = self._get_text_color()
        style = f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); background: transparent;"

        # Get price label height to match badge height
        fm = QFontMetrics(font)
        target_height = fm.height()

        # Check if we should show arrows
        has_arrow = self._direction != 0 and self.settings.indicator_enabled
        arrow_char = "\u2191" if self._direction > 0 else "\u2193"
        arrow_color = self._get_arrow_color() if has_arrow else None

        row = 0
        for symbol, price in self._prices.items():
            if price > 0:
                # Symbol badge (rounded rectangle with symbol)
                badge = SymbolBadge(symbol, self.settings, target_height, self)
                self._layout.addWidget(badge, row, 0, Qt.AlignLeft | Qt.AlignVCenter)
                self._labels.append(badge)

                # Price label (right aligned)
                price_label = QLabel(f"${price:,.2f}")
                price_label.setFont(font)
                price_label.setStyleSheet(style)
                price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._layout.addWidget(price_label, row, 1)
                self._labels.append(price_label)

                if has_arrow:
                    arrow_label = QLabel(arrow_char)
                    arrow_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
                    arrow_font.setPointSize(font.pointSize() - (font.pointSize() // 4))
                    arrow_label.setFont(arrow_font)

                    # Color only, no padding in stylesheet
                    arrow_style = f"color: rgba({arrow_color.red()}, {arrow_color.green()}, {arrow_color.blue()}, {arrow_color.alpha()}); background: transparent;"
                    arrow_label.setStyleSheet(arrow_style)

                    # Vertical offset using margins (same method as widget)
                    arrow_fm = QFontMetrics(arrow_font)
                    vertical_offset = arrow_fm.height() // 10
                    arrow_label.setContentsMargins(0, 0, 0, vertical_offset)

                    arrow_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self._layout.addWidget(arrow_label, row, 2)
                    self._labels.append(arrow_label)

                row += 1

        self.adjustSize()
        # Defer reposition to after layout is complete
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._reposition)

    def apply_settings(self, settings: Settings):
        """Apply new settings."""
        self.settings = settings
        self._rebuild_labels()

    def set_anchor_widget(self, widget: QWidget):
        """Set the widget to anchor below."""
        self._anchor_widget = widget

    def _reposition(self):
        """Position popup relative to anchor widget, remembering above/below preference."""
        if not self._anchor_widget or not self._anchor_widget.isVisible():
            return

        # Get anchor widget position and size
        anchor_pos = self._anchor_widget.pos()
        anchor_size = self._anchor_widget.size()

        # Align popup text with main widget text
        pill_x = MOVE_BUTTON_SIZE - MOVE_BUTTON_OVERLAP
        x = anchor_pos.x() + pill_x

        # Check screen bounds to determine if we should be above or below
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()

            # Get actual dimensions (deferred call ensures layout is complete)
            popup_height = self.height() if self.height() > 0 else self.sizeHint().height()
            popup_width = self.width() if self.width() > 0 else self.sizeHint().width()

            # Calculate positions for both above and below
            y_below = anchor_pos.y() + anchor_size.height() + 4
            y_above = anchor_pos.y() - popup_height - 4

            # Determine if popup would fit below
            fits_below = (y_below + popup_height) <= screen_geo.bottom()
            fits_above = y_above >= screen_geo.top()

            # Only change preference when current position doesn't work
            # This makes the position "sticky" to avoid flipping on rebuild
            if self._show_above:
                # Currently showing above - only switch to below if above doesn't fit
                if not fits_above and fits_below:
                    self._show_above = False
            else:
                # Currently showing below - only switch to above if below doesn't fit
                if not fits_below and fits_above:
                    self._show_above = True

            # Apply position based on preference
            y = y_above if self._show_above else y_below

            # Keep x on screen
            if x + popup_width > screen_geo.right():
                x = screen_geo.right() - popup_width
            if x < screen_geo.left():
                x = screen_geo.left()

            self.move(x, y)
        else:
            # Fallback without screen info
            y = anchor_pos.y() + anchor_size.height() + 4
            self.move(x, y)

    def show_below_anchor(self):
        """Show popup positioned below anchor widget."""
        if not self._prices:
            return
        self._rebuild_labels()
        self.show()
        self.raise_()

    def update_position(self):
        """Update position (call when anchor moves)."""
        if self.isVisible():
            self._reposition()

    def paintEvent(self, event):
        """Paint the popup background (no border, matches main window non-hover state)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        corner_radius = self._get_corner_radius()

        # Background only (border only shows during drag on main window)
        bg_color = self._get_bg_color()
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            self.rect().adjusted(1, 1, -1, -1),
            corner_radius, corner_radius
        )

        painter.end()

    def set_direction(self, direction: int):
        """Set test direction state for all prices (for keyboard testing)."""
        # Direction: 1 = up, -1 = down, 0 = none
        self._direction = direction
        if self._prices:
            self._rebuild_labels()
