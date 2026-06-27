# agents.researcher.tools

## Function: 

Lazy-load SentimentTool from shared tools.

*Line: 37*

---

## Function: 

Lazy-load MarketDataTool from shared tools.

*Line: 47*

---

## Function: 

Lazy-load settings for API keys.

*Line: 57*

---

## Function: 

*Line: 213*

---

## Function: 

*Line: 230*

---

## Function: 

*Line: 253*

---

## Function: 

*Line: 273*

---

## Function: 

Search the web for financial information and market data.

PRODUCTION: Attempts to use configured search APIs (Tavily, SerpAPI).
Falls back to mock data only in _MOCK_MODE.

Args:
    query: Search query string
    num_results: Number of results to return (default: 5)

Returns:
    JSON string with search results

*Line: 298*

---

## Function: 

Retrieve SEC filing data for a given symbol.

PRODUCTION: Uses SEC EDGAR API for real filing data.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Stock ticker symbol (e.g., AAPL)
    filing_type: Type of SEC filing (10-K, 10-Q, 8-K, DEF 14A)
    years: Number of years of filings to retrieve

Returns:
    JSON string with SEC filing data

*Line: 367*

---

## Function: 

Fetch recent news articles for a given symbol.

PRODUCTION: Uses SentimentTool for real news aggregation from
Alpha Vantage, Polygon, and yfinance APIs.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Stock ticker symbol
    days_back: Number of days to look back (default: 7)
    category: Optional news category filter (earnings, mergers, regulatory, etc.)

Returns:
    JSON string with news articles

*Line: 441*

---

## Function: 

Retrieve financial data for a given symbol.

PRODUCTION: Uses yfinance for real financial data (overview, income,
balance, cashflow, metrics).
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Stock ticker symbol
    data_type: Type of financial data (overview, income, balance, cashflow, metrics)
    period: Data period (annual, quarterly)

Returns:
    JSON string with financial data

*Line: 488*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 21*

---

## Function: 

*Line: 25*

---

