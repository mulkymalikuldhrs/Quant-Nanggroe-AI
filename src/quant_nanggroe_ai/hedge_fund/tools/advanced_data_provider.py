"""
Advanced Multi-Source Data Provider
With Auto-Failover, Rate Limiting, and Caching
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import yfinance as yf


class DataSource(Enum):
    """Available data sources (all FREE!)"""
    # Stocks
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    TIINGO = "tiingo"
    
    # Forex
    EXCHANGE_RATE_API = "exchange_rate_api"
    FRANKFURTER = "frankfurter"
    FX_LAYER = "fx_layer"
    
    # Crypto
    COINGECKO = "coingecko"
    BINANCE = "binance"
    CRYPTOWATCH = "cryptowatch"
    
    # Commodities
    TradingEconomics = "trading_economics"
    METALS_API = "metals_api"


@dataclass
class PriceData:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None
    source: str = "unknown"


@dataclass
class DataSourceStats:
    source: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    reliability: float = 100.0


class RateLimiter:
    """Rate limiter with token bucket"""
    
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.tokens = calls
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Refill tokens
            self.tokens = min(self.calls, self.tokens + (elapsed / self.period) * self.calls)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class DataCache:
    """Simple file-based cache with expiration"""
    
    def __init__(self, cache_dir: str = "cache", ttl: int = 3600):
        self.cache_dir = cache_dir
        self.ttl = ttl
        import os
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        import os
        import json
        
        filepath = f"{self.cache_dir}/{self._get_key(key)}.json"
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check expiration
            if time.time() - data.get('timestamp', 0) > self.ttl:
                os.remove(filepath)
                return None
            
            return data.get('value')
        except:
            return None
    
    def set(self, key: str, value: Any):
        import os
        import json
        
        filepath = f"{self.cache_dir}/{self._get_key(key)}.json"
        with open(filepath, 'w') as f:
            json.dump({
                'value': value,
                'timestamp': time.time()
            }, f)


class MultiSourceDataProvider:
    """
    Advanced data provider with:
    - Multiple free data sources
    - Auto-failover
    - Rate limiting
    - Caching
    - Source reliability tracking
    """
    
    def __init__(self):
        self.cache = DataCache(ttl=3600)  # 1 hour cache
        
        # Rate limiters (calls per second)
        self.rate_limiters = {
            DataSource.COINGECKO: RateLimiter(10, 60),  # 10/min
            DataSource.ALPHA_VANTAGE: RateLimiter(5, 60),  # 5/min
            DataSource.FINNHUB: RateLimiter(60, 60),  # 60/min
            DataSource.TIINGO: RateLimiter(100, 60),  # 100/min
        }
        
        # Source statistics
        self.stats: Dict[str, DataSourceStats] = {}
        
        # Initialize stats
        for source in DataSource:
            self.stats[source.value] = DataSourceStats(source=source.value)
    
    def _update_stats(self, source: str, success: bool, response_time: float):
        """Update source statistics"""
        stat = self.stats.get(source)
        if stat:
            stat.total_requests += 1
            if success:
                stat.successful_requests += 1
                stat.last_success = datetime.now()
            else:
                stat.failed_requests += 1
                stat.last_failure = datetime.now()
            
            # Update reliability
            if stat.total_requests > 0:
                stat.reliability = (stat.successful_requests / stat.total_requests) * 100
            
            # Update avg response time (exponential moving average)
            stat.avg_response_time = 0.9 * stat.avg_response_time + 0.1 * response_time
    
    def _wait_for_rate_limit(self, source: DataSource):
        """Wait for rate limit if needed"""
        limiter = self.rate_limiters.get(source)
        if limiter:
            while not limiter.acquire():
                time.sleep(0.1)
    
    # ============ STOCK DATA (US) ============
    
    def get_stock_price_yahoo(self, ticker: str, days: int = 30) -> List[PriceData]:
        """Get US stock from Yahoo Finance"""
        start_time = time.time()
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                return []
            
            prices = []
            for idx, row in hist.iterrows():
                prices.append(PriceData(
                    date=idx.strftime("%Y-%m-%d"),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                    adj_close=float(row.get('Adj Close', row['Close'])),
                    source="yahoo_finance"
                ))
            
            self._update_stats(DataSource.YAHOO_FINANCE.value, True, time.time() - start_time)
            return prices
        except Exception as e:
            self._update_stats(DataSource.YAHOO_FINANCE.value, False, time.time() - start_time)
            return []
    
    def get_stock_price_alpha_vantage(self, ticker: str, api_key: str = "demo") -> List[PriceData]:
        """Get stock from Alpha Vantage (free tier: 25 requests/day)"""
        self._wait_for_rate_limit(DataSource.ALPHA_VANTAGE)
        start_time = time.time()
        
        cache_key = f"alpha_vantage_{ticker}"
        if cached := self.cache.get(cache_key):
            return cached
        
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "apikey": api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            prices = []
            time_series = data.get("Time Series (Daily)", {})
            for date, values in list(time_series.items())[:30]:
                prices.append(PriceData(
                    date=date,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(values["5. volume"]),
                    source="alpha_vantage"
                ))
            
            self.cache.set(cache_key, prices)
            self._update_stats(DataSource.ALPHA_VANTAGE.value, True, time.time() - start_time)
            return prices
        except Exception as e:
            self._update_stats(DataSource.ALPHA_VANTAGE.value, False, time.time() - start_time)
            return []
    
    def get_stock_price_finnhub(self, ticker: str, api_key: str = None) -> List[PriceData]:
        """Get stock from Finnhub (free tier: 60 calls/min)"""
        if not api_key:
            return self.get_stock_price_yahoo(ticker)
        
        self._wait_for_rate_limit(DataSource.FINNHUB)
        start_time = time.time()
        
        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {"symbol": ticker, "token": api_key}
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('c'):  # Current price exists
                now = datetime.now().strftime("%Y-%m-%d")
                return [PriceData(
                    date=now,
                    open=data.get('o', 0),
                    high=data.get('h', 0),
                    low=data.get('l', 0),
                    close=data.get('c', 0),
                    volume=0,
                    source="finnhub"
                )]
            
            self._update_stats(DataSource.FINNHUB.value, False, time.time() - start_time)
            return []
        except Exception as e:
            self._update_stats(DataSource.FINNHUB.value, False, time.time() - start_time)
            return []
    
    # ============ STOCK DATA (INDONESIAN/IDX) ============
    
    def get_idx_stock_price(self, ticker: str, days: int = 30) -> List[PriceData]:
        """Get Indonesian stock (auto .JK suffix)"""
        yahoo_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        return self.get_stock_price_yahoo(yahoo_ticker, days)
    
    # ============ FOREX DATA ============
    
    def get_forex_exchangerate_api(self, base: str = "USD", quote: str = "IDR") -> Dict[str, float]:
        """Get forex from exchangerate-api.com (FREE, no key)"""
        start_time = time.time()
        
        try:
            url = f"https://open.er-api.com/v6/latest/{base}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            rate = float(data.get('rates', {}).get(quote, 0))
            
            self._update_stats(DataSource.EXCHANGE_RATE_API.value, True, time.time() - start_time)
            return {'rate': rate, 'source': 'exchangerate-api'}
        except Exception as e:
            self._update_stats(DataSource.EXCHANGE_RATE_API.value, False, time.time() - start_time)
            return {'rate': 0, 'source': 'exchangerate-api'}
    
    def get_forex_frankfurter(self, base: str = "USD", quote: str = "EUR") -> Dict[str, float]:
        """Get forex from Frankfurter API (ECB data, FREE)"""
        start_time = time.time()
        
        try:
            url = f"https://api.frankfurter.app/latest"
            params = {"from": base, "to": quote}
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            rate = float(data.get('rates', {}).get(quote, 0))
            
            self._update_stats(DataSource.FRANKFURTER.value, True, time.time() - start_time)
            return {'rate': rate, 'source': 'frankfurter'}
        except Exception as e:
            self._update_stats(DataSource.FRANKFURTER.value, False, time.time() - start_time)
            return {'rate': 0, 'source': 'frankfurter'}
    
    # ============ CRYPTO DATA ============
    
    def get_crypto_coingecko(self, symbol: str = "bitcoin", currency: str = "usd", days: int = 30) -> List[PriceData]:
        """Get crypto from CoinGecko (FREE, 10-50 calls/min)"""
        self._wait_for_rate_limit(DataSource.COINGECKO)
        start_time = time.time()
        
        # Map symbol to CoinGecko ID
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'UNI': 'uniswap',
            'ATOM': 'cosmos',
            'FIL': 'filecoin',
            'NEAR': 'near',
        }
        
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': currency,
                'days': days,
                'interval': 'daily'
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                self._update_stats(DataSource.COINGECKO.value, False, time.time() - start_time)
                return []
            
            data = response.json()
            prices = data.get('prices', [])
            
            result = []
            for price_data in prices:
                timestamp = price_data[0] / 1000
                date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                result.append(PriceData(
                    date=date,
                    open=price_data[1],
                    high=price_data[1],
                    low=price_data[1],
                    close=price_data[1],
                    volume=0,
                    source="coingecko"
                ))
            
            self._update_stats(DataSource.COINGECKO.value, True, time.time() - start_time)
            return result
        except Exception as e:
            self._update_stats(DataSource.COINGECKO.value, False, time.time() - start_time)
            return []
    
    def get_crypto_binance(self, symbol: str = "BTC", quote: str = "USDT") -> Dict[str, float]:
        """Get crypto from Binance public API"""
        start_time = time.time()
        
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": f"{symbol.upper()}{quote.upper()}"}
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            result = {
                'price': float(data.get('lastPrice', 0)),
                'change_24h': float(data.get('priceChangePercent', 0)),
                'high': float(data.get('highPrice', 0)),
                'low': float(data.get('lowPrice', 0)),
                'volume': float(data.get('quoteVolume', 0)),
                'source': 'binance'
            }
            
            self._update_stats(DataSource.BINANCE.value, True, time.time() - start_time)
            return result
        except Exception as e:
            self._update_stats(DataSource.BINANCE.value, False, time.time() - start_time)
            return {}
    
    # ============ COMMODITIES ============
    
    def get_commodity(self, symbol: str) -> Dict[str, float]:
        """Get commodity from Yahoo Finance"""
        commodity_map = {
            'GOLD': 'GC=F',
            'SILVER': 'SI=F',
            'OIL': 'CL=F',
            'BRENT': 'BZ=F',
            'NATGAS': 'NG=F',
            'COPPER': 'HG=F',
            'PLATINUM': 'PL=F',
            'PALLADIUM': 'PA=F',
        }
        
        yahoo_ticker = commodity_map.get(symbol.upper(), symbol)
        return self.get_stock_price_yahoo(yahoo_ticker, 1)
    
    def get_gold_metal_price(self) -> Dict[str, float]:
        """Get gold from Metals API (free tier available)"""
        start_time = time.time()
        
        try:
            url = "https://www.goldapi.io/api/XAU/USD"
            headers = {"x-access-token": "demo"}
            
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()
            
            result = {
                'price': data.get('price', 0),
                'source': 'metals_api'
            }
            
            self._update_stats(DataSource.METALS_API.value, True, time.time() - start_time)
            return result
        except:
            # Fallback to Yahoo Finance
            prices = self.get_stock_price_yahoo('GC=F', 1)
            if prices:
                return {'price': prices[0].close, 'source': 'yahoo_finance'}
            return {'price': 0, 'source': 'metals_api'}
    
    # ============ INDEX DATA ============
    
    def get_index(self, symbol: str) -> Dict[str, float]:
        """Get market index"""
        index_map = {
            'IHSG': '^JKSE',
            'SPX': '^GSPC',
            'DJI': '^DJI',
            'IXIC': '^IXIC',
            'FTSE': '^FTSE',
            'N225': '^N225',
            'HSI': '^HSI',
        }
        
        yahoo_ticker = index_map.get(symbol.upper(), symbol)
        prices = self.get_stock_price_yahoo(yahoo_ticker, 1)
        
        if prices:
            return {
                'price': prices[0].close,
                'change': prices[0].close - prices[0].open,
                'source': 'yahoo_finance'
            }
        return {'price': 0}
    
    # ============ UNIVERSAL FETCHER ============
    
    def get_price_data(self, ticker: str, asset_type: str = "stock", days: int = 30) -> List[PriceData]:
        """
        Universal price fetcher with auto-failover
        Tries multiple sources until one succeeds
        """
        cache_key = f"price_{asset_type}_{ticker}_{days}"
        
        if cached := self.cache.get(cache_key):
            return cached
        
        # Try sources based on asset type
        sources_order = self._get_source_order(asset_type)
        
        for source in sources_order:
            prices = self._try_source(source, ticker, days)
            if prices:
                self.cache.set(cache_key, prices)
                return prices
        
        return []
    
    def _get_source_order(self, asset_type: str) -> List[str]:
        """Get prioritized list of sources for asset type"""
        orders = {
            'stock_us': ['yahoo_finance', 'alpha_vantage', 'finnhub'],
            'stock_idx': ['yahoo_finance'],
            'forex': ['exchangerate_api', 'frankfurter'],
            'crypto': ['coingecko', 'binance'],
            'commodity': ['yahoo_finance', 'trading_economics'],
            'index': ['yahoo_finance'],
        }
        return orders.get(asset_type, ['yahoo_finance'])
    
    def _try_source(self, source: str, ticker: str, days: int) -> List[PriceData]:
        """Try a specific data source"""
        source_map = {
            'yahoo_finance': lambda: self.get_stock_price_yahoo(ticker, days),
            'alpha_vantage': lambda: self.get_stock_price_alpha_vantage(ticker),
            'finnhub': lambda: self.get_stock_price_finnhub(ticker),
            'exchangerate_api': lambda: self.get_forex_exchangerate_api(ticker.split('/')[0], ticker.split('/')[1]) or [],
            'frankfurter': lambda: self.get_forex_frankfurter(ticker.split('/')[0], ticker.split('/')[1]) or [],
            'coingecko': lambda: self.get_crypto_coingecko(ticker, 'usd', days),
            'binance': lambda: self.get_crypto_binance(ticker) or [],
        }
        
        func = source_map.get(source)
        if func:
            try:
                return func()
            except:
                pass
        return []
    
    # ============ MULTI-SOURCE AGGREGATION ============
    
    def get_aggregated_price(self, ticker: str, asset_type: str = "stock") -> Dict[str, Any]:
        """
        Get price from multiple sources and aggregate
        Returns: {'price': weighted_avg, 'sources': count, 'variance': std}
        """
        prices = []
        
        # Try multiple sources in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            if asset_type in ['stock_us', 'stock_idx']:
                futures.append(executor.submit(self.get_stock_price_yahoo, ticker, 1))
                if asset_type == 'stock_us':
                    futures.append(executor.submit(self.get_stock_price_alpha_vantage, ticker))
            
            if asset_type == 'crypto':
                futures.append(executor.submit(self.get_crypto_coingecko, ticker, 'usd', 1))
                futures.append(executor.submit(self.get_crypto_binance, ticker))
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result and hasattr(result[0], 'close'):
                        prices.append(result[0].close)
                except:
                    pass
        
        if not prices:
            return {'price': 0, 'sources': 0, 'variance': 0}
        
        import numpy as np
        return {
            'price': float(np.mean(prices)),
            'sources': len(prices),
            'variance': float(np.std(prices)) if len(prices) > 1 else 0
        }
    
    # ============ STATISTICS ============
    
    def get_source_stats(self) -> Dict[str, DataSourceStats]:
        """Get statistics for all sources"""
        return self.stats
    
    def get_best_source(self, asset_type: str) -> str:
        """Get most reliable source for asset type"""
        sources = self._get_source_order(asset_type)
        
        best_source = None
        best_reliability = 0
        
        for source in sources:
            stat = self.stats.get(source)
            if stat and stat.reliability > best_reliability:
                best_reliability = stat.reliability
                best_source = source
        
        return best_source or 'yahoo_finance'


# Global data provider instance
data_provider = MultiSourceDataProvider()


if __name__ == "__main__":
    print("=== Testing Multi-Source Data Provider ===\n")
    
    provider = MultiSourceDataProvider()
    
    # Test stocks
    print("1. US Stock (AAPL):")
    prices = provider.get_stock_price_yahoo("AAPL", 5)
    print(f"   Yahoo Finance: {len(prices)} days loaded")
    
    # Test IDX
    print("\n2. IDX Stock (BBCA):")
    prices = provider.get_idx_stock_price("BBCA", 5)
    print(f"   IDX: {len(prices)} days loaded")
    
    # Test Forex
    print("\n3. Forex (USD/IDR):")
    rate = provider.get_forex_exchangerate_api("USD", "IDR")
    print(f"   Rate: {rate}")
    
    # Test Crypto
    print("\n4. Crypto (BTC):")
    prices = provider.get_crypto_coingecko("BTC", "usd", 5)
    print(f"   CoinGecko: {len(prices)} days loaded")
    
    # Test Index
    print("\n5. Index (IHSG):")
    index = provider.get_index("IHSG")
    print(f"   IHSG: {index}")
    
    # Show stats
    print("\n6. Source Statistics:")
    for name, stat in provider.get_source_stats().items():
        if stat.total_requests > 0:
            print(f"   {name}: {stat.reliability:.1f}% ({stat.successful_requests}/{stat.total_requests})")
    
    print("\n=== All tests completed ===")

# ============ BACKWARD COMPATIBILITY ALIAS ============
# AdvancedDataProvider was renamed to MultiSourceDataProvider
# This alias maintains backward compatibility
AdvancedDataProvider = MultiSourceDataProvider

# ============ BACKWARD COMPATIBILITY LAYER ============
# These functions provide backward compatibility with existing tests

def fetch_yahoo_finance(ticker: str, period: str = "5d") -> pd.DataFrame:
    """
    Fetch historical prices from Yahoo Finance
    Backward compatibility function for test suite
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance: {e}")
        return pd.DataFrame()


