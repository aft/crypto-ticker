"""Window positioning module with corner-relative positioning and resolution change handling."""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QObject, Signal, QRect
from enum import Enum
from typing import Tuple, Optional


class Corner(Enum):
    """Screen corners for relative positioning."""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class WindowPositionManager(QObject):
    """Manages window position relative to screen corners."""

    position_changed = Signal(int, int)  # x, y

    def __init__(self, widget: QWidget, parent=None):
        super().__init__(parent)
        self._widget = widget
        self._corner = Corner.TOP_LEFT
        self._offset_x = 100
        self._offset_y = 100
        self._last_screen_geometry: Optional[QRect] = None

        # Connect to screen changes
        app = QApplication.instance()
        if app:
            for screen in app.screens():
                screen.geometryChanged.connect(self._on_screen_changed)
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(self._on_screen_removed)

    def _on_screen_added(self, screen):
        """Handle new screen added."""
        screen.geometryChanged.connect(self._on_screen_changed)
        self._validate_position()

    def _on_screen_removed(self, screen):
        """Handle screen removed."""
        self._validate_position()

    def _on_screen_changed(self, geometry):
        """Handle screen geometry change."""
        self._validate_position()

    def _get_screen_geometry(self) -> QRect:
        """Get current screen geometry."""
        screen = QApplication.primaryScreen()
        if screen:
            return screen.availableGeometry()
        return QRect(0, 0, 1920, 1080)  # Fallback

    def _find_closest_corner(self, x: int, y: int) -> Tuple[Corner, int, int]:
        """Find the closest corner and calculate offset from it."""
        geo = self._get_screen_geometry()

        # Calculate distances to each corner
        corners = {
            Corner.TOP_LEFT: (x - geo.left(), y - geo.top()),
            Corner.TOP_RIGHT: (geo.right() - x - self._widget.width(), y - geo.top()),
            Corner.BOTTOM_LEFT: (x - geo.left(), geo.bottom() - y - self._widget.height()),
            Corner.BOTTOM_RIGHT: (geo.right() - x - self._widget.width(),
                                  geo.bottom() - y - self._widget.height()),
        }

        # Find corner with smallest combined offset (closest)
        closest = Corner.TOP_LEFT
        min_dist = float('inf')

        for corner, (ox, oy) in corners.items():
            dist = abs(ox) + abs(oy)
            if dist < min_dist:
                min_dist = dist
                closest = corner

        offset_x, offset_y = corners[closest]
        return closest, offset_x, offset_y

    def _calculate_absolute_position(self) -> Tuple[int, int]:
        """Calculate absolute position from corner and offset."""
        geo = self._get_screen_geometry()
        w = self._widget.width()
        h = self._widget.height()

        if self._corner == Corner.TOP_LEFT:
            x = geo.left() + self._offset_x
            y = geo.top() + self._offset_y
        elif self._corner == Corner.TOP_RIGHT:
            x = geo.right() - w - self._offset_x
            y = geo.top() + self._offset_y
        elif self._corner == Corner.BOTTOM_LEFT:
            x = geo.left() + self._offset_x
            y = geo.bottom() - h - self._offset_y
        else:  # BOTTOM_RIGHT
            x = geo.right() - w - self._offset_x
            y = geo.bottom() - h - self._offset_y

        return x, y

    def set_position(self, x: int, y: int):
        """Set position and calculate corner-relative coordinates."""
        self._corner, self._offset_x, self._offset_y = self._find_closest_corner(x, y)
        self._last_screen_geometry = self._get_screen_geometry()

    def get_corner_position(self) -> Tuple[str, int, int]:
        """Get the corner and offsets for saving."""
        return self._corner.value, self._offset_x, self._offset_y

    def set_corner_position(self, corner: str, offset_x: int, offset_y: int):
        """Set position from saved corner and offsets."""
        try:
            self._corner = Corner(corner)
        except ValueError:
            self._corner = Corner.TOP_LEFT
        self._offset_x = offset_x
        self._offset_y = offset_y

    def apply_position(self):
        """Apply the calculated position to the widget."""
        x, y = self._calculate_absolute_position()
        x, y = self._ensure_on_screen(x, y)
        self._widget.move(x, y)
        self.position_changed.emit(x, y)

    def _ensure_on_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Ensure position is within screen bounds."""
        geo = self._get_screen_geometry()
        w = self._widget.width()
        h = self._widget.height()

        # Ensure at least 50px of widget is visible
        min_visible = 50

        if x + w < geo.left() + min_visible:
            x = geo.left()
        elif x > geo.right() - min_visible:
            x = geo.right() - w

        if y + h < geo.top() + min_visible:
            y = geo.top()
        elif y > geo.bottom() - min_visible:
            y = geo.bottom() - h

        return x, y

    def _validate_position(self):
        """Validate and correct position after screen changes."""
        x, y = self._calculate_absolute_position()
        x, y = self._ensure_on_screen(x, y)

        # Update widget position
        self._widget.move(x, y)
        self.position_changed.emit(x, y)

        # Update corner-relative position based on new screen geometry
        new_geo = self._get_screen_geometry()
        if self._last_screen_geometry and new_geo != self._last_screen_geometry:
            # Recalculate corner offset for new geometry
            self._corner, self._offset_x, self._offset_y = self._find_closest_corner(x, y)
            self._last_screen_geometry = new_geo
