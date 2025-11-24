"""Background worker for fetching prices without blocking UI."""

from PySide6.QtCore import QObject, Signal, QThread, QMutex
from typing import Dict, List, Optional


class PriceWorker(QObject):
    """Worker that fetches prices in a background thread."""

    # Signals
    price_fetched = Signal(float)  # Main price
    secondary_fetched = Signal(dict)  # Secondary prices {symbol: price}
    fetch_error = Signal(str)  # Error message
    fetch_success = Signal()  # Successful fetch (clears error state)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._symbol = "btc"
        self._vs_currency = "usd"
        self._secondary_symbols: List[str] = []
        self._mutex = QMutex()

    def set_config(self, symbol: str, vs_currency: str, secondary: List[str]):
        """Update fetch configuration (thread-safe)."""
        self._mutex.lock()
        self._symbol = symbol
        self._vs_currency = vs_currency
        self._secondary_symbols = secondary.copy()
        self._mutex.unlock()

    def fetch(self):
        """Fetch prices - called from worker thread."""
        from api import get_price, get_prices, get_api

        self._mutex.lock()
        symbol = self._symbol
        vs_currency = self._vs_currency
        secondary = self._secondary_symbols.copy()
        self._mutex.unlock()

        api = get_api()
        if api and api.is_paused():
            return

        try:
            # Fetch main price
            price = get_price(symbol, vs_currency)
            if price is not None:
                self.price_fetched.emit(price)
                self.fetch_success.emit()
            else:
                # Check if there was an error
                if api and api.state.last_error:
                    self.fetch_error.emit(api.state.last_error)

            # Fetch secondary prices
            if secondary:
                prices = get_prices(secondary, vs_currency)
                if prices:
                    self.secondary_fetched.emit(prices)
                elif api and api.state.last_error:
                    self.fetch_error.emit(api.state.last_error)

        except Exception as e:
            self.fetch_error.emit(str(e))


class PriceFetchThread(QThread):
    """Thread that runs price fetching."""

    def __init__(self, worker: PriceWorker, parent=None):
        super().__init__(parent)
        self._worker = worker

    def run(self):
        """Run the fetch operation."""
        self._worker.fetch()
