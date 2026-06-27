# engine.strategy.strategies.crypto_specific

## Class: 

Crypto-specific trading strategy.

Supports multiple sub-strategies via the 'mode' parameter:
- 'funding_rate_arb': Funding rate arbitrage between spot and perpetual
- 'liquidation_cascade': Detect and trade liquidation cascades
- 'on_chain': Trade based on on-chain metrics
- 'dex_arb': DEX arbitrage opportunity detection
- 'mev_aware': MEV-aware execution for Solana

Parameters:
    mode: Sub-strategy mode (default 'funding_rate_arb').
    lookback: Rolling window for calculations (default 24).
    entry_threshold: Entry threshold (varies by mode) (default 0.0003).
    exit_threshold: Exit threshold (default 0.0001).
    stop_loss_pct: Stop loss fraction (default 0.05).
    take_profit_pct: Take profit fraction (default 0.10).
    cascade_z_threshold: Z-score threshold for cascade detection (default 2.5).
    whale_threshold: Large transaction threshold in USD (default 1000000).
    funding_rate_column: Column name for funding rate data (default "funding_rate").
    open_interest_column: Column name for open interest (default "open_interest").
    symbol: Trading symbol (default "BTC").

**Methods:** __init__, required_columns, warmup_period, compute_funding_rate_signal, detect_liquidation_cascade, compute_on_chain_signal, detect_dex_arb, compute_mev_signal, generate_signal

*Line: 32*

---

## Function: 

*Line: 56*

---

## Function: 

*Line: 70*

---

## Function: 

*Line: 83*

---

## Function: 

Generate funding rate arbitrage signal.

When funding rate is significantly positive, perpetual traders pay
longs → short perp / long spot to collect funding.
When funding rate is significantly negative, do the opposite.

The annualized funding rate gives the expected carry:
    annualized_carry = funding_rate * 3 * 365  (3 funding periods/day on most exchanges)

Reference:
    Alexander & Dakos (2020), Economic Modelling, 87, 117-129.

Args:
    data: DataFrame with funding rate and price data.

Returns:
    Signal if funding rate opportunity exists.

*Line: 90*

---

## Function: 

Detect liquidation cascades from price and volume patterns.

A liquidation cascade is characterized by:
1. Sharp price decline (or rise) exceeding normal volatility
2. Volume spike well above average
3. Rapid price recovery (mean reversion after cascade)

We detect these using z-scores of returns and volume.

Reference:
    Baur & Dimpfl (2018), Economics Letters, 173, 148-151.

Args:
    data: OHLCV DataFrame.

Returns:
    Signal if cascade detected.

*Line: 181*

---

## Function: 

Generate signal based on on-chain metrics.

Indicators:
- Exchange net flow: large inflows = bearish, outflows = bullish
- Whale transaction count: increased whale activity signals major moves
- Exchange reserve changes

Reference:
    Harvey, Ramachandran, & Santoro (2021). DeFi and the Future of Finance. Wiley.

Args:
    data: DataFrame with on-chain columns.

Returns:
    Signal if on-chain condition met.

*Line: 276*

---

## Function: 

Detect DEX-CEX arbitrage opportunities.

Compares DEX and CEX prices for the same asset.
If DEX price < CEX price: buy on DEX, sell on CEX.
If DEX price > CEX price: sell on DEX, buy on CEX.

Reference:
    Daian et al. (2020). "Flash Boys 2.0." IEEE S&P.

Args:
    data: DataFrame with 'dex_price' and 'cex_price' columns.

Returns:
    Signal if arb opportunity exists.

*Line: 374*

---

## Function: 

Generate MEV-aware execution signal for Solana.

Analyzes priority fees and tips to determine optimal
execution timing and avoid MEV extraction.

Key metrics:
- Current tip level (higher = more MEV competition)
- Priority fee percentile (avoid high-fee environments)
- Compute unit price trends

Reference:
    Daian et al. (2020). "Flash Boys 2.0." IEEE S&P.

Args:
    data: DataFrame with Solana-specific columns.

Returns:
    Signal with MEV-aware execution recommendation.

*Line: 448*

---

## Function: 

Generate crypto-specific signal based on selected mode.

Dispatches to the appropriate sub-strategy based on self.mode.

Args:
    data: DataFrame with required columns for the mode.

Returns:
    Signal if condition met, None otherwise.

*Line: 544*

---

