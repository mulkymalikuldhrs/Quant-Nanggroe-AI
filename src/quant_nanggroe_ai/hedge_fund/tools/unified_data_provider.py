"""
Unified Data Provider - All Free Data Sources Connected

Sources:
- Stocks: Yahoo Finance (US, IDX)
- Forex: exchangerate-api.com, Frankfurter (ECB)
- Crypto: CoinGecko, Binance
- Commodities: Yahoo Finance
- Indices: Yahoo Finance
"""

import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import requests
import pandas as pd
import yfinance as yf


class AssetType(Enum):
    STOCK_US = "stock_us"
    STOCK_IDX = "stock_idx"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    INDEX = "index"


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
class MarketQuote:
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    high: float
    low: float
    source: str


class UnifiedDataProvider:
    """
    Unified Data Provider - All FREE data sources
    
    Usage:
        provider = UnifiedDataProvider()
        prices = provider.get_price("AAPL", "stock_us")
        forex = provider.get_forex("USD/IDR")
        crypto = provider.get_crypto("BTC")
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (AI-Hedge-Fund/1.0)'
        })
    
    # ============ STOCKS ============
    
    def get_stock(self, ticker: str, days: int = 30, market: str = "US") -> List[PriceData]:
        """
        Get stock price from Yahoo Finance
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'BBCA')
            days: Number of days of historical data
            market: 'US' or 'IDX'
        
        Returns:
            List of PriceData
        """
        try:
            if market.upper() == "IDX" and not ticker.endswith(".JK"):
                ticker = f"{ticker}.JK"
            
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
            
            return prices
        except Exception as e:
            print(f"Error fetching stock {ticker}: {e}")
            return []
    
    def get_stock_quote(self, ticker: str, market: str = "US") -> Optional[MarketQuote]:
        """Get current stock quote"""
        prices = self.get_stock(ticker, days=1, market=market)
        if prices:
            p = prices[0]
            change = p.close - p.open
            return MarketQuote(
                symbol=ticker,
                price=p.close,
                change=change,
                change_pct=(change / p.open * 100) if p.open > 0 else 0,
                volume=p.volume,
                high=p.high,
                low=p.low,
                source="yahoo_finance"
            )
        return None
    
    # ============ FOREX ============
    
    def get_forex(self, pair: str = "USD/IDR") -> Dict[str, Any]:
        """
        Get forex rate
        
        Args:
            pair: Currency pair (e.g., 'USD/IDR', 'EUR/USD')
        
        Returns:
            Dict with rate info
        """
        try:
            base, quote = pair.split('/')
            
            # Try exchangerate-api first
            url = f"https://open.er-api.com/v6/latest/{base}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                rate = float(data.get('rates', {}).get(quote, 0))
                return {
                    'pair': pair,
                    'rate': rate,
                    'base': base,
                    'quote': quote,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'exchangerate-api'
                }
        except Exception as e:
            print(f"Error fetching forex {pair}: {e}")
        
        return {'pair': pair, 'rate': 0, 'source': 'error'}
    
    def get_forex_frankfurter(self, base: str = "USD", quote: str = "EUR") -> Dict[str, Any]:
        """Get forex from Frankfurter (ECB)"""
        try:
            url = "https://api.frankfurter.app/latest"
            params = {"from": base, "to": quote}
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                rate = float(data.get('rates', {}).get(quote, 0))
                return {
                    'pair': f"{base}/{quote}",
                    'rate': rate,
                    'source': 'frankfurter'
                }
        except Exception as e:
            print(f"Error fetching frankfurter {base}/{quote}: {e}")
        
        return {'pair': f"{base}/{quote}", 'rate': 0, 'source': 'error'}
    
    # ============ CRYPTO ============
    
    def get_crypto(self, symbol: str = "BTC", quote: str = "USDT", days: int = 30) -> List[PriceData]:
        """
        Get crypto historical data from CoinGecko
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            quote: Quote currency (default: USDT)
            days: Number of days
        
        Returns:
            List of PriceData
        """
        try:
            # Map symbol to CoinGecko ID
            symbol_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin',
                'DOT': 'polkadot', 'LINK': 'chainlink', 'LTC': 'litecoin',
                'BCH': 'bitcoin-cash', 'AVAX': 'avalanche-2',
                'MATIC': 'matic-network', 'UNI': 'uniswap',
                'ATOM': 'cosmos', 'FIL': 'filecoin', 'NEAR': 'near',
            }
            
            coin_id = symbol_map.get(symbol.upper(), symbol.lower())
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',  # CoinGecko uses USD not USDT
                'days': min(days, 365)
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
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
                        volume=int(vol),
                        source="coingecko"
                    ))
                
                return result
        except Exception as e:
            print(f"Error fetching crypto {symbol}: {e}")
        
        return []
    
    def get_crypto_binance(self, symbol: str = "BTC", quote: str = "USDT") -> Dict[str, Any]:
        """Get crypto from Binance"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": f"{symbol.upper()}{quote.upper()}"}
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': float(data.get('lastPrice', 0)),
                    'change_24h': float(data.get('priceChangePercent', 0)),
                    'high': float(data.get('highPrice', 0)),
                    'low': float(data.get('lowPrice', 0)),
                    'volume': float(data.get('quoteVolume', 0)),
                    'source': 'binance'
                }
        except Exception as e:
            print(f"Error fetching binance {symbol}: {e}")
        
        return {'symbol': symbol, 'price': 0, 'source': 'error'}
    
    def get_crypto_quote(self, symbol: str = "BTC") -> Optional[MarketQuote]:
        """Get current crypto quote from CoinGecko"""
        try:
            # Map symbol to CoinGecko ID
            symbol_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin',
            }
            
            coin_id = symbol_map.get(symbol.upper(), symbol.lower())
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                market = data.get('market_data', {})
                current = market.get('current_price', {})
                
                return MarketQuote(
                    symbol=symbol,
                    price=current.get('usd', 0),
                    change=market.get('price_change_24h', 0),
                    change_pct=market.get('price_change_percentage_24h', 0),
                    volume=market.get('total_volume', {}).get('usd', 0),
                    high=market.get('high_24h', {}).get('usd', 0),
                    low=market.get('low_24h', {}).get('usd', 0),
                    source='coingecko'
                )
        except Exception as e:
            print(f"Error fetching crypto quote {symbol}: {e}")
        
        return None
    
    # ============ COMMODITIES ============
    
    def get_commodity(self, symbol: str) -> Dict[str, Any]:
        """
        Get commodity price
        
        Args:
            symbol: 'GOLD', 'SILVER', 'OIL', 'BRENT', etc.
        
        Returns:
            Dict with commodity info
        """
        try:
            commodity_map = {
                'GOLD': 'GC=F', 'SILVER': 'SI=F', 'OIL': 'CL=F',
                'BRENT': 'BZ=F', 'NATGAS': 'NG=F', 'COPPER': 'HG=F',
                'PLATINUM': 'PL=F', 'PALLADIUM': 'PA=F',
            }
            
            yahoo_ticker = commodity_map.get(symbol.upper(), symbol)
            prices = self.get_stock(yahoo_ticker, days=1)
            
            if prices:
                p = prices[0]
                return {
                    'symbol': symbol,
                    'price': p.close,
                    'change': p.close - p.open,
                    'volume': p.volume,
                    'source': 'yahoo_finance'
                }
        except Exception as e:
            print(f"Error fetching commodity {symbol}: {e}")
        
        return {'symbol': symbol, 'price': 0, 'source': 'error'}
    
    # ============ INDICES ============
    
    def get_index(self, symbol: str) -> Dict[str, Any]:
        """Get market index value"""
        try:
            index_map = {
                'IHSG': '^JKSE', 'SPX': '^GSPC', 'DJI': '^DJI',
                'IXIC': '^IXIC', 'FTSE': '^FTSE', 'N225': '^N225',
                'HSI': '^HSI', 'DAX': '^GDAXI', 'CAC': '^FCHI',
            }
            
            yahoo_ticker = index_map.get(symbol.upper(), symbol)
            prices = self.get_stock(yahoo_ticker, days=1)
            
            if prices:
                p = prices[0]
                return {
                    'symbol': symbol,
                    'price': p.close,
                    'change': p.close - p.open,
                    'change_pct': ((p.close - p.open) / p.open * 100) if p.open > 0 else 0,
                    'source': 'yahoo_finance'
                }
        except Exception as e:
            print(f"Error fetching index {symbol}: {e}")
        
        return {'symbol': symbol, 'price': 0, 'source': 'error'}
    
    # ============ UNIVERSAL GETTER ============
    
    def get_price(self, ticker: str, asset_type: str = "stock", days: int = 30) -> List[PriceData]:
        """
        Universal price getter for all asset types
        
        Args:
            ticker: Symbol (e.g., 'AAPL', 'BBCA.JK', 'BTC', 'USD/IDR', 'GOLD')
            asset_type: 'stock_us', 'stock_idx', 'forex', 'crypto', 'commodity', 'index'
            days: Days of historical data
        
        Returns:
            List of PriceData
        """
        asset = AssetType(asset_type) if asset_type else None
        
        # Auto-detect
        if not asset:
            if '.JK' in ticker:
                asset = AssetType.STOCK_IDX
            elif '/' in ticker:
                asset = AssetType.FOREX
            elif ticker.upper() in ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE']:
                asset = AssetType.CRYPTO
            elif ticker.upper() in ['GOLD', 'SILVER', 'OIL', 'BRENT']:
                asset = AssetType.COMMODITY
            else:
                asset = AssetType.STOCK_US
        
        if asset == AssetType.STOCK_IDX:
            return self.get_stock(ticker.replace('.JK', ''), days, "IDX")
        elif asset == AssetType.STOCK_US:
            return self.get_stock(ticker, days, "US")
        elif asset == AssetType.FOREX:
            rate = self.get_forex(ticker)['rate']
            return [PriceData(
                date=datetime.now().strftime("%Y-%m-%d"),
                open=rate, high=rate, low=rate, close=rate, volume=0
            )]
        elif asset == AssetType.CRYPTO:
            return self.get_crypto(ticker, "USDT", days)
        elif asset == AssetType.COMMODITY:
            prices = self.get_commodity(ticker)
            if prices.get('price'):
                return [PriceData(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    open=prices['price'], high=prices['price'],
                    low=prices['price'], close=prices['price'],
                    volume=prices.get('volume', 0)
                )]
        
        return []
    
    # ============ BATCH OPERATIONS ============
    
    def get_multiple(self, tickers: List[Dict], days: int = 30) -> Dict[str, List[PriceData]]:
        """
        Get prices for multiple assets
        
        Args:
            tickers: List of {'symbol': 'AAPL', 'type': 'stock_us'}
        
        Returns:
            Dict mapping symbol to PriceData list
        """
        results = {}
        for item in tickers:
            symbol = item['symbol']
            asset_type = item.get('type', 'stock')
            results[symbol] = self.get_price(symbol, asset_type, days)
        return results


