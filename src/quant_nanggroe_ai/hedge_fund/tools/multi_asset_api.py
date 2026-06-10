"""
Multi-Asset Data Provider - FREE data sources for:
- Stocks (US, Indonesia/IDX, Global)
- Forex/Currencies
- Cryptocurrencies
- Commodities
"""

import json
import time
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import requests


class AssetType(Enum):
    STOCK_US = "stock_us"
    STOCK_IDX = "stock_idx"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"


@dataclass
class PriceData:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None


@dataclass
class TickerInfo:
    symbol: str
    name: str
    asset_type: AssetType
    exchange: str
    currency: str


# ============ INDONESIAN STOCKS (IDX) ============

def get_idx_stock_price(ticker: str, days: int = 30) -> List[PriceData]:
    """
    Get Indonesian stock price from Yahoo Finance (.JK suffix)
    Free - no API key needed
    """
    try:
        import yfinance as yf
        
        # Add .JK suffix for Indonesian stocks if not present
        if not ticker.endswith(".JK"):
            yahoo_ticker = f"{ticker}.JK"
        else:
            yahoo_ticker = ticker
        
        stock = yf.Ticker(yahoo_ticker)
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
                adj_close=float(row.get('Adj Close', row['Close']))
            ))
        
        return prices
    except Exception as e:
        print(f"Error fetching IDX stock {ticker}: {e}")
        return []


def get_idx_stock_info(ticker: str) -> Optional[TickerInfo]:
    """Get Indonesian stock info from IDX API"""
    try:
        # IDX Constituent API (free)
        response = requests.get(
            "https://www.idx.co.id/umbraco/Surface/StockData/GetConstituent",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('Data', []):
                if item.get('KodeEmiten') == ticker.upper():
                    return TickerInfo(
                        symbol=ticker.upper(),
                        name=item.get('NamaEmiten', ''),
                        asset_type=AssetType.STOCK_IDX,
                        exchange="IDX",
                        currency="IDR"
                    )
    except Exception as e:
        print(f"Error fetching IDX info for {ticker}: {e}")
    
    return None


# ============ US STOCKS ============

def get_us_stock_price(ticker: str, days: int = 30) -> List[PriceData]:
    """Get US stock price from Yahoo Finance - FREE, no API key"""
    try:
        import yfinance as yf
        
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
                adj_close=float(row.get('Adj Close', row['Close']))
            ))
        
        return prices
    except Exception as e:
        print(f"Error fetching US stock {ticker}: {e}")
        return []


# ============ FOREX ============

def get_forex_price(base: str = "USD", quote: str = "IDR") -> Dict[str, float]:
    """
    Get forex exchange rates from free API
    No API key required for basic endpoints
    Sources: exchangerate-api.com (free), freeforexapi.com
    """
    try:
        # exchangerate-api free endpoint (no key needed)
        url = f"https://open.er-api.com/v6/latest/{base}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates', {})
            return {
                'rate': float(rates.get(quote, 0)),
                'base': base,
                'quote': quote,
                'timestamp': data.get('timeLastUpdateUnix', '')
            }
    except Exception as e:
        print(f"Error fetching forex {base}/{quote}: {e}")
    
    return {'rate': 0, 'base': base, 'quote': quote}


def get_forex_cross_rate(base: str, quote: str) -> float:
    """Get cross exchange rate between two currencies"""
    try:
        # Get both rates relative to USD
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates', {})
            base_rate = rates.get(base, 1)
            quote_rate = rates.get(quote, 1)
            return quote_rate / base_rate
    except Exception as e:
        print(f"Error fetching cross rate {base}/{quote}: {e}")
    
    return 0


# ============ CRYPTOCURRENCIES ============

def get_crypto_price(symbol: str, quote: str = "USDT", days: int = 30) -> List[PriceData]:
    """
    Get cryptocurrency price from Binance public API
    FREE - no API key needed for public endpoints
    """
    try:
        # Binance ticker price (public)
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}{quote.upper()}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return [PriceData(
                date=datetime.now().strftime("%Y-%m-%d"),
                open=float(data.get('openPrice', 0)),
                high=float(data.get('highPrice', 0)),
                low=float(data.get('lowPrice', 0)),
                close=float(data.get('lastPrice', 0)),
                volume=int(float(data.get('quoteVolume', 0)))
            )]
    except Exception as e:
        print(f"Error fetching crypto {symbol}: {e}")
    
    return []


