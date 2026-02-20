"""CryptoCompare API integration with caching and retry logic."""

import json
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


@dataclass
class APIState:
    """Tracks API state for pause/resume functionality."""
    paused: bool = False
    consecutive_failures: int = 0
    auto_pause_until: Optional[float] = None
    last_error: Optional[str] = None

    def should_skip(self) -> bool:
        """Check if API calls should be skipped."""
        if self.paused:
            return True
        if self.auto_pause_until and time.time() < self.auto_pause_until:
            return True
        return False

    def record_failure(self, error: str):
        """Record a failure and check for auto-pause."""
        self.consecutive_failures += 1
        self.last_error = error
        if self.consecutive_failures >= 10:
            # Auto-pause for 30 minutes
            self.auto_pause_until = time.time() + (30 * 60)

    def record_success(self):
        """Record a successful call."""
        self.consecutive_failures = 0
        self.last_error = None

    def resume(self):
        """Resume API calls."""
        self.paused = False
        self.auto_pause_until = None
        self.consecutive_failures = 0

    def get_auto_resume_remaining(self) -> Optional[int]:
        """Get seconds until auto-resume, or None if not auto-paused."""
        if self.auto_pause_until:
            remaining = self.auto_pause_until - time.time()
            return max(0, int(remaining))
        return None


class CryptoAPI:
    """CryptoCompare API client with caching and retry logic."""

    BASE_URL = "https://min-api.cryptocompare.com/data"
    CACHE_DURATION = timedelta(hours=24)

    # CryptoCompare supports these common fiat currencies
    SUPPORTED_CURRENCIES = [
        "usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "cny",
        "krw", "rub", "inr", "brl", "zar", "mxn", "sgd", "hkd",
        "nok", "sek", "dkk", "pln", "czk", "huf", "ils", "try",
        "thb", "php", "idr", "myr", "nzd", "twd", "aed", "ars",
        "clp", "cop", "egp", "ngn", "pkr", "sar", "uah", "vnd",
    ]

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.state = APIState()

        # Retry configuration (will be updated from settings)
        self.retry_attempts = 3
        self.retry_wait = 5

        # Callbacks for state changes
        self.on_state_change: Optional[Callable[[APIState], None]] = None

    def _get_cache_path(self, name: str) -> Path:
        """Get path for a cache file."""
        return self.cache_dir / f"{name}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < self.CACHE_DURATION

    def _load_cache(self, name: str) -> Optional[dict]:
        """Load data from cache if valid."""
        cache_path = self._get_cache_path(name)
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def _save_cache(self, name: str, data):
        """Save data to cache."""
        cache_path = self._get_cache_path(name)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except IOError:
            pass

    def _notify_state_change(self):
        """Notify listeners of state change."""
        if self.on_state_change:
            self.on_state_change(self.state)

    def _make_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make an API request with retry logic."""
        if self.state.should_skip():
            return None

        # Create retry decorator with current settings
        @retry(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_fixed(self.retry_wait),
            retry=retry_if_exception_type(requests.RequestException),
            reraise=True
        )
        def do_request():
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 429:
                raise RateLimitError("Rate limited by API")
            response.raise_for_status()
            data = response.json()
            # CryptoCompare error responses
            if isinstance(data, dict) and data.get("Response") == "Error":
                msg = data.get("Message", "API error")
                if "rate limit" in msg.lower():
                    raise RateLimitError(msg)
            return data

        try:
            result = do_request()
            self.state.record_success()
            self._notify_state_change()
            return result
        except RateLimitError as e:
            self.state.record_failure(f"Rate limited: {e}")
            self._notify_state_change()
            return None
        except Exception as e:
            self.state.record_failure(str(e))
            self._notify_state_change()
            return None

    def get_supported_currencies(self) -> List[str]:
        """Get list of supported vs currencies."""
        return list(self.SUPPORTED_CURRENCIES)

    def get_coin_list(self) -> List[Dict]:
        """Get list of all coins (cached 24h).

        Returns list of dicts with 'symbol' and 'name' keys,
        matching the format expected by settings_dialog.
        """
        cached = self._load_cache("coin_list")
        if cached:
            return cached

        url = f"{self.BASE_URL}/all/coinlist"
        data = self._make_request(url, {"summary": "true"})
        if data and "Data" in data:
            coins = []
            for sym, info in data["Data"].items():
                full_name = info.get("FullName", sym)
                # Extract just the name part from "Name (SYM)" format
                name = full_name.split("(")[0].strip() if "(" in full_name else full_name
                coins.append({
                    "symbol": info.get("Symbol", sym).lower(),
                    "name": name,
                })
            self._save_cache("coin_list", coins)
            return coins
        # Return default coins if API fails
        return [
            {"symbol": "btc", "name": "Bitcoin"},
            {"symbol": "eth", "name": "Ethereum"},
        ]

    def get_prices(self, symbols: List[str], vs_currency: str) -> Dict[str, float]:
        """
        Get prices for multiple cryptocurrencies by symbol.

        Args:
            symbols: List of crypto symbols (e.g., ['btc', 'eth'])
            vs_currency: Target currency (e.g., 'usd')

        Returns:
            Dict mapping symbol to price, e.g., {'btc': 50000.0, 'eth': 3000.0}
        """
        if not symbols:
            return {}

        if self.state.should_skip():
            return {}

        # CryptoCompare uses symbols directly (uppercase)
        fsyms = ",".join(s.upper() for s in symbols)
        tsym = vs_currency.upper()

        url = f"{self.BASE_URL}/pricemulti"
        params = {"fsyms": fsyms, "tsyms": tsym}

        data = self._make_request(url, params)
        if not data:
            return {}

        # Map response to lowercase symbols
        result = {}
        for sym_upper, prices in data.items():
            if isinstance(prices, dict) and tsym in prices:
                result[sym_upper.lower()] = float(prices[tsym])

        return result

    def get_price(self, symbol: str, vs_currency: str) -> Optional[float]:
        """Get price for a single cryptocurrency."""
        prices = self.get_prices([symbol], vs_currency)
        return prices.get(symbol.lower())

    def pause(self):
        """Pause API calls."""
        self.state.paused = True
        self._notify_state_change()

    def resume(self):
        """Resume API calls."""
        self.state.resume()
        self._notify_state_change()

    def is_paused(self) -> bool:
        """Check if API is paused."""
        return self.state.should_skip()

    def update_retry_settings(self, attempts: int, wait: int):
        """Update retry configuration."""
        self.retry_attempts = attempts
        self.retry_wait = wait


# Module-level convenience functions
_api: Optional[CryptoAPI] = None


def init_api(cache_dir: Path) -> CryptoAPI:
    """Initialize the global API instance."""
    global _api
    _api = CryptoAPI(cache_dir)
    return _api


def get_api() -> Optional[CryptoAPI]:
    """Get the global API instance."""
    return _api


def get_price(symbol: str, vs_currency: str) -> Optional[float]:
    """Convenience function to get price."""
    if _api:
        return _api.get_price(symbol, vs_currency)
    return None


def get_prices(symbols: List[str], vs_currency: str) -> Dict[str, float]:
    """Convenience function to get multiple prices."""
    if _api:
        return _api.get_prices(symbols, vs_currency)
    return {}