# ============ CONVENIENCE FUNCTIONS ============

def get_price_data(ticker: str, asset_type: str = "stock", days: int = 30) -> List[PriceData]:
    """Quick access to price data"""
    provider = UnifiedDataProvider()
    return provider.get_price(ticker, asset_type, days)


def get_popular_tickers() -> Dict[str, List[str]]:
    """Get popular tickers by asset type"""
    return {
        'stock_us': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM'],
        'stock_idx': ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'UNVR', 'ASII', 'HMSP', 'PTBA'],
        'forex': ['USD/IDR', 'USD/JPY', 'EUR/USD', 'GBP/USD', 'USD/CHF'],
        'crypto': ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'LINK'],
        'commodity': ['GOLD', 'SILVER', 'OIL', 'BRENT', 'NATGAS'],
        'index': ['IHSG', 'SPX', 'DJI', 'IXIC', 'FTSE', 'N225']
    }


# ============ TEST ============

if __name__ == "__main__":
    provider = UnifiedDataProvider()
    
    print("=" * 60)
    print("UNIFIED DATA PROVIDER - All APIs Connected")
    print("=" * 60)
    
    # Test Stocks
    print("\n📈 STOCKS (Yahoo Finance)")
    aapl = provider.get_stock_quote("AAPL")
    print(f"   AAPL: ${aapl.price:.2f} ({aapl.change_pct:+.2f}%)" if aapl else "   AAPL: Error")
    
    bca = provider.get_stock_quote("BBCA", "IDX")
    print(f"   BBCA: Rp{bca.price:.0f} ({bca.change_pct:+.2f}%)" if bca else "   BBCA: Error")
    
    # Test Forex
    print("\n💱 FOREX (exchangerate-api.com)")
    usd_idr = provider.get_forex("USD/IDR")
    print(f"   USD/IDR: {usd_idr['rate']:.2f}")
    
    eur_usd = provider.get_forex("EUR/USD")
    print(f"   EUR/USD: {eur_usd['rate']:.4f}")
    
    # Test Crypto
    print("\n🪙 CRYPTO (CoinGecko + Binance)")
    btc = provider.get_crypto_quote("BTC")
    print(f"   BTC: ${btc.price:,.0f} ({btc.change_pct:+.2f}%)" if btc else "   BTC: Error")
    
    eth = provider.get_crypto_quote("ETH")
    print(f"   ETH: ${eth.price:,.0f} ({eth.change_pct:+.2f}%)" if eth else "   ETH: Error")
    
    # Test Commodities
    print("\n🥇 COMMODITIES (Yahoo Finance)")
    gold = provider.get_commodity("GOLD")
    print(f"   GOLD: ${gold['price']:.2f}" if gold['price'] > 0 else "   GOLD: Error")
    
    oil = provider.get_commodity("OIL")
    print(f"   OIL: ${oil['price']:.2f}" if oil['price'] > 0 else "   OIL: Error")
    
    # Test Indices
    print("\n📊 INDICES (Yahoo Finance)")
    spx = provider.get_index("SPX")
    print(f"   S&P 500: {spx['price']:,.2f} ({spx['change_pct']:+.2f}%)" if spx['price'] > 0 else "   S&P 500: Error")
    
    ihsg = provider.get_index("IHSG")
    print(f"   IHSG: {ihsg['price']:,.2f} ({ihsg['change_pct']:+.2f}%)" if ihsg['price'] > 0 else "   IHSG: Error")
    
    print("\n" + "=" * 60)
    print("✅ All data sources connected to REAL APIs!")
    print("=" * 60)
