"""CoinGecko API integration with caching and retry logic."""

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


class CoinGeckoAPI:
    """CoinGecko API client with caching and retry logic."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_DURATION = timedelta(hours=24)

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

    def _save_cache(self, name: str, data: dict):
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
            # Check for rate limit before raising
            if response.status_code == 429:
                raise RateLimitError("Rate limited by API")
            response.raise_for_status()
            data = response.json()
            # CoinGecko may return error in JSON body
            if isinstance(data, dict) and "status" in data:
                status = data["status"]
                if isinstance(status, dict) and status.get("error_code") == 429:
                    raise RateLimitError(status.get("error_message", "Rate limited"))
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
        """Get list of supported vs currencies (cached 24h)."""
        cached = self._load_cache("supported_currencies")
        if cached:
            return cached

        url = f"{self.BASE_URL}/simple/supported_vs_currencies"
        data = self._make_request(url)
        if data:
            self._save_cache("supported_currencies", data)
            return data
        return ["usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "cny"]

    def get_coin_list(self) -> List[Dict]:
        """Get list of all coins (cached 24h)."""
        cached = self._load_cache("coin_list")
        if cached:
            return cached

        url = f"{self.BASE_URL}/coins/list"
        data = self._make_request(url)
        if data:
            self._save_cache("coin_list", data)
            return data
        # Return default coins if API fails
        return [
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
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

        # Get coin list to map symbols to IDs
        coin_list = self.get_coin_list()
        symbol_to_id = {coin["symbol"].lower(): coin["id"] for coin in coin_list}

        # Map requested symbols to IDs
        ids = []
        symbol_map = {}  # id -> symbol
        for sym in symbols:
            sym_lower = sym.lower()
            if sym_lower in symbol_to_id:
                coin_id = symbol_to_id[sym_lower]
                ids.append(coin_id)
                symbol_map[coin_id] = sym_lower

        if not ids:
            return {}

        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": ",".join(ids),
            "vs_currencies": vs_currency,
        }

        data = self._make_request(url, params)
        if not data:
            return {}

        # Map back to symbols
        result = {}
        for coin_id, prices in data.items():
            if coin_id in symbol_map and vs_currency in prices:
                result[symbol_map[coin_id]] = float(prices[vs_currency])

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
_api: Optional[CoinGeckoAPI] = None


def init_api(cache_dir: Path) -> CoinGeckoAPI:
    """Initialize the global API instance."""
    global _api
    _api = CoinGeckoAPI(cache_dir)
    return _api


def get_api() -> Optional[CoinGeckoAPI]:
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
