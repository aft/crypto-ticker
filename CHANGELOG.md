# Changelog

## [1.3.4] - 2024-11-24

### Added
- Popup is now mouse-transparent (click through to main window)

### Fixed
- Arrow indicator spacing unified between main window and popup
- Popup position now stable after price updates (deferred reposition)
- Popup no longer jumps after drag release (sticky position logic)
- Removed keyboard direction testing (was temporary debug feature)

## [1.3.3] - 2024-11-24

### Added
- Arrow indicators now appear in secondary prices popup during keyboard testing

### Fixed
- Arrow indicator positioning: added half-char horizontal gap between price and arrow
- Arrow indicator now vertically centered relative to price text

## [1.3.2] - 2024-11-23

### Added
- Background API fetching: price updates no longer freeze the UI
- Connection error indicator: shows orange "!" when API fails or is rate limited
- Keyboard testing: press Up/Down arrow keys to test direction indicator states
- Rate limit detection: handles CoinGecko's 429 errors (both HTTP status and JSON body)

### Changed
- Minimum update interval increased from 10s to 60s to avoid API rate limiting

### Fixed
- App no longer freezes during API errors or rate limiting
- Popup remains visible during connection errors

## [1.3.1] - 2024-11-23

### Changed
- Price indicator now uses Unicode arrows (U+2191, U+2193) directly after price (no space)
- Arrow indicator uses OS default sans-serif font for consistent rendering

### Fixed
- Price flash animation now works correctly (flash triggered after text update)
- Added repaint calls to ensure flash color changes are visible immediately

## [1.3.0] - 2024-11-23

### Changed
- **App renamed**: "BTC Ticker" is now "Crypto Ticker" throughout the application
- Tray icon now shows app logo instead of price (price shown in tooltip)

### Improved
- **Cross-platform icon support**: App tries ICO, PNG, then SVG formats for best compatibility
- **Cross-platform startup**: Launch on startup now works on Windows, macOS, and Linux
- About dialog logo increased to 80x80px for better visibility
- PyInstaller spec file updated with icon and data files

### Added
- Icon generation script (generate_icons.py) to create ICO/PNG from SVG
- Support for macOS LaunchAgent for startup
- Support for Linux .desktop autostart files

## [1.2.2] - 2024-11-23

### Added
- Application icon from logo.svg (cross-platform: Windows, macOS, Linux)
- App icon displayed in About dialog above app name

### Improved
- About dialog: all items now centered for cleaner appearance

## [1.2.1] - 2024-11-23

### Fixed
- Price change indicator now shows after second price update (was requiring 3 updates)
- Arrow indicator uses +/- symbols for better Windows compatibility

## [1.2.0] - 2024-11-23

### Added
- **Window Positioning Module**: Position saved relative to nearest screen corner, auto-repositions on resolution change, recovers if window goes off-screen
- **Notification Module**: Price change alerts with customizable threshold (0.1-100%), direction (up/down/both), optional sound file, and rate limiting (cooldown in minutes)
- **Price Change Indicator**: Up/down arrow next to price with customizable colors, flash animation on price change (toggle-able)
- Notifications toggle in system tray context menu
- Settings dialog reorganized: split "Main Crypto" and "Secondary Prices (Popup)" into separate groups

### Fixed
- Popup vertical position now persists correctly after drag release (stays above/below based on screen position)

### Improved
- Settings dialog layout is clearer and more organized

## [1.1.1] - 2024-11-23

### Added
- Customizable badge text weight: choose font weight for badge symbols in settings

## [1.1.0] - 2024-11-23

### Added
- Symbol badges in popup: crypto symbols now display in stylish rounded rectangles
- Customizable badge font: choose any system font for badge symbols
- Customizable badge colors: change badge background and text colors with opacity
- Default: white badge with black text for a clean, logo-like appearance

### Improved
- Badges are 5% smaller for a more refined look
- Badge corner radius 10% larger for smoother appearance

## [1.0.9] - 2024-11-23

### Added
- Symbol badges in popup (initial implementation)

## [1.0.8] - 2024-11-23

### Fixed
- Popup corner radius now exactly matches main widget corner radius

## [1.0.7] - 2024-11-23

### Improved
- Popup text now aligns with main widget text (B in BTC aligns with A in ADA)
- Popup padding matches main widget padding
- Popup no longer shows border (matches main widget non-hover state)
- Settings dialog is now more compact - no scrollbar needed

## [1.0.6] - 2024-11-23

### Improved
- Popup now aligns to left edge of main widget
- Popup corner radius matches main widget style
- Popup background and opacity now matches main widget exactly
- Secondary size setting now ranges from 0.1x to 3.0x

## [1.0.5] - 2024-11-23

### Added
- Secondary prices popup now shows below the main widget (instead of tray)
- New setting: Show secondary prices on hover or always visible
- New setting: Adjust secondary prices font size
- Popup follows widget when you drag it

## [1.0.4] - 2024-11-23

### Added
- Portable exe build support (single file, no installation needed)

## [1.0.3] - 2024-11-23

### Improved
- Price popup now uses all your settings (font, weight, colors, opacity)
- Prices aligned in columns for easier reading
- Removed redundant currency display

## [1.0.2] - 2024-11-23

### Added
- Custom styled popup for secondary crypto prices (click tray icon to show)

## [1.0.1] - 2024-11-23

### Fixed
- Settings checkboxes now save and restore correctly
- Show prefix toggle updates the widget immediately

## [1.0.0] - 2024-11-23

### Added
- Transparent desktop widget showing crypto prices
- Drag to move widget anywhere on screen
- System tray with price display
- Track multiple cryptocurrencies (secondary ones show on hover)
- Customizable fonts, colors, and opacity
- Adjustable update interval
- Pause/resume price updates from tray menu
- Auto-pause after connection issues, auto-resume after 30 minutes
- Launch on startup option
- Always on top option
- About dialog with credits