def get_crypto_historical(symbol: str = "BTC", quote: str = "USDT", days: int = 30) -> List[PriceData]:
    """
    Get cryptocurrency historical data from CoinGecko API
    FREE - no API key needed
    """
    try:
        # CoinGecko free API
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}/market_chart"
        params = {
            'vs_currency': quote.lower(),
            'days': min(days, 365)  # CoinGecko max is 365 days
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            result = []
            for i, price_data in enumerate(prices):
                timestamp = price_data[0] / 1000
                date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                vol = volumes[i][1] if i < len(volumes) else 0
                result.append(PriceData(
                    date=date,
                    open=price_data[1],
                    high=price_data[1],
                    low=price_data[1],
                    close=price_data[1],
                    volume=int(vol)
                ))
            
            return result
    except Exception as e:
        print(f"Error fetching crypto historical {symbol}: {e}")
    
    return []


def get_crypto_top_coins(limit: int = 10) -> List[Dict]:
    """Get top cryptocurrencies from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching top coins: {e}")
    
    return []


# ============ COMMODITIES ============

def get_commodity_price(symbol: str) -> Dict[str, Any]:
    """
    Get commodity prices from free APIs
    - Gold: GoldAPI.io (free tier) or alternative
    - Oil: Use forex/crypto proxy or Yahoo Finance
    """
    try:
        # Try Yahoo Finance for commodity ETFs
        import yfinance as yf
        
        # Common commodity tickers on Yahoo
        ticker_map = {
            'GOLD': 'GC=F',      # Gold Futures
            'SILVER': 'SI=F',    # Silver Futures
            'OIL': 'CL=F',       # Crude Oil
            'BRENT': 'BZ=F',     # Brent Oil
            'NATGAS': 'NG=F',    # Natural Gas
            'COPPER': 'HG=F',    # Copper
        }
        
        yahoo_ticker = ticker_map.get(symbol.upper(), symbol)
        stock = yf.Ticker(yahoo_ticker)
        hist = stock.history(period="1d")
        
        if not hist.empty:
            row = hist.iloc[0]
            return {
                'symbol': symbol,
                'price': float(row['Close']),
                'change': float(row.get('Open', 0) - row['Close']),
                'volume': int(row.get('Volume', 0)),
                'source': 'yahoo'
            }
    except Exception as e:
        print(f"Error fetching commodity {symbol}: {e}")
    
    return {'symbol': symbol, 'price': 0, 'error': str(e)}


def get_gold_price() -> Dict[str, float]:
    """Get gold price from GoldAPI.io or alternative"""
    try:
        # GoldAPI.io has a free tier with API key
        api_key = "goldapi-8x9xk2z9x9xk2z9x"  # Demo - user needs to get their own
        
        headers = {'x-access-token': api_key}
        response = requests.get(
            'https://www.goldapi.io/api/XAU/USD',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'price': data.get('price', 0),
                'symbol': 'XAU',
                'currency': 'USD'
            }
    except:
        pass
    
    # Fallback: Use proxy through crypto/forex
    return get_commodity_price('GOLD')


# ============ UNIVERSAL PRICE FETCHER ============

def get_price_data(ticker: str, asset_type: str = "stock", days: int = 30) -> List[PriceData]:
    """
    Universal price fetcher for all asset types
    
    Args:
        ticker: Symbol (e.g., 'AAPL', 'BBCA.JK', 'BTC', 'USD/IDR')
        asset_type: 'stock_us', 'stock_idx', 'forex', 'crypto', 'commodity'
        days: Number of days of historical data
    
    Returns:
        List of PriceData
    """
    asset = AssetType(asset_type) if asset_type else None
    
    if not asset:
        # Auto-detect asset type from ticker format
        if '.JK' in ticker:
            asset = AssetType.STOCK_IDX
        elif '/' in ticker or len(ticker) == 6:
            asset = AssetType.FOREX
        elif ticker.upper() in ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE']:
            asset = AssetType.CRYPTO
        else:
            asset = AssetType.STOCK_US
    
    if asset == AssetType.STOCK_IDX:
        clean_ticker = ticker.replace('.JK', '')
        return get_idx_stock_price(clean_ticker, days)
    
    elif asset == AssetType.STOCK_US:
        return get_us_stock_price(ticker, days)
    
    elif asset == AssetType.FOREX:
        base, quote = ticker.split('/') if '/' in ticker else ('USD', 'IDR')
        rate = get_forex_cross_rate(base, quote)
        return [PriceData(
            date=datetime.now().strftime("%Y-%m-%d"),
            open=rate,
            high=rate,
            low=rate,
            close=rate,
            volume=0
        )]
    
    elif asset == AssetType.CRYPTO:
        return get_crypto_historical(ticker, 'USDT', days)
    
    elif asset == AssetType.COMMODITY:
        prices = get_commodity_price(ticker)
        if prices.get('price'):
            return [PriceData(
                date=datetime.now().strftime("%Y-%m-%d"),
                open=prices['price'],
                high=prices['price'],
                low=prices['price'],
                close=prices['price'],
                volume=int(prices.get('volume', 0))
            )]
    
    return []


# ============ MARKET INDICES ============

def get_index_price(index_symbol: str) -> Dict[str, Any]:
    """Get major market indices"""
    try:
        import yfinance as yf
        
        indices = {
            'IHSG': '^JKSE',       # Indonesia Stock Exchange
            'SPX': '^GSPC',        # S&P 500
            'DJI': '^DJI',         # Dow Jones
            'IXIC': '^IXIC',       # Nasdaq
            'FTSE': '^FTSE',       # FTSE 100
            'N225': '^N225',       # Nikkei 225
            'HSI': '^HSI',         # Hang Seng
        }
        
        yahoo_ticker = indices.get(index_symbol.upper(), index_symbol)
        stock = yf.Ticker(yahoo_ticker)
        hist = stock.history(period="1d")
        
        if not hist.empty:
            row = hist.iloc[0]
            return {
                'symbol': index_symbol,
                'price': float(row['Close']),
                'change': float(row['Close'] - row['Open']),
                'percent_change': ((row['Close'] - row['Open']) / row['Open']) * 100
            }
    except Exception as e:
        print(f"Error fetching index {index_symbol}: {e}")
    
    return {'symbol': index_symbol, 'price': 0}


# ============ POPULAR TICKERS BY ASSET CLASS ============

POPULAR_TICKERS = {
    # Indonesian Stocks (IDX)
    'stock_idx': [
        'BBCA', 'BBRI', 'BMRI', 'TLKM', 'UNVR', 'ASII', 'HMSP', 'PTBA',
        'ANTM', 'TLKM', 'BBNI', 'BTPN', 'MIKA', 'UPST', 'DEWA', 'BRIS'
    ],
    
    # US Stocks
    'stock_us': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM',
        'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS', 'NFLX', 'PYPL', 'INTC'
    ],
    
    # Forex
    'forex': [
        'USD/IDR', 'USD/JPY', 'EUR/USD', 'GBP/USD', 'USD/CHF',
        'AUD/USD', 'USD/CNY', 'EUR/JPY', 'GBP/JPY', 'EUR/GBP'
    ],
    
    # Crypto
    'crypto': [
        'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'LINK',
        'LTC', 'BCH', 'AVAX', 'MATIC', 'UNI', 'ATOM', 'FIL', 'NEAR'
    ],
    
    # Commodities
    'commodity': [
        'GOLD', 'SILVER', 'OIL', 'BRENT', 'NATGAS', 'COPPER',
        'PLATINUM', 'PALLADIUM', 'COFFEE', 'SUGAR', 'CORN', 'WHEAT'
    ],
    
    # Indices
    'index': [
        'IHSG', 'SPX', 'DJI', 'IXIC', 'FTSE', 'N225', 'HSI'
    ]
}


if __name__ == "__main__":
    # Test all data sources
    print("=== Testing Multi-Asset Data Provider ===\n")
    
    # Test Indonesian Stock
    print("1. Indonesian Stock (BBCA.JK):")
    prices = get_idx_stock_price('BBCA', 5)
    print(f"   Found {len(prices)} days of data")
    
    # Test US Stock
    print("\n2. US Stock (AAPL):")
    prices = get_us_stock_price('AAPL', 5)
    print(f"   Found {len(prices)} days of data")
    
    # Test Forex
    print("\n3. Forex (USD/IDR):")
    rate = get_forex_cross_rate('USD', 'IDR')
    print(f"   1 USD = {rate:.2f} IDR")
    
    # Test Crypto
    print("\n4. Crypto (BTC):")
    prices = get_crypto_historical('BTC', 'USDT', 5)
    print(f"   Found {len(prices)} days of data")
    
    # Test Commodity
    print("\n5. Commodity (GOLD):")
    gold = get_commodity_price('GOLD')
    print(f"   Gold price: ${gold.get('price', 'N/A')}")
    
    # Test Index
    print("\n6. Index (IHSG):")
    index = get_index_price('IHSG')
    print(f"   IHSG: {index.get('price', 'N/A')}")
    
    print("\n=== All tests completed ===")
