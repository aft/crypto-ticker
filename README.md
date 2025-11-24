# Crypto Ticker

A tiny desktop widget that shows cryptocurrency prices. Always visible. Always watching. For those of us who can't *not* look.

## What Is This?

You know that feeling when you close the browser tab with the charts, but then immediately open it again? This app removes the middleman. It sits on your desktop, showing the price, so you can stress about market movements while pretending to work.

It's a transparent, draggable widget that stays on top of your windows. Glance at it 47 times per hour. We don't judge.

## Features

- **Always-on-top widget** - The price follows you everywhere. No escape.
- **Multiple cryptocurrencies** - Track your main coin plus others in a hover popup
- **Price change indicators** - Arrows and flash animations so you notice every movement
- **Desktop notifications** - Get alerted when prices move beyond your threshold (for extra anxiety)
- **Fully customizable** - Fonts, colors, opacity, badge styling. Make it match your desktop aesthetic.
- **System tray integration** - Minimize to tray, price in tooltip
- **Smart positioning** - Remembers where you put it, even across resolution changes
- **Background updates** - Fetches prices without freezing. Smooth panic.
- **Launch on startup** - Because why wait to start worrying?

## Cross-Platform

Works on Windows, macOS, and Linux. Your obsession knows no operating system boundaries.

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/crypto-ticker.git
cd crypto-ticker

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Building

For a portable Windows executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=logo.ico main.py
```

## Contributing

Contributions are welcome! Whether it's bug fixes, new features, or just making the code less embarrassing - feel free to open issues or submit pull requests.

## License

MIT License - Do whatever you want with it. See [LICENSE](LICENSE) for details.

---

*Disclaimer: This app will not make you money. It will, however, ensure you're fully aware of exactly how much you're losing at any given moment.*
