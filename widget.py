"""Transparent desktop widget for Crypto Ticker."""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QCursor, QFontDatabase
from typing import Dict

from settings import Settings
from price_popup import PricePopup
from window_position import WindowPositionManager


# Layout constants
MOVE_BUTTON_SIZE = 24          # Diameter of move button circle
MOVE_BUTTON_OVERLAP = 8       # How much the circle overlaps the pill
MOVE_BUTTON_BG_OPACITY = 0.2   # Move button background opacity (0.0 - 1.0)
MOVE_BUTTON_CORNER_RADIUS = 6  # Corner radius (half of size = circle, less = rounded square)
PADDING_H = 24                 # Horizontal padding inside pill
PADDING_V = 8                  # Vertical padding inside pill
DOT_SIZE = 2                   # Diameter of each dot
DOT_SPACING_H = 4              # Horizontal spacing between dot centers
DOT_SPACING_V = 4              # Vertical spacing between dot centers


class PriceWidget(QWidget):
    """Transparent, draggable price widget with hover effects."""

    settings_requested = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self._dragging = False
        self._drag_just_ended = False  # Prevents popup rebuild right after drag
        self._drag_start = QPoint()
        self._hovering = False
        self._hover_opacity = 0.0
        self._price_text = "Loading..."
        self._current_price = 0.0
        self._previous_price = 0.0
        self._price_direction = 0  # -1 down, 0 none, 1 up
        self._flash_progress = 0.0  # 0.0 to 1.0 for flash animation
        self._secondary_prices: Dict[str, float] = {}
        self._connection_error = False  # True when API has issues

        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        self._setup_popup()
        self._setup_position_manager()

    def _setup_window(self):
        """Configure window properties."""
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.settings.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Position will be set by position manager after UI setup

    def _setup_ui(self):
        """Set up the user interface."""
        self._price_label = QLabel(self._price_text, self)
        self._price_label.setAlignment(Qt.AlignCenter)
        # Arrow indicator label (positioned to right of price)
        self._arrow_label = QLabel("", self)
        
        # Adjustment attempt for vertical alignment of arrow with text
        font = QFont(self.settings.font_name, self.settings.font_size)
        arrow_style = f"background: transparent; padding-bottom: {font.pointSize() / 2}px;"
        self._arrow_label.setStyleSheet(arrow_style)
        
        self._arrow_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self._arrow_label.hide()  # Hidden until direction is known
        self._update_styles()
        self._resize_to_content()

    def _setup_animations(self):
        """Set up hover and flash animations."""
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(16)
        self._hover_timer.timeout.connect(self._animate_hover)

        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(16)
        self._flash_timer.timeout.connect(self._animate_flash)

    def _setup_popup(self):
        """Set up the secondary prices popup."""
        self._popup = PricePopup(self.settings)
        self._popup.set_anchor_widget(self)

    def _setup_position_manager(self):
        """Set up the window position manager."""
        self._position_manager = WindowPositionManager(self)
        self._position_manager.set_corner_position(
            self.settings.window_corner,
            self.settings.window_offset_x,
            self.settings.window_offset_y
        )
        self._position_manager.apply_position()

    def _animate_hover(self):
        """Animate hover effect."""
        target = 1.0 if self._hovering else 0.0
        diff = target - self._hover_opacity

        if abs(diff) < 0.05:
            self._hover_opacity = target
            self._hover_timer.stop()
        else:
            self._hover_opacity += diff * 0.15

        self.update()

    def _animate_flash(self):
        """Animate price flash effect."""
        # Flash fades out over time (1.0 -> 0.0)
        self._flash_progress -= 0.05

        if self._flash_progress <= 0:
            self._flash_progress = 0.0
            self._flash_timer.stop()

        self._update_price_color()
        self._price_label.repaint()  # Force immediate visual update

    def _start_flash(self):
        """Start the flash animation."""
        if self.settings.indicator_flash_enabled and self._price_direction != 0:
            self._flash_progress = 1.0
            if not self._flash_timer.isActive():
                self._flash_timer.start()
            self._update_price_color()
            self._price_label.repaint()  # Force immediate visual update

    def _get_indicator_up_color(self) -> QColor:
        """Get the up indicator color from settings."""
        return QColor(
            self.settings.indicator_up_r,
            self.settings.indicator_up_g,
            self.settings.indicator_up_b,
            int(self.settings.indicator_up_alpha * 2.55)
        )

    def _get_indicator_down_color(self) -> QColor:
        """Get the down indicator color from settings."""
        return QColor(
            self.settings.indicator_down_r,
            self.settings.indicator_down_g,
            self.settings.indicator_down_b,
            int(self.settings.indicator_down_alpha * 2.55)
        )

    def _get_text_color(self) -> QColor:
        """Get the text color from settings."""
        return QColor(
            self.settings.text_r,
            self.settings.text_g,
            self.settings.text_b,
            int(self.settings.text_alpha * 2.55)
        )

    def _get_border_color(self) -> QColor:
        """Get border color (30% of text color)."""
        color = self._get_text_color()
        color.setAlpha(int(76 * self._hover_opacity))
        return color

    def _get_bg_color(self) -> QColor:
        """Get background color - blends to text color at 10% on hover."""
        # Base: settings bg color with bg_alpha
        base_alpha = int(self.settings.bg_alpha * 2.55)

        # On hover: text color at 10% alpha (25.5 out of 255)
        hover_alpha = int(25 * self._hover_opacity)

        if self._hover_opacity > 0.01:
            # Blend towards text color on hover
            text_color = self._get_text_color()
            t = self._hover_opacity
            r = int(self.settings.bg_r * (1 - t))
            g = int(self.settings.bg_g * (1 - t))
            b = int(self.settings.bg_b * (1 - t))
            a = max(base_alpha, hover_alpha)
            return QColor(r, g, b, a)
        else:
            return QColor(
                self.settings.bg_r,
                self.settings.bg_g,
                self.settings.bg_b,
                base_alpha
            )

    def _get_icon_color(self) -> QColor:
        """Get move icon color (50% of text color)."""
        color = self._get_text_color()
        color.setAlpha(int(127 * self._hover_opacity))
        return color

    def _update_styles(self):
        """Update widget styles from settings."""
        font = QFont(self.settings.font_name, self.settings.font_size)
        font.setWeight(self._qt_font_weight(self.settings.font_weight))
        self._price_label.setFont(font)

        # Arrow uses OS default sans-serif font at same size
        arrow_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        arrow_font.setPointSize(self.settings.font_size - self.settings.font_size // 4)
        self._arrow_label.setFont(arrow_font)

        color = self._get_text_color()
        self._price_label.setStyleSheet(
            f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
            f"background: transparent;"
        )
        self._update_arrow_style()

    def _update_arrow_style(self):
        """Update arrow indicator style based on direction or connection status."""
        # Show connection error indicator if there's an issue
        if self._connection_error:
            self._arrow_label.setText("!")  # Warning indicator
            color = QColor(255, 165, 0, 255)  # Orange for warning
            self._arrow_label.setStyleSheet(
                f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
                f"background: transparent;"
            )
            self._arrow_label.raise_()
            return

        if not self.settings.indicator_enabled or self._price_direction == 0:
            self._arrow_label.setText("")
            return

        # Use Unicode arrows (U+2191 up, U+2193 down)
        if self._price_direction > 0:
            arrow_char = "\u2191"  # Up arrow
            color = self._get_indicator_up_color()
        else:
            arrow_char = "\u2193"  # Down arrow
            color = self._get_indicator_down_color()

        self._arrow_label.setText(arrow_char)
        self._arrow_label.setStyleSheet(
            f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
            f"background: transparent;"
        )
        self._arrow_label.raise_()  # Ensure arrow is on top

    def _update_price_color(self):
        """Update price label color, blending with indicator color during flash."""
        base_color = self._get_text_color()

        if self._flash_progress > 0 and self._price_direction != 0:
            # Blend base color with indicator color based on flash progress
            if self._price_direction > 0:
                flash_color = self._get_indicator_up_color()
            else:
                flash_color = self._get_indicator_down_color()

            t = self._flash_progress
            r = int(base_color.red() * (1 - t) + flash_color.red() * t)
            g = int(base_color.green() * (1 - t) + flash_color.green() * t)
            b = int(base_color.blue() * (1 - t) + flash_color.blue() * t)
            a = base_color.alpha()
            color = QColor(r, g, b, a)
        else:
            color = base_color

        self._price_label.setStyleSheet(
            f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
            f"background: transparent;"
        )

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

    def _resize_to_content(self):
        """Resize widget to fit content."""
        label_size = self._price_label.sizeHint()
        arrow_size = self._arrow_label.sizeHint()

        # Arrow width (only if has text and indicator enabled)
        has_arrow = bool(self._arrow_label.text()) and self.settings.indicator_enabled
        # Match popup's grid spacing (8px base, scaled with font)
        arrow_gap = arrow_size.width() * 0.9 if has_arrow else 0
        arrow_width = (arrow_size.width() + arrow_gap) if has_arrow else 0

        # Pill dimensions (the main price container)
        pill_width = label_size.width() + arrow_width + (PADDING_H * 2)
        pill_height = label_size.height() + (PADDING_V * 2)

        # Total widget size includes the overlapping move button
        # Move button sticks out to the left
        total_width = (MOVE_BUTTON_SIZE - MOVE_BUTTON_OVERLAP) + pill_width
        total_height = max(pill_height, MOVE_BUTTON_SIZE)

        self.setFixedSize(int(total_width), int(total_height))

        # Position price label inside the pill area
        pill_x = MOVE_BUTTON_SIZE - MOVE_BUTTON_OVERLAP
        label_x = pill_x + PADDING_H
        label_y = (total_height - label_size.height()) // 2
        self._price_label.setGeometry(
            int(label_x), int(label_y),
            label_size.width(), label_size.height()
        )

        # Position arrow label after price with gap matching popup's spacing
        if has_arrow:
            arrow_x = label_x + label_size.width() + arrow_gap
            # Vertical: center arrow relative to price label center
            label_center_y = label_y + label_size.height() // 2
            arrow_y = label_center_y - arrow_size.height() // 2 - (arrow_size.height() // 15)
            self._arrow_label.setGeometry(
                int(arrow_x), int(arrow_y),
                arrow_size.width(), arrow_size.height()
            )
            self._arrow_label.setVisible(True)
        else:
            self._arrow_label.setVisible(False)

    def set_price(self, price: float):
        """Update the displayed price."""
        # Track direction for indicator (compare with current, not previous)
        should_flash = False
        if self._current_price > 0 and price != self._current_price:
            new_direction = 1 if price > self._current_price else -1
            if new_direction != self._price_direction:
                self._price_direction = new_direction
                self._update_arrow_style()
            should_flash = True

        self._previous_price = self._current_price
        self._current_price = price

        if self.settings.show_prefix:
            prefix = self.settings.crypto_symbol.upper()
            self._price_text = f"{prefix}: ${price:,.2f}"
        else:
            self._price_text = f"${price:,.2f}"

        self._price_label.setText(self._price_text)
        self._resize_to_content()

        # Trigger flash AFTER text is set to ensure color applies correctly
        if should_flash:
            self._start_flash()

    def set_secondary_prices(self, prices: Dict[str, float]):
        """Update secondary cryptocurrency prices."""
        self._secondary_prices = prices
        self._popup.set_prices(prices)
        self._update_popup_visibility()

    def _update_popup_visibility(self):
        """Update popup visibility based on settings and state."""
        if not self._secondary_prices:
            self._popup.hide()
            return

        if self.settings.secondary_display == "always":
            self._popup.show_below_anchor()
        elif self.settings.secondary_display == "hover":
            if self._hovering:
                self._popup.show_below_anchor()
            else:
                self._popup.hide()

    def apply_settings(self, settings: Settings):
        """Apply new settings."""
        self.settings = settings
        self._update_styles()

        # Reformat price text with new settings
        if self._current_price > 0:
            self.set_price(self._current_price)
        else:
            self._resize_to_content()

        # Update always on top without recreating window
        current_flags = self.windowFlags()
        if self.settings.always_on_top:
            new_flags = current_flags | Qt.WindowStaysOnTopHint
        else:
            new_flags = current_flags & ~Qt.WindowStaysOnTopHint

        if new_flags != current_flags:
            self.setWindowFlags(new_flags)
            self.show()

        # Update popup settings
        self._popup.apply_settings(settings)
        self._update_popup_visibility()

        # Repaint to apply visual changes (background, colors)
        self.update()

    def paintEvent(self, event):
        """Custom paint for pill shape and move button."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        h = self.height()
        w = self.width()

        # Calculate positions
        move_btn_center_x = MOVE_BUTTON_SIZE / 2
        move_btn_center_y = h / 2
        move_btn_radius = MOVE_BUTTON_SIZE / 2

        pill_x = MOVE_BUTTON_SIZE - MOVE_BUTTON_OVERLAP
        pill_width = w - pill_x
        pill_height = h
        pill_radius = pill_height / 2

        # Draw pill background
        pill_rect = QRectF(pill_x + 1, 1, pill_width - 2, pill_height - 2)
        bg_color = self._get_bg_color()
        if bg_color.alpha() > 0:
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(pill_rect, pill_radius, pill_radius)

        # Draw pill border on hover
        if self._hover_opacity > 0.05:
            border_color = self._get_border_color()
            pen = QPen(border_color, 2)
            if self._dragging:
                pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(pill_rect, pill_radius, pill_radius)

        # Draw move button on hover
        if self._hover_opacity > 0.05:
            # Move button background - solid black to avoid transparency overlap
            move_bg_color = QColor(0, 0, 0, int(255 * self._hover_opacity))

            move_btn_rect = QRectF(
                move_btn_center_x - move_btn_radius,
                move_btn_center_y - move_btn_radius,
                MOVE_BUTTON_SIZE,
                MOVE_BUTTON_SIZE
            )

            painter.setBrush(QBrush(move_bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(move_btn_rect, MOVE_BUTTON_CORNER_RADIUS, MOVE_BUTTON_CORNER_RADIUS)

            # Move button border
            border_color = self._get_border_color()
            pen = QPen(border_color, 2)
            if self._dragging:
                pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(move_btn_rect, MOVE_BUTTON_CORNER_RADIUS, MOVE_BUTTON_CORNER_RADIUS)

            # Draw 6 dots (2x3 grid) centered in move button
            icon_color = self._get_icon_color()
            if icon_color.alpha() > 0:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(icon_color))

                grid_width = DOT_SPACING_H
                grid_height = DOT_SPACING_V * 2

                start_x = move_btn_center_x - grid_width / 2
                start_y = move_btn_center_y - grid_height / 2

                for row in range(3):
                    for col in range(2):
                        cx = start_x + col * DOT_SPACING_H
                        cy = start_y + row * DOT_SPACING_V
                        painter.drawEllipse(
                            QRectF(cx - DOT_SIZE/2, cy - DOT_SIZE/2, DOT_SIZE, DOT_SIZE)
                        )

        painter.end()

    def enterEvent(self, event):
        """Mouse entered widget."""
        self._hovering = True
        self._hover_timer.start()
        self._update_popup_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse left widget."""
        if not self._dragging and not self._drag_just_ended:
            self._hovering = False
            self._hover_timer.start()
            self._update_popup_visibility()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            # Check if clicking on move button area
            if event.position().x() < MOVE_BUTTON_SIZE:
                self._dragging = True
                self._drag_start = event.globalPosition().toPoint() - self.pos()
                self.setCursor(QCursor(Qt.SizeAllCursor))
                self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._drag_just_ended = True  # Prevent popup rebuild in leaveEvent
            self.setCursor(QCursor(Qt.ArrowCursor))

            # Save position (corner-relative)
            self._position_manager.set_position(self.x(), self.y())
            corner, offset_x, offset_y = self._position_manager.get_corner_position()
            self.settings.window_corner = corner
            self.settings.window_offset_x = offset_x
            self.settings.window_offset_y = offset_y
            self.settings.save()

            # Ensure popup position is finalized after drag
            self._popup.update_position()

            # Clear drag_just_ended flag after a short delay
            QTimer.singleShot(100, self._clear_drag_ended_flag)

            if not self.underMouse():
                self._hovering = False
            self._hover_timer.start()
        super().mouseReleaseEvent(event)

    def _clear_drag_ended_flag(self):
        """Clear the drag just ended flag."""
        self._drag_just_ended = False

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_start
            self.move(new_pos)
            self._popup.update_position()
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        """Right-click opens settings."""
        self.settings_requested.emit()

    def set_connection_error(self, has_error: bool):
        """Set connection error state."""
        if self._connection_error != has_error:
            self._connection_error = has_error
            self._update_arrow_style()
            self._resize_to_content()
