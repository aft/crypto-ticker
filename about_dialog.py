"""About dialog for Crypto Ticker."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDesktopServices, QPixmap, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage

from version import __version__, __app_name__, __author__, __github__, __license__


class AboutDialog(QDialog):
    """About dialog showing app info and credits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {__app_name__}")
        self.setFixedSize(350, 300)
        self._setup_ui()

    def _get_icon_path(self) -> Path:
        """Get the path to the logo file."""
        if getattr(sys, 'frozen', False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).parent
        return app_dir / "logo.svg"

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignHCenter)

        # App icon
        icon_path = self._get_icon_path()
        if icon_path.exists():
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedSize(80, 80)
            # Render SVG to pixmap
            renderer = QSvgRenderer(str(icon_path))
            image = QImage(80, 80, QImage.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            pixmap = QPixmap.fromImage(image)
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # App name
        title = QLabel(f"{__app_name__}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Version
        version = QLabel(f"Version {__version__}")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version, alignment=Qt.AlignCenter)

        layout.addSpacing(10)

        # Author
        author_label = QLabel(f"Created by {__author__}")
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label, alignment=Qt.AlignCenter)

        # GitHub button (centered)
        github_btn = QPushButton("GitHub")
        github_btn.setFixedWidth(80)
        github_btn.setToolTip("Visit GitHub repository")
        github_btn.setCursor(Qt.PointingHandCursor)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(__github__)))
        layout.addWidget(github_btn, alignment=Qt.AlignCenter)

        # License
        license_label = QLabel(f"License: {__license__}")
        license_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_label, alignment=Qt.AlignCenter)

        layout.addSpacing(10)

        # API credit
        api_label = QLabel("Price data by")
        api_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(api_label, alignment=Qt.AlignCenter)

        coingecko_btn = QPushButton("CoinGecko")
        coingecko_btn.setFixedWidth(100)
        coingecko_btn.setToolTip("Visit CoinGecko website")
        coingecko_btn.setCursor(Qt.PointingHandCursor)
        coingecko_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.coingecko.com"))
        )
        layout.addWidget(coingecko_btn, alignment=Qt.AlignCenter)

        layout.addStretch()

        # Close button (centered)
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