def get_historical_prices(ticker: str, period: str = "5d", market: str = "US") -> pd.DataFrame:
    """
    Get historical prices with auto-market detection
    Backward compatibility function for test suite
    """
    try:
        import yfinance as yf
        
        # Adjust ticker for IDX market
        if market == "IDX" and not ticker.endswith(".JK"):
            ticker = f"{ticker}.JK"
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        logger.error(f"Error fetching historical prices: {e}")
        return pd.DataFrame()


# Backward-compatible class wrapper
class AdvancedDataProvider:
    """
    Backward compatibility wrapper around MultiSourceDataProvider
    Maintains the old API that tests expect
    """
    
    def __init__(self):
        self._provider = MultiSourceDataProvider()
        self.cache = self._provider.cache
        self.rate_limiters = self._provider.rate_limiters
        self.stats = self._provider.stats
    
    def get_historical_prices(self, ticker: str, period: str = "5d", market: str = "US", asset_type: str = "stock") -> pd.DataFrame:
        """Get historical prices (backward compatible)"""
        # Handle different asset types
        if asset_type == "crypto":
            return fetch_coingecko(ticker, "usd", int(period.rstrip('d'))) if period.isdigit() or period.endswith('d') else fetch_coingecko(ticker)
        else:
            # For stocks, use yahoo finance
            return fetch_yahoo_finance(ticker, period)
    
    def __getattr__(self, name):
        """Delegate all other attributes to MultiSourceDataProvider"""
        return getattr(self._provider, name)

# Additional backward compatibility function
def fetch_coingecko(symbol: str, currency: str = "usd", days: int = 30) -> pd.DataFrame:
    """
    Fetch crypto from CoinGecko
    Backward compatibility function for test suite
    """
    try:
        provider = MultiSourceDataProvider()
        prices = provider.get_crypto_coingecko(symbol, currency, days)
        
        # Convert to DataFrame for backward compatibility
        if prices:
            import pandas as pd
            data = [{'date': p.date, 'close': p.close} for p in prices]
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching from CoinGecko: {e}")
        return pd.DataFrame()
