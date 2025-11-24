# Crypto Ticker

A tiny open-source desktop widget that shows cryptocurrency prices. Always visible. Always watching. For those of us who can't *not* look.

## What Is This?

This app sits on your desktop, showing the price of your chosen cryptocoins, so you can stress about market movements while pretending to work. And it does this while looking glamourous. It has lots of customizable settings make typography conscience peeps get excited.

Make the text huge and put on your desktop; or make it small and use always on top for easy glance 47 times per hour. We won't judge.

## For The Typography Nerds

For the one who has opinions about kerning... Pick any font on your system; monospaced recommended. Adjust the weight. Tweak the colors. Change the opacity until it's exactly 73% because 70% is "too transparent" and 75% is "visually heavy.

Go absolutely wild. Spend more time in the settings dialog than actually looking at prices. We built this for you. Your portfolio might be down 40%, but at least it's displayed in Helvetica Neu with a tasteful semi-transparent background and perfectly balanced badge weights...

Priorities.

## Features

- **Multiple cryptocurrencies** - Track your main coin plus others in a hover popup
- **Price change indicators** - Arrows and flash animations so you notice every movement
- **Desktop notifications** - Get alerted when prices move beyond your threshold (for extra anxiety)
- **System tray integration** - Minimize to tray, price in tooltip


## Cross-Platform

Aims to work on Windows, macOS, and Linux, no promises, yet. 

## Download It

Go to releases section for releases. Or build it yourself.

## Building

```bash
# Clone the repo
git clone https://github.com/yourusername/crypto-ticker.git
cd crypto-ticker

# Install dependencies
pip install -r requirements.txt

pip install pyinstaller
pyinstaller --onefile --windowed --icon=logo.ico main.py
```

## Contributing

Contributions are welcome! Whether it's bug fixes, new features, or just making the code less embarrassing - feel free to open issues or submit pull requests.

## License

MIT License - See [LICENSE](LICENSE).

---

*Disclaimer: This app does not promise you to make money. It will, however, ensure you're fully aware of exactly how much you're losing at any given moment.*
