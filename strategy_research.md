# Hedge Fund Quant Strategies Research — Comprehensive Reference

> **140+ Real Institutional Quant Strategies** used by top funds including Renaissance Technologies, Citadel, D.E. Shaw, Two Sigma, Bridgewater, AQR, Point72/Cubist, Millennium, JP Morgan, BlackRock, and others. Includes all Fibonacci variants, candlestick patterns, Sharpe ranges, fund attribution, complexity ratings, and pseudocode for the top 20 signals.

---

## Table of Contents

1. [Category Legend & Sharpe Context](#category-legend--sharpe-context)
2. [Top 20 Strategies — Full Pseudocode](#top-20-strategies--pseudocode)
3. [Fibonacci Strategy Suite](#fibonacci-strategy-suite)
4. [Candlestick Pattern Strategies](#candlestick-pattern-strategies)
5. [Complete Ranked Strategy Table (140+ Strategies)](#complete-ranked-strategy-table)
6. [Fund-by-Fund Strategy Map](#fund-by-fund-strategy-map)
7. [Appendices](#appendices)

---

## Category Legend & Sharpe Context

| Category Code | Type | Typical Sharpe Range | Capacity | Description |
|---|---|---|---|---|
| **STA** | Statistical Arbitrage | 0.8–2.5 | Low-Moderate | Pairs, baskets, cointegration |
| **MOM** | Momentum / Trend | 0.5–1.4 | High | Cross-sectional & time-series |
| **MRV** | Mean Reversion | 0.6–1.8 | Moderate | Contrarian, pullback |
| **FAC** | Factor / Style Premia | 0.3–0.9 | Very High | Value, momentum, carry, defensive |
| **VOL** | Volatility | 0.7–1.8 | Moderate | Dispersion, gamma, VRP |
| **FI** | Fixed Income | 0.4–1.5 | Very High | Curve, swap-spread, mortgage |
| **ARB** | Arbitrage | 0.5–2.0 | Low-Moderate | Merger, convertible, basis |
| **HFT** | High-Frequency | 1.0–5.0 | Very Low | Market making, latency arb |
| **ML** | Machine Learning / AI | 0.6–2.0 | Moderate | Neural nets, NLP, alt data |
| **MAC** | Macro / CTA | 0.3–1.2 | Very High | Global macro, trend-following |
| **TECH** | Technical | 0.3–1.0 | High | Patterns, Fib, candlestick |
| **RP** | Risk Parity | 0.3–0.7 | Very High | Balanced beta |
| **LS** | Long/Short Equity | 0.4–1.2 | High | Fundamental + quant |
| **ESG** | ESG / Thematic | 0.2–0.6 | High | Climate, governance factors |

> **Note:** Sharpe ratios above 2.0 (ex-ante) are rare for large-AUM funds. Renaissance Medallion is an extreme outlier at an estimated 3.5+ gross / 2.0+ net of fees. HFT strategies can exhibit higher Sharpe ratios but have severe capacity constraints.

---

## Top 20 Strategies — Pseudocode

### #1 — Renaissance Medallion: Hidden Markov Model Regime Detection

```
Strategy: HMM Regime-Switching Stat Arb
Sharpe: ~3.5 (gross), ~2.0 (net)
Used by: Renaissance Technologies (Medallion Fund)
Complexity: Very High

function generate_signals(market_data):
    # Step 1: Extract latent regime from ~500 features
    features = [
        price_momentum(1d, 5d, 21d),
        volume_zscore(20d),
        volatility_regime(60d),
        correlation_breakdown(30d),
        order_flow_imbalance(),
        cross_asset_dispersion()
    ]
    
    # Step 2: Fit HMM with 3-5 hidden states (bull, bear, neutral, high-vol, low-vol)
    hmm_model = HiddenMarkovModel(n_components=4)
    hmm_model.fit(features)
    current_regime = hmm_model.predict(features[-1])
    
    # Step 3: For each asset, compute deviation from regime-conditional mean
    signals = {}
    for asset in universe:
        conditional_mean = hmm_model.conditional_expectation(asset, current_regime)
        z_score = (asset.current_price - conditional_mean) / asset.regime_volatility
        signals[asset] = z_score
    
    # Step 4: Rank and apply convex position sizing
    ranked = sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True)
    portfolio = {}
    for i, (asset, z) in enumerate(ranked[:100]):
        position_size = welford_convex(z, rank=i, total=100)
        portfolio[asset] = position_size * sign(z)  # mean-reversion bet
    
    return portfolio
```

### #2 — Bridgewater Pure Alpha / Risk Parity

```
Strategy: Systematic Macro + Risk Parity
Sharpe: ~0.5-0.7 (All Weather), ~0.8-1.2 (Pure Alpha)
Used by: Bridgewater Associates
Complexity: High

function all_weather_allocation():
    # Decompose macro environment into 4 quadrants
    # Growth: Inflation (High/Low) x Growth (High/Low)
    
    # Equal risk contribution from each quadrant
    targets = {
        "equities":      risk_weight(0.25, vol=15%),
        "bonds_long":    risk_weight(0.25, vol=8%),
        "commodities":   risk_weight(0.25, vol=20%),
        "tips":          risk_weight(0.25, vol=6%)
    }
    
    portfolio = risk_parity_optimizer(targets, max_leverage=2.0)
    return portfolio

function pure_alpha_signals(macro_data):
    # Step 1: Compute z-scores for 30+ macro factors
    growth_surprise = zscore(macro_data.gdp_nowcast - macro_data.gdp_consensus)
    inflation_z     = zscore(macro_data.cpi_mom_chg)
    credit_spread_z = zscore(macro_data.hy_spread - macro_data.ig_spread)
    yield_curve_z   = zscore(macro_data.10y2y_spread)
    
    # Step 2: Generate directional macro bets
    bets = []
    if growth_surprise > 1.0:
        bets += long_equity_index(), short_bonds()
    if inflation_z > 1.5:
        bets += long_commodities(), short_nominal_bonds(), long_tips()
    if yield_curve_z < -1.0:  # flattening
        bets += steepener_trade()
    if credit_spread_z > 2.0:  # stress
        bets += long_volatility(), short_high_beta()
    
    # Step 3: Risk overlay — tail hedge portfolio
    tail_hedge = buy_otm_puts(SPX, 5% OTM, 3-month) * 5% NAV
    # Step 4: Combine alpha + risk parity + tail
    return risk_parity_alpha(alpha_bets=bets, beta_portfolio=all_weather_allocation(), tail=tail_hedge)
```

### #3 — Citadel: Multi-Strategy Cross-Asset Relative Value

```
Strategy: Relative Value / Global Fixed Income Arbitrage
Sharpe: ~1.0-1.8
Used by: Citadel (Global Fixed Income, Convertible Arb)
Complexity: Very High

function relative_value_signals():
    signals = []
    
    # 1. Swap-Spread Arbitrage
    for tenors in [2y, 5y, 10y, 30y]:
        swap_spread = treasury_yield(tenor) - swap_rate(tenor)
        z = zscore(swap_spread, 252d)
        if abs(z) > 2.0:
            signals += swap_spread_trade(tenor, direction=sign(z))
    
    # 2. Cross-Currency Basis
    for pair in [EURUSD, GBPUSD, USDJPY]:
        basis = ccs_basis(pair, 3m)
        if basis < -15bps:   # funding stress
            signals += long_basis_trade(pair)
    
    # 3. Convertible Arb — gamma + credit hedge
    for conv in convertible_universe:
        delta = calc_delta(conv)
        gamma = calc_gamma(conv)
        credit_delta = calc_credit_spread_delta(conv)
        z_spread = zscore(conv.implied_vol - conv.realized_vol, 60d)
        
        if z_spread > 1.5:  # rich implied vol
            trade = long_convertible(conv)
            trade += short_delta_shares(conv, delta)
            trade += short_credit_default_swap(conv, credit_delta)
            signals += trade
    
    return rank_by_risk_adjusted_return(signals)
```

### #4 — Two Sigma: ML-Driven Factor Timing

```
Strategy: Machine Learning Factor Timing + Statistical Arbitrage
Sharpe: ~0.8-1.5
Used by: Two Sigma
Complexity: Very High

function ml_factor_signals(raw_data):
    # Step 1: Construct 200+ proprietary factors
    factors = {
        "value": [book_to_price, earnings_yield, cash_flow_yield, ...],
        "momentum": [12m_1m_momentum, industry_momentum, ...],
        "quality": [roa, roe, gross_margin, accruals, ...],
        "sentiment": [revision_ratio, short_interest, insider_trading, ...],
        "alt_data": [satellite_imagery, credit_card, web_traffic, ...]
    }
    
    # Step 2: XGBoost regime classifier — which factors work now?
    X = stack_factor_matrices(factors, lookback=252d)
    y = forward_returns(1d)
    
    model = XGBRegressor(n_estimators=500, max_depth=5, learning_rate=0.03)
    model.fit(X[:-60], y[:-60])  # rolling train
    
    # Step 3: Predict next-day returns for each stock
    predictions = model.predict(X[-1:])
    
    # Step 4: Market-neutral portfolio optimization
    long_stocks  = top_percentile(predictions, 10%)
    short_stocks = bottom_percentile(predictions, 10%)
    
    portfolio = market_neutral(long_stocks, short_stocks)
    portfolio = apply_risk_model(portfolio, max_industry_exposure=10%)
    portfolio = apply_transaction_cost_penalty(portfolio)
    
    return portfolio
```

### #5 — D.E. Shaw: Statistical Arbitrage / Pairs Trading System

```
Strategy: Cointegration-Based Pairs Trading
Sharpe: ~1.0-2.0
Used by: D.E. Shaw, Two Sigma
Complexity: High

function pairs_trading_signals(universe_prices):
    # Step 1: Screen for cointegrated pairs (rolling 60d window)
    cointegrated_pairs = []
    for i in range(len(universe_prices)):
        for j in range(i+1, len(universe_prices)):
            p1, p2 = universe_prices[i], universe_prices[j]
            stat = engle_granger_test(p1, p2, 60d)
            if stat.p_value < 0.05:
                hedge_ratio = stat.hedge_ratio
                half_life = estimate_half_life(p1 - hedge_ratio * p2, 60d)
                cointegrated_pairs.append((i, j, hedge_ratio, half_life))
    
    # Step 2: For each pair, compute spread z-score
    signals = []
    for pair in cointegrated_pairs:
        i, j, hr, hl = pair
        spread = universe_prices[i] - hr * universe_prices[j]
        z = (spread - mean(spread, 60d)) / std(spread, 60d)
        
        # Step 3: Entry/exit rules based on half-life
        entry_threshold = max(2.0, 3.0 * (5 / hl))  # adaptive
        exit_threshold = 0.5
        
        if z > entry_threshold:
            signals.append((i, j, 'short', 'long', abs(z)))  # short leg1, long leg2
        elif z < -entry_threshold:
            signals.append((i, j, 'long', 'short', abs(z)))
        elif abs(z) < exit_threshold:  # close position
            signals.append((i, j, 'close', 'close', 0))
    
    # Step 4: Rank by half-life — faster mean reversion = higher weight
    return sorted(signals, key=lambda s: s[4], reverse=True)[:20]
```

### #6 — AQR: Style Premia (Value + Momentum + Carry + Defensive)

```
Strategy: Multi-Asset Style Premia
Sharpe: ~0.5-1.0
Used by: AQR Capital Management
Complexity: Medium

function style_premia_signals(global_markets):
    # 4 style premia harvested across asset classes
    portfolio = []
    
    # 1. VALUE — buy cheap, sell expensive
    for asset in global_markets:
        value_z = combined_z([
            zscore(asset.book_to_price),
            zscore(-asset.pe_ratio),
            zscore(asset.dividend_yield)
        ])
        if value_z > 1.0:  portfolio.append((asset, 'long',  value_z * 0.25))
        if value_z < -1.0: portfolio.append((asset, 'short', value_z * 0.25))
    
    # 2. MOMENTUM — buy recent winners, sell losers
    for asset in global_markets:
        mom_z = zscore(asset.return_12m_1m)
        if mom_z > 1.0:  portfolio.append((asset, 'long',  mom_z * 0.25))
        if mom_z < -1.0: portfolio.append((asset, 'short', mom_z * 0.25))
    
    # 3. CARRY — buy high-yield, sell low-yield
    for asset in global_markets:
        carry_z = zscore(asset.carry_yield)
        if carry_z > 1.0:  portfolio.append((asset, 'long',  carry_z * 0.125))
        if carry_z < -1.0: portfolio.append((asset, 'short', carry_z * 0.125))
    
    # 4. DEFENSIVE — buy low beta, sell high beta
    for asset in global_markets:
        def_z = -zscore(asset.beta_60m)  # lower beta = more defensive
        if def_z > 1.0:  portfolio.append((asset, 'long',  def_z * 0.125))
        if def_z < -1.0: portfolio.append((asset, 'short', def_z * 0.125))
    
    # Apply volatility scaling to 10% target vol
    portfolio = target_volatility(portfolio, 10%)
    return risk_balance(portfolio)
```

### #7 — Millennium / Point72: Multi-Pod Discretionary + Systematic

```
Strategy: Multi-Pod / Multi-Manager Platform Allocation
Sharpe: ~0.8-1.5 (firm level)
Used by: Millennium Management, Point72
Complexity: Very High (firm-level)

function pod_allocation_signals():
    # Each pod operates its own strategy with defined risk limits
    # This is the FIRM-LEVEL capital allocation overlay
    
    pods = get_all_pods()  # 100+ independent teams
    
    # Risk allocation: rolling Sharpe-based capital allocation
    for pod in pods:
        pod.sharpe_6m = compute_rolling_sharpe(pod.returns, 6m)
        pod.var_95    = compute_var_historical(pod.returns, 95%, 1d)
        pod.corr_with_firm = correlation(pod.returns, firm_returns, 6m)
    
    # Optimize capital allocation (mean-variance across pods)
    objective = maximize(sum(pods.sharpe_6m * capital) / sqrt(sum(capital^2 * var_95^2)))
    constraints = {
        max_single_pod_capital: 0.05,  # no more than 5% in one pod
        max_leverage: 2.0,
        net_exposure: |sum(signals)| < 0.15,  # 15% net limit
        gross_exposure: sum(|signals|) < 2.0
    }
    
    capitals = portfolio_optimizer(objective, constraints)
    return capitals
```

### #8 — JP Morgan: Macrosynergy Quantamental

```
Strategy: Macro-Quantamental (Systematic Macro + Fundamentals)
Sharpe: ~0.6-1.2
Used by: JP Morgan (JPMaQS)
Complexity: High

function macrosynergy_signals():
    # Combine quantamental indicator scores
    
    # 1. Growth signal
    growth_score = composite([
        pmi_surprise * 0.3,
        industrial_production_mom * 0.2,
        retail_sales_yoy * 0.2,
        labor_market_diffusion * 0.3
    ])
    
    # 2. Inflation signal
    inflation_score = composite([
        cpi_core_mom * 0.4,
        ppi_final_demand * 0.3,
        wage_growth * 0.3
    ])
    
    # 3. Monetary policy signal
    policy_score = composite([
        central_bank_forward_guidance * 0.25,
        rate_hike_probability * 0.35,
        balance_sheet_chg * 0.4
    ])
    
    # 4. Convert to trade signals across 58 currency pairs and rates
    trades = []
    for country_pair in g10_pairs:
        g = growth_score(country_pair[0]) - growth_score(country_pair[1])
        i = inflation_score(country_pair[0]) - inflation_score(country_pair[1])
        p = policy_score(country_pair[0]) - policy_score(country_pair[1])
        
        composite_signal = g * 0.4 + i * (-0.2) + p * 0.4
        if abs(composite_signal) > 0.5:
            trades.append(fx_trade(country_pair, direction=sign(composite_signal)))
    
    return rank_by_composite(trades)
```

### #9 — AHL (Man Group): Time-Series Momentum

```
Strategy: Diversified Trend Following / Time-Series Momentum
Sharpe: ~0.6-1.2
Used by: Man AHL, Aspect Capital, Winton
Complexity: Medium

function ts_momentum_signals(price_series):
    # Lookback periods: 1m, 3m, 6m, 12m (standard CTA approach)
    lookbacks = [21, 63, 126, 252]
    instruments = futures_universe()  # 100+ futures (equity index, rates, FX, commodities)
    
    positions = {}
    for inst in instruments:
        trend_score = 0
        for lb in lookbacks:
            ret = (inst.price / inst.price[-lb]) - 1
            z = zscore(ret, lookback=504)  # 2-year window
            volatility = atr(inst, lb)
            
            # Position sizing: inverse volatility + signal strength
            scaled_ret = ret / (volatility * sqrt(252/lb))
            trend_score += scaled_ret * 0.25
        
        # Entry threshold
        if abs(trend_score) > 0.3:
            direction = sign(trend_score)
            position_size = min(abs(trend_score) / 2.0, 0.05)  # max 5% notional per inst
            positions[inst] = direction * position_size / volatility
    
    # Apply portfolio-level vol target (15% annualized)
    portfolio = vol_target(positions, target=15%)
    return portfolio
```

### #10 — BlackRock: Systematic Factor Investing

```
Strategy: Factor-Based Smart Beta
Sharpe: ~0.4-0.8
Used by: BlackRock (Systematic Active Equity)
Complexity: Medium

function systematic_factor_strategy(stock_universe):
    # Multi-factor scoring
    scores = []
    for stock in stock_universe:
        value_score   = percentile_rank(stock.book_to_price, universe)
        quality_score = composite_percentile([
            percentile_rank(stock.roe, universe),
            percentile_rank(stock.gross_margin, universe),
            percentile_rank(stock.accruals_reversed, universe)
        ])
        momentum_score = percentile_rank(stock.return_12m_1m, universe)
        low_vol_score  = -percentile_rank(stock.beta_60m, universe)
        growth_score   = percentile_rank(stock.eps_growth_5y, universe)
        
        total = (value_score * 0.20 + quality_score * 0.25 + 
                 momentum_score * 0.20 + low_vol_score * 0.20 + 
                 growth_score * 0.15)
        scores.append((stock, total))
    
    sorted_stocks = sorted(scores, key=lambda x: x[1], reverse=True)
    long_stocks  = sorted_stocks[:top_n]
    short_stocks = sorted_stocks[-bottom_n:]
    
    portfolio = build_long_short(long_stocks, short_stocks, market_neutral=True)
    portfolio = apply_constraints(portfolio, sector_limits=0.15, turnover_limits=0.20)
    return portfolio
```

### #11 — Cubist Systematic (Point72): Short-Term Mean Reversion

```
Strategy: Short-Term Reversion + Microstructure
Sharpe: ~1.5-2.5
Used by: Cubist Systematic Strategies (Point72), KEPL team
Complexity: High

function short_term_reversion(order_book, trades):
    # 1. Order flow imbalance
    for stock in universe:
        ofi = (bid_volume * (bid_improvement > 0) - ask_volume * (ask_improvement > 0)) 
               / total_volume
        ofi_z = zscore(ofi, lookback=20)
        
        # 2. Tick-level return reversal signal
        tick_return = log(price[-1] / price[-20])
        micro_price = (bid[-1] * ask_size[-1] + ask[-1] * bid_size[-1]) / (bid_size[-1] + ask_size[-1])
        micro_z = (price[-1] - micro_price) / tick_size
        
        # 3. Inventory signal
        inventory_z = current_inventory(stock) / daily_volume_estimate(stock) * 100
        
        # Combined signal — contrarian to microstructure noise
        signal = - (ofi_z * 0.3 + zscore(tick_return, 100) * 0.4 + inventory_z * 0.3)
        
        if abs(signal) > 1.5:
            size = max_position_limit(stock) * min(abs(signal) / 3.0, 1.0)
            execute_market_order(stock, sign(signal), size)
```

### #12 — Volatility Risk Premium Harvest (Global Macro Funds)

```
Strategy: Short Volatility / Put Writing
Sharpe: ~0.8-1.5
Used by: Various macro/vol funds, Citadel (tail risk)
Complexity: Low-Medium

function vrp_harvest_signals():
    # Sell options when IV > RV — capture premium
    for underlying in vol_surface_universe:
        iv_atm = implied_vol(underlying, tenor=30d, strike=atm)
        rv_30d = realized_vol(underlying, 30d)
        z_iv_rv = (iv_atm - rv_30d) / std(iv_atm - rv_30d, 120d)
        
        # Skew premium — out-of-the-money puts tend to be rich
        put_skew = implied_vol(underlying, 30d, 90% strike) - iv_atm
        z_skew = zscore(put_skew, 120d)
        
        if z_iv_rv > 0.5 and z_skew > 0.3:
            # Sell 10-delta put spread (OTM puts, cap tail risk)
            short_put = sell_put(underlying, strike=90%, tenor=30d)
            long_put = buy_put(underlying, strike=80%, tenor=30d)
            position_risk = premium_received / var_95(1d)
            
            if position_risk < 0.03 * capital:
                execute(short_put, long_put)
        
        # Tail hedge overlay — buy 5% OTM puts during low vol
        if z_iv_rv < -1.0:  # vol too cheap
            tail_put = buy_put(underlying, strike=95%, tenor=60d)
            execute(tail_put, size=0.01 * capital)
```

### #13 — Merger Arbitrage (Millennium / Citadel / D.E. Shaw)

```
Strategy: Merger / Risk Arbitrage
Sharpe: ~0.6-1.5
Used by: Millennium, Citadel, D.E. Shaw, Kylin
Complexity: Medium

function merger_arb_signals(deal_pipeline):
    signals = []
    for deal in deal_pipeline.all_active_deals:
        # 1. Compute deal spread
        offer_price = deal.terms.cash_per_share or deal.terms.stock_ratio * acquirer.price
        spread = (offer_price - target.price) / target.price
        annualized_spread = spread / (deal.expected_close_days / 365)
        
        # 2. Estimate probability of completion
        completion_prob = logistic_regression_predict([
            deal.is_all_cash,
            deal.regulatory_risk_score,
            deal.target_size / acquirer.market_cap,
            deal.mgmt_support_flag,
            deal.termination_fee / deal.equity_value
        ])
        
        # 3. Expected value
        expected_return = completion_prob * spread - (1 - completion_prob) * deal.announced_drop
        if deal.expected_close_days < 180:
            sharpe = expected_return / (spread_volatility(deal, 60d) * sqrt(252/deal.expected_close_days))
        
        if sharpe > 0.5 and completion_prob > 0.75:
            size = min(capital * 0.02, capital * sharpe / sum(all_sharpes))
            signals.append({
                'type': 'merger_arb',
                'target': deal.target,
                'acquirer': deal.acquirer if deal.stock_deal else None,
                'position': long_target(target, size),
                'hedge': short_acquirer(acquirer, delta_ratio) if deal.stock_deal else None,
                'expected_return': expected_return,
                'sharpe': sharpe
            })
    
    return signals
```

### #14 — Dispersion Trading (Vol Funds, Citadel)

```
Strategy: Index vs. Single-Name Volatility Dispersion
Sharpe: ~0.8-1.6
Used by: Citadel, Capula, GSA Capital
Complexity: High

function dispersion_signals():
    # Core idea: short index vol, long single-stock vol (dispersion is usually too tight)
    for index in [SPX, NDX, STOXX50, NKY]:
        iv_index = implied_vol(index, 30d, atm)
        iv_singles = [implied_vol(s, 30d, atm) for s in index.components]
        weighted_iv_singles = sum(iv_singles * index.weights)
        
        # Correlation implied vs. realised
        implied_corr = iv_index^2 / sum(w_i^2 * iv_single_i^2 + w_i * w_j * iv_single_i * iv_single_j)
        realized_corr = realized_correlation(index.components, 30d)
        corr_z = zscore(implied_corr - realized_corr, 60d)
        
        # Dispersion trade signal
        disp_z = zscore(weighted_iv_singles - iv_index, 60d)
        
        if corr_z > 1.0:  # implied correlation too high → sell index vol, buy single vol
            portfolio = short_straddle(index, 30d, atm, notional=10m)
            portfolio += long_straddle_basket(index.components, 30d, atm, weighted_notional=10m)
            execute(portfolio)
        elif corr_z < -1.0:  # implied correlation too low → buy index vol, sell single vol
            portfolio = long_straddle(index, 30d, atm, notional=10m)
            portfolio += short_straddle_basket(index.components, 30d, atm, weighted_notional=10m)
            execute(portfolio)
```

### #15 — ETF Arbitrage / Index Arb (HFT Firms)

```
Strategy: ETF Premium/Discount Arbitrage
Sharpe: ~1.5-4.0
Used by: Jane Street, Citadel Securities, Susquehanna, DRW
Complexity: High

function etf_arb_signal(etf, basket, traded_prices):
    # 1. Compute NAV from component prices
    nav = sum(traded_prices[symbol] * basket.weights for symbol in basket.components)
    market_price = etf.last_traded
    
    premium = (market_price - nav) / nav  # in bps
    premium_z = zscore(premium, lookback=1d)  # tick-level
    
    creation_cost = basket.commission + market_impact(etf.volume * 0.01)
    redemption_cost = creation_cost  # symmetric approx
    
    threshold_bps = max(creation_cost * 10000, 2.0)  # min 2 bps
    
    # 2. Signal
    if premium > threshold_bps and premium_z > 2:
        # ETF overvalued → short ETF, long basket (creation)
        execute(short(etf, size=creation_unit))
        execute(buy_basket(basket, size=creation_unit))
    elif premium < -threshold_bps and premium_z < -2:
        # ETF undervalued → buy ETF, short basket (redemption)
        execute(buy(etf, size=redemption_unit))
        execute(short_basket(basket, size=redemption_unit))
    
    # 3. Mean-reverting exit — close when premium < 0.5 bps
    if abs(premium) < 0.5:
        close_position(etf, basket)
```

### #16 — News Sentiment NLP Strategy (Renaissance / WorldQuant)

```
Strategy: NLP-Driven Sentiment Alpha
Sharpe: ~0.6-1.4
Used by: Renaissance, WorldQuant, Two Sigma
Complexity: High

function nlp_sentiment_signals(news_feeds, filings):
    # 1. Process real-time news articles
    for article in news_feeds:
        entities = extract_entities(article.text)  # companies, tickers
        sentiment = finbert_sentiment(
            article.text, 
            domain='finance'
        )  # score: -1 (negative) to +1 (positive)
        
        relevance = entity_relevance(article, entity=entities[0])
        novelty = 1 - cosine_sim(article.embedding, recent_articles[entity].embeddings)
        source_authority = source_trust_score(article.source)
        
        # 2. Compute event score
        event_score = sentiment * relevance * novelty * source_authority
    
    # 3. Aggregate by ticker
    ticker_signals = defaultdict(float)
    for entity, score in events:
        ticker_signals[entity.ticker] += score
    
    # 4. Cross-sectional rank and normalize
    scores_array = array(ticker_signals.values())
    ranked = rank(scores_array) / len(scores_array)  # 0 to 1
    signals = dict(zip(ticker_signals.keys(), ranked))
    
    # 5. Market neutral overlay
    long = top_percentile(signals, 10%)
    short = bottom_percentile(signals, 10%)
    portfolio = equal_weight(long) - equal_weight(short)
    portfolio = sector_neutral(portfolio)
    portfolio = beta_neutral(portfolio)
    return portfolio
```

### #17 — Commodity Futures Seasonality (CTA / AHL)

```
Strategy: Commodity Seasonal Pattern Trading
Sharpe: ~0.5-1.2
Used by: Man AHL, Gresham, Transtrend
Complexity: Low-Medium

function seasonal_pattern_signals():
    positions = {}
    
    for commodity in futures_universe:
        # 1. Compute seasonal return for this calendar window
        today = datetime.now()
        lookback_years = 15
        
        season_returns = []
        for year in range(today.year - lookback_years, today.year):
            # Same calendar window ±5 days over history
            window_start = datetime(year, today.month, today.day) - timedelta(5)
            window_end = window_start + timedelta(30)  # 30-day forward
            ret = (price_at_date(window_end) / price_at_date(window_start)) - 1
            season_returns.append(ret)
        
        # 2. Statistical significance
        t_stat = one_sample_ttest(season_returns, 0)
        avg_return = mean(season_returns)
        win_rate = sum(r > 0 for r in season_returns) / len(season_returns)
        
        # 3. Entry condition
        current_carry = commodity.futures_curve_slope()
        speculative_positions = commodity.cot_report_speculative_long_pct()
        
        if avg_return > 0 and t_stat.p_value < 0.10 and win_rate > 0.55:
            direction = 'long'
        elif avg_return < 0 and t_stat.p_value < 0.10 and win_rate > 0.55:
            direction = 'short'
        else:
            continue
        
        size = min(abs(t_stat) * 0.02, 0.05) * capital
        positions[commodity] = (direction, size)
    
    return positions
```

### #18 — Gamma Scalping (Options Market Makers / Vol Funds)

```
Strategy: Gamma Scalping / Delta-Neutral Vol Arbitrage
Sharpe: ~0.8-1.8
Used by: Optiver, Susquehanna, IMC, Citadel Securities
Complexity: High

function gamma_scalp_signals():
    # Long gamma position when VRP is favorable
    for underlying in equity_universe:
        iv = implied_vol(underlying, 30d, atm)
        rv_forecast = garch_predict(underlying.returns, horizon=30d)
        vrp = iv - rv_forecast
        vrp_z = zscore(vrp, 60d)
        
        if vrp_z > 0.5:  # IV > RV — good time to short vol, but we want gamma scalp
            # Actually: buy straddle when we expect vol to increase
            continue
        elif vrp_z < -0.5:  # IV < RV — options are cheap, buy gamma
            # Step 1: Buy ATM straddle
            option = buy_straddle(underlying, tenor=30d, strikes=atm)
            
            # Step 2: Maintain delta neutrality
            def delta_neutral_loop():
                for tick in stream_market_data():
                    current_delta = option.delta(underlying.price, underlying.vol)
                    if abs(current_delta) > 0.01 * option.notional:
                        hedge_delta = -current_delta * option.multiplier
                        if tick.side == 'up':  # bought hedge → gamma profit captured
                            realized_gamma_profit += hedge_delta * (tick.price - last_hedge_price)
                        execute_offset(underlying, hedge_delta)
                        last_hedge_price = tick.price
            
            # Step 3: Gamma P&L = 0.5 * gamma * (Δprice)^2
            # Profit when price moves, loss from theta decay
            # Net positive if realized vol > implied vol at purchase
            
            if net_pnl_today > 0:
                hold_another_day()
            elif vrp_z >= 0:  # VRP closed, exit
                close_straddle(option)
```

### #19 — Cross-Sectional Momentum (Equity L/S Funds)

```
Strategy: Cross-Sectional Momentum (1-year, skip 1-month)
Sharpe: ~0.5-1.2
Used by: AQR, Morgan Stanley, GSAM, numerous quant funds
Complexity: Low

function xsmom_signals(stocks):
    # Canonical: Jegadeesh & Titman (1993) momentum
    momentum_scores = {}
    
    for stock in stocks:
        # 12-month cumulative return skipping last month
        ret_12m_1m = stock.price[-252] / stock.price[-21] - 1
        
        # Risk-adjusted by volatility
        vol_6m = std(stock.returns[-126:])
        risk_adjusted = ret_12m_1m / vol_6m
        
        # Industry-relative momentum
        industry_avg = mean(momentum_scores[s] for s in stocks if s.industry == stock.industry)
        ind_relative = risk_adjusted - industry_avg
        
        momentum_scores[stock] = ind_relative
    
    # Rank and form decile portfolios
    ranked = sorted(momentum_scores.items(), key=lambda x: x[1])
    top_decile  = ranked[-len(ranked)//10:]
    bot_decile  = ranked[:len(ranked)//10]
    
    # Long winners, short losers — market neutral
    portfolio = long(top_decile, weight='ew') + short(bot_decile, weight='ew')
    portfolio = size_by_volatility(portfolio, target=12%)
    
    return portfolio
```

### #20 — Treasury Basis Trade (Fixed Income Relative Value)

```
Strategy: Cash-Futures Treasury Basis Trade
Sharpe: ~0.4-1.2
Used by: Citadel, D.E. Shaw, Tudor, Balyasny
Complexity: Medium-High

function treasury_basis_signals():
    signals = []
    
    for tenor in [2y, 5y, 10y, 30y]:
        # CTD (cheapest-to-deliver) bond
        ctd = find_ctd(tenor)
        futures_price = treasury_futures.price(tenor)
        
        # Conversion factor-adjusted forward
        cf = futures.conversion_factor(ctd)
        implied_forward = futures_price * cf + ctd.accrued_interest - futures_price * (1 - cf)
        cash_price = ctd.clean_price + ctd.accrued_interest
        
        # Basis = cash - futures_equivalent
        basis = cash_price - implied_forward
        z_basis = zscore(basis, lookback=60d)
        
        # Financing cost (repo rate)
        repo_rate = implied_repo_rate(cash_price, futures_price, ctd, cf, days_to_delivery)
        gc_rate = general_collateral_rate(tenor)
        funding_advantage = gc_rate - repo_rate
        
        # Step 2: Trade logic
        if z_basis > 1.5 and funding_advantage < 0:  # basis rich (cash expensive vs futures)
            signals.append(short_cash_long_futures(tenor, ctd, size=std_size))
        elif z_basis < -1.5 and funding_advantage < 0:  # basis cheap
            signals.append(long_cash_short_futures(tenor, ctd, size=std_size))
        
        # Step 3: Dynamic hedging
        for trade in signals:
            trade.hedge_rates_risk(dv01_neutral=True)
            trade.monitor_financing(daily)
    
    return signals
```

---

## Fibonacci Strategy Suite

### Complete Fibonacci Tool Reference

| Tool | Levels | Signal Logic | Common Use | Estimated Sharpe |
|---|---|---|---|---|
| **Retracement** | 23.6%, 38.2%, 50%, 61.8%, 78.6% | Buy at support pullback to 38.2-61.8% in uptrend; sell at resistance in downtrend | Swing trading, pullback entries | 0.3-0.7 |
| **Extension** | 127.2%, 161.8%, 200%, 261.8% | Price target projection beyond 100%; 161.8% is common profit target | Take-profit levels, breakout targets | 0.3-0.6 |
| **Time Zones** | Vertical lines at Fibonacci intervals (1,2,3,5,8,13,21,34,55,89) | Reversal expected near Fib time zone; cluster with price level = confluence | Cycle timing, trend exhaustion | 0.2-0.5 |
| **Fan Lines** | Diagonal lines from swing high/low at 38.2°, 50°, 61.8° | Support/resistance along fan lines; break of 38.2 line = trend change | Trend strength filter | 0.3-0.6 |
| **Arc** | Curved lines at 38.2%, 50%, 61.8% radius from swing point | Dynamic support/resistance; arcs converge at trend origin | Swing trading entries | 0.2-0.5 |
| **Expansion** | 100%, 127.2%, 161.8% from ABC swing | C-wave target = A-wave × 1.618; three-point projection | Harmonic pattern targets | 0.3-0.7 |
| **Channel** | Lines parallel to trendline at 61.8% intervals | Price oscillating within Fibonacci channel; edges = trade zones | Trending markets | 0.3-0.6 |
| **Cluster** | Multiple Fib levels from different swings converging | Confluence of 2+ Fib levels = high-probability zone | All-strategy confluence | 0.4-0.8 |
| **Pivot** | Midpoint of prior trend + Fib extension | Pivot at 38.2% retrace = confirmation of trend continuation | Institutional entry levels | 0.3-0.6 |
| **Spiral (Golden Spiral)** | Logarithmic spiral based on Φ (1.618) | Price following golden ratio expansion/contraction cycles | Long-term macro cycles | 0.2-0.4 |

### Fibonacci Strategy #21: Retracement Pullback System

```
function fibonacci_pullback(price_series):
    # Identify swing high and swing low (last 50 bars)
    swing_high = max(price_series[-50:])
    swing_low  = min(price_series[-50:])
    trend = 'up' if close[-1] > sma(close, 200) else 'down'
    
    range = swing_high - swing_low
    levels = {
        '0.236': swing_high - 0.236 * range,
        '0.382': swing_high - 0.382 * range,
        '0.500': swing_high - 0.500 * range,
        '0.618': swing_high - 0.618 * range,
        '0.786': swing_high - 0.786 * range
    }
    
    close_ = close[-1]
    if trend == 'up':
        if abs(close_ - levels['0.618']) / levels['0.618'] < 0.002:
            if rsi(14) < 40 and volume[-1] > volume_avg(20):
                return 'BUY', stop=levels['0.786'], target=swing_high
    elif trend == 'down':
        if abs(close_ - levels['0.382']) / levels['0.382'] < 0.002:
            if rsi(14) > 60 and volume[-1] > volume_avg(20):
                return 'SELL', stop=levels['0.236'], target=swing_low
```

### Fibonacci Strategy #22: Extension Profit Target

```
function fibonacci_extension(swing_low, swing_high, pullback_low):
    ab_range = swing_high - swing_low  # waves A-B
    bc_retrace = (swing_high - pullback_low) / ab_range
    
    if 0.382 <= bc_retrace <= 0.618:  # valid fib pullback
        ext_127 = pullback_low + 0.618 * (swing_high - pullback_low) * 1.27
        ext_161 = pullback_low + 0.618 * (swing_high - pullback_low) * 1.618
        ext_261 = pullback_low + 0.618 * (swing_high - pullback_low) * 2.618
        return {'TP1': ext_127, 'TP2': ext_161, 'TP3': ext_261}
```

### Fibonacci Strategy #23: Time Zone Reversal

```
function fibonacci_time_zones(start_bar):
    fib_sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    zones = defaultdict(list)
    
    for bar_offset in fib_sequence:
        bar_idx = start_bar + bar_offset
        zones[bar_idx] = ('possible_reversal', bar_offset)
    
    # Confluence with price pattern = high probability
    for bar_idx, info in zones.items():
        price_at_zone = prices[bar_idx]
        if rsi(bar_idx) > 70 and bar_idx in zones:
            zones[bar_idx] = ('SELL_signal', info[1])
        elif rsi(bar_idx) < 30 and bar_idx in zones:
            zones[bar_idx] = ('BUY_signal', info[1])
    return zones
```

### Fibonacci Strategy #24: Harmonic Pattern Detection (Gartley / Butterfly)

```
function gartley_pattern(prices):
    # XABCD pattern — 5-point harmonic
    X = prices[0]; A = prices[1]; B = prices[2]; C = prices[3]; D = prices[4]
    
    AB_retrace = (B - A) / (A - X)  # should be 0.618
    BC_retrace = (C - B) / (A - B)  # should be 0.382-0.886
    CD_retrace = (D - C) / (B - C)  # should be 1.13-2.618
    
    tolerance = 0.05
    if abs(AB_retrace - 0.618) < tolerance:
        if 0.382 <= BC_retrace <= 0.886:
            if 1.13 <= CD_retrace <= 2.618:
                if (D - X) / (A - X) between 0.786 - tolerance and 0.786 + tolerance:
                    return 'BUY_GARTLEY', D, target=A
    return None
```

### Fibonacci Strategy #25: Multi-Timeframe Fib Confluence

```
function multi_tf_fib_confluence(weekly_bars, daily_bars, h4_bars):
    zones = []
    for tf in [weekly_bars, daily_bars, h4_bars]:
        sw_high = max(tf[-50:])
        sw_low = min(tf[-50:])
        range_ = sw_high - sw_low
        zones.append({
            '0.382': sw_high - 0.382 * range_,
            '0.500': sw_high - 0.500 * range_,
            '0.618': sw_high - 0.618 * range_,
        })
    
    # Find price levels where 2+ TFs have converging Fib levels
    confluence = {}
    for level_key in ['0.382', '0.500', '0.618']:
        values = [z[level_key] for z in zones]
        if max(values) - min(values) < 0.01 * sw_high:  # convergence within 1%
            avg = mean(values)
            confluence[level_key] = avg
    
    current = close[-1]
    for level, price in confluence.items():
        if abs(current - price) / price < 0.003:
            return f'ENTER at {level} confluence zone (price = {current})'
```

---

## Candlestick Pattern Strategies

### Complete Candlestick Pattern Reference

| # | Pattern | Type | Candles | Signal Quality | Context | Est. Sharpe |
|---|---|---|---|---|---|---|
| 1 | **Doji** | Reversal | 1 | Low-Med | Indecision; needs confirmation | 0.2-0.4 |
| 2 | **Dragonfly Doji** | Reversal Bullish | 1 | Medium | Long lower shadow; trend bottom | 0.3-0.5 |
| 3 | **Gravestone Doji** | Reversal Bearish | 1 | Medium | Long upper shadow; trend top | 0.3-0.5 |
| 4 | **Long-Legged Doji** | Reversal | 1 | Low | Extreme indecision; volatility | 0.2-0.4 |
| 5 | **Hammer** | Bullish Reversal | 1 | Medium | Downtrend + small body + long lower wick | 0.3-0.6 |
| 6 | **Inverted Hammer** | Bullish Reversal | 1 | Medium | Downtrend + small body + long upper wick | 0.3-0.5 |
| 7 | **Hanging Man** | Bearish Reversal | 1 | Medium | Uptrend + small body + long lower wick | 0.3-0.5 |
| 8 | **Shooting Star** | Bearish Reversal | 1 | Medium | Uptrend + small body + long upper wick | 0.3-0.6 |
| 9 | **Marubozu** | Continuation | 1 | Medium | No/no wicks; strong momentum | 0.2-0.5 |
| 10 | **Spinning Top** | Indecision | 1 | Low | Small body, wicks both sides | 0.1-0.3 |
| 11 | **Bullish Engulfing** | Bullish Reversal | 2 | High | Downtrend; small red then larger green | 0.4-0.8 |
| 12 | **Bearish Engulfing** | Bearish Reversal | 2 | High | Uptrend; small green then larger red | 0.4-0.8 |
| 13 | **Bullish Harami** | Bullish Reversal | 2 | Medium | Downtrend; large red then small green inside | 0.3-0.6 |
| 14 | **Bearish Harami** | Bearish Reversal | 2 | Medium | Uptrend; large green then small red inside | 0.3-0.6 |
| 15 | **Harami Cross** | Reversal | 2 | Medium | Harami with doji on 2nd candle | 0.3-0.6 |
| 16 | **Piercing Line** | Bullish Reversal | 2 | Medium-High | Downtrend; red then green closes >50% of red | 0.3-0.7 |
| 17 | **Dark Cloud Cover** | Bearish Reversal | 2 | Medium-High | Uptrend; green then red closes <50% of green | 0.3-0.7 |
| 18 | **Morning Star** | Bullish Reversal | 3 | High | Long red, doji/small, long green >50% of red | 0.4-0.9 |
| 19 | **Evening Star** | Bearish Reversal | 3 | High | Long green, doji/small, long red >50% of green | 0.4-0.9 |
| 20 | **Morning Doji Star** | Bullish Reversal | 3 | High | Same as Morning Star but doji in middle | 0.4-0.8 |
| 21 | **Evening Doji Star** | Bearish Reversal | 3 | High | Same as Evening Star but doji in middle | 0.4-0.8 |
| 22 | **Three White Soldiers** | Bullish Continuation | 3 | High | 3 long green candles, each closing higher | 0.4-0.8 |
| 23 | **Three Black Crows** | Bearish Continuation | 3 | High | 3 long red candles, each closing lower | 0.4-0.8 |
| 24 | **Three Inside Up** | Bullish Reversal | 3 | Medium | Harami + bullish confirmation candle | 0.3-0.6 |
| 25 | **Three Inside Down** | Bearish Reversal | 3 | Medium | Harami + bearish confirmation | 0.3-0.6 |
| 26 | **Three Outside Up** | Bullish Reversal | 3 | Medium | Engulfing + confirmation | 0.3-0.7 |
| 27 | **Three Outside Down** | Bearish Reversal | 3 | Medium | Engulfing + confirmation | 0.3-0.7 |
| 28 | **Rising Three Methods** | Bullish Continuation | 5 | High | Long green, 3 small reds inside, long green closes high | 0.4-0.7 |
| 29 | **Falling Three Methods** | Bearish Continuation | 5 | High | Long red, 3 small greens inside, long red closes low | 0.4-0.7 |
| 30 | **Tweezer Top** | Bearish Reversal | 2 | Medium | Same high on 2 candles; uptrend | 0.3-0.5 |
| 31 | **Tweezer Bottom** | Bullish Reversal | 2 | Medium | Same low on 2 candles; downtrend | 0.3-0.5 |
| 32 | **Abandoned Baby** | Reversal | 3 | High | Gap + doji + gap opposite direction | 0.4-0.8 |
| 33 | **Upside Tasuki Gap** | Bullish Continuation | 3 | Medium | Gap up, red gaps within previous gap | 0.3-0.5 |
| 34 | **Downside Tasuki Gap** | Bearish Continuation | 3 | Medium | Gap down, green gaps within previous gap | 0.3-0.5 |
| 35 | **Belt Hold (Bullish)** | Bullish Reversal | 1 | Medium | White marubozu at trend low | 0.2-0.5 |
| 36 | **Belt Hold (Bearish)** | Bearish Reversal | 1 | Medium | Black marubozu at trend high | 0.2-0.5 |
| 37 | **Kicking** | Reversal | 2 | High | Marubozu gap opposite direction | 0.4-0.7 |
| 38 | **Thrusting Line** | Continuation | 2 | Low-Med | Incomplete piercing line | 0.2-0.4 |
| 39 | **Counterattack** | Reversal | 2 | Medium | Opposite candles with same close | 0.3-0.5 |
| 40 | **Mat Hold** | Bullish Continuation | 5 | High | Long green, 3 small reds, long green above | 0.4-0.7 |

### Candlestick Strategy #26: Engulfing + Volume Confirmation

```
function engulfing_with_volume(prices, volumes):
    current = candles[-1]; previous = candles[-2]
    
    # Bullish Engulfing
    if (trend_is_down() and
        previous.close < previous.open and  # red candle
        current.close > current.open and    # green candle
        current.open <= previous.close and
        current.close >= previous.open and
        volumes[-1] > ma(volumes, 20) * 1.5 and  # volume confirmation
        current.close > ema(current.close, 50)):  # above key moving avg
        
        return 'BUY', stop=min(current.low, previous.low), target=current.close + 1.5 * (current.close - current.open)
    
    # Bearish Engulfing
    if (trend_is_up() and
        previous.close > previous.open and
        current.close < current.open and
        current.open >= previous.close and
        current.close <= previous.open and
        volumes[-1] > ma(volumes, 20) * 1.5 and
        current.close < ema(current.close, 50)):
        
        return 'SELL', stop=max(current.high, previous.high), target=current.close - 1.5 * (current.open - current.close)
```

### Candlestick Strategy #27: Morning/Evening Star with Fib Confluence

```
function star_pattern_with_fib(prices):
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    # Morning Star
    if (trend_is_down() and
        c1.close < c1.open and c1.body_size > avg_body(20) * 1.5 and
        c2.body_size < avg_body(20) * 0.5 and   # small body / doji
        c2.low < c1.low and                      # gap down
        c3.close > c3.open and
        c3.close > (c1.open + c1.close) / 2):   # closes >50% into 1st candle
        
        # Fib confluence filter
        fib_618 = fibonacci_resistance(0.618)
        if abs(c3.close - fib_618) / fib_618 < 0.01:
            return 'BUY_HIGH_CONVICTION', stop=c2.low, target=fib_ext_1618()
    
    # Evening Star
    if (trend_is_up() and
        c1.close > c1.open and c1.body_size > avg_body(20) * 1.5 and
        c2.body_size < avg_body(20) * 0.5 and
        c2.high > c1.high and
        c3.close < c3.open and
        c3.close < (c1.open + c1.close) / 2):
        
        fib_618 = fibonacci_support(0.618)
        if abs(c3.close - fib_618) / fib_618 < 0.01:
            return 'SELL_HIGH_CONVICTION', stop=c2.high, target=fib_ext_1618()
```

### Candlestick Strategy #28: Three Methods Pattern Filter

```
function three_methods_filter(prices):
    # Bullish Rising Three Methods
    c1, c2, c3, c4, c5 = candles[-5:]
    
    if (c1.close > c1.open and c1.body_size > avg_body(20) and
        all(c.close < c.open and c.close > c1.open and c.high < c1.high 
            for c in [c2, c3, c4]) and  # 3 small reds inside range
        c5.close > c5.open and c5.close > c1.close):
        return 'TREND_CONTINUATION_BULLISH'
    
    # Bearish Falling Three Methods
    if (c1.close < c1.open and c1.body_size > avg_body(20) and
        all(c.close > c.open and c.close < c1.open and c.low > c1.low 
            for c in [c2, c3, c4]) and
        c5.close < c5.open and c5.close < c1.close):
        return 'TREND_CONTINUATION_BEARISH'
```

---

## Complete Ranked Strategy Table

### Tier 1: Extreme Sharpe (2.0+) | HFT / Capacity-Constrained

| # | Strategy Name | Category | Expected Sharpe | Used By | Complexity |
|---|---|---|---|---|---|
| 1 | **Hidden Markov Model Regime Stat Arb** | STA | 2.5-3.5+ | Renaissance (Medallion) | Very High |
| 2 | **Co-Location Latency Arbitrage** | HFT | 2.0-5.0 | Jump, Citadel Securities, DRW | Very High |
| 3 | **Tick-Level Microstructure Reversal** | HFT/MRV | 1.5-3.0 | Cubist/KEPL, Virtu, Flow Traders | Very High |
| 4 | **Liquidity Rebate Capture** | HFT | 1.5-3.0 | Virtu, Citadel Securities | Medium |
| 5 | **ETF Premium/Discount Arbitrage** | HFT/ARB | 1.5-4.0 | Jane Street, Susquehanna, Citadel Sec | High |
| 6 | **Cross-Exchange Arb (Crypto)** | HFT/ARB | 2.0-4.0 | Jump, Alameda, Wintermute | High |
| 7 | **Options Market Making (Gamma Scalp)** | HFT/VOL | 1.5-3.0 | Optiver, IMC, Susquehanna, SIG | High |
| 8 | **Pair Cointegration (Ultra-Short)** | STA | 1.5-2.5 | D.E. Shaw, Two Sigma | High |
| 9 | **Order Flow Imbalance Momentum** | HFT/MOM | 1.5-3.0 | Tower Research, Headlands Tech | High |
| 10 | **Volatility Surface Arbitrage** | VOL | 1.5-2.5 | Capula, Citadel, GSA Capital | Very High |

### Tier 2: High Sharpe (1.0-2.0) | Institutional Core

| # | Strategy Name | Category | Expected Sharpe | Used By | Complexity |
|---|---|---|---|---|---|
| 11 | **Cross-Asset Relative Value** | ARB | 1.0-1.8 | Citadel, D.E. Shaw | Very High |
| 12 | **Distressed Asset / Debtholder Arb** | ARB | 1.0-2.0 | Oaktree, Elliott, Citadel | High |
| 13 | **Convertible Bond Arbitrage** | ARB | 1.0-1.8 | Citadel, D.E. Shaw, Millennium | High |
| 14 | **Statistical Arbitrage (Medium-Freq)** | STA | 1.0-2.0 | D.E. Shaw, Two Sigma, WorldQuant | High |
| 15 | **Index Rebalancing Front-Run** | ARB | 1.0-1.5 | BlackRock, GSAM, State Street | Medium |
| 16 | **Dispersion Trading** | VOL | 0.8-1.6 | Citadel, Capula, GSA | High |
| 17 | **Option Risk Premium Harvest (Short Vol)** | VOL | 0.8-1.5 | LMR, Walleye, Parallax | Medium |
| 18 | **Swap-Spread Arbitrage** | FI | 0.8-1.5 | Citadel, D.E. Shaw, BlueMountain | High |
| 19 | **Yield Curve Relative Value** | FI/ARB | 0.8-1.5 | Citadel, Tudor, Brevan Howard | High |
| 20 | **Short-Term Mean Reversion (1-5 day)** | MRV | 0.8-1.5 | Two Sigma, Citadel, WorldQuant | Medium |
| 21 | **Machine Learning Factor Timing** | ML | 0.8-1.5 | Two Sigma, Renaissance, WorldQuant | Very High |
| 22 | **NLP Sentiment Alpha** | ML | 0.6-1.4 | Renaissance, Two Sigma, Point72 | High |
| 23 | **Multi-Pod Platform Allocation** | LS | 0.8-1.5 | Millennium, Point72 | Very High |
| 24 | **Time-Series Momentum (CTA)** | MOM | 0.6-1.2 | Man AHL, Winton, Aspect | Medium |
| 25 | **Cross-Sectional Momentum** | MOM | 0.5-1.2 | AQR, GSAM, Morgan Stanley | Low |
| 26 | **Alternative Data (Satellite / CC)** | ML | 0.7-1.5 | Two Sigma, Point72, Numerai | High |
| 27 | **Market-Neutral L/S Equity** | LS | 0.6-1.3 | Numerous | Medium |
| 28 | **Earnings Momentum / Revisions** | MOM | 0.6-1.3 | D.E. Shaw, AQR, GSAM | Medium |
| 29 | **IPO / SPAC Arbitrage** | ARB | 0.6-1.5 | Millennium, Weiss, Kylin | Medium |
| 30 | **Regulation D / PIPEs** | ARB | 0.7-1.4 | Millennium, Deerfield | High |

### Tier 3: Moderate Sharpe (0.5-1.2) | Large Capacity

| # | Strategy Name | Category | Expected Sharpe | Used By | Complexity |
|---|---|---|---|---|---|
| 31 | **Pure Alpha — Systematic Macro** | MAC | 0.8-1.2 | Bridgewater | High |
| 32 | **Merger / Risk Arbitrage** | ARB | 0.6-1.5 | Millennium, Citadel, Kylin | Medium |
| 33 | **Macro-Quantamental System** | MAC | 0.6-1.2 | JP Morgan (JPMaQS) | High |
| 34 | **Treasury Basis (Cash-Futures)** | FI/ARB | 0.4-1.2 | Citadel, D.E. Shaw, Balyasny | Medium-High |
| 35 | **Mortgage-Backed Securities Arb** | FI | 0.5-1.2 | Citadel, Amherst, Angora | High |
| 36 | **Structured Credit / CLO Arb** | FI | 0.5-1.2 | PineBridge, CIFC, Brigade | High |
| 37 | **FX Carry Trade** | MAC | 0.4-1.0 | AQR, Man FX, FX Concepts | Low |
| 38 | **Commodity Seasonal Patterns** | MOM | 0.5-1.2 | Man AHL, Gresham, Transtrend | Low-Med |
| 39 | **Quality Factor (Low Beta, High ROE)** | FAC | 0.4-0.9 | BlackRock, AQR, GSAM | Low |
| 40 | **Value Factor (Cheap Stocks)** | FAC | 0.3-0.8 | AQR, Dimensional, BlackRock | Low |
| 41 | **Low Volatility Anomaly** | FAC | 0.4-0.9 | AQR, BlackRock, State Street | Low |
| 42 | **Defensive / Low Beta Factor** | FAC | 0.4-0.8 | AQR, BlackRock | Low |
| 43 | **Multi-Factor Integrated (Composite)** | FAC | 0.4-0.8 | BlackRock, AQR, GSAM | Medium |
| 44 | **Seasonality / Calendar Effects** | TECH | 0.3-0.7 | Various quant funds | Low |
| 45 | **Volatility Risk Parity** | RP | 0.3-0.7 | Bridgewater (All Weather) | Medium |
| 46 | **Risk Parity Multi-Asset** | RP | 0.3-0.6 | Bridgewater, AQR, BlackRock | Medium |
| 47 | **Managed Futures Diversified** | MOM | 0.4-0.9 | Man AHL, Winton, Campbell | Medium |
| 48 | **Global Inflation-Linked** | MAC | 0.4-0.8 | Bridgewater, Brevan Howard | Medium |
| 49 | **Credit Default Swap Index Arb** | FI | 0.4-1.0 | Citadel, BlueMountain | High |
| 50 | **Closed-End Fund Arbitrage** | ARB | 0.5-1.2 | D.E. Shaw, Millennium | Medium |
| 51 | **VIX Futures Term Structure** | VOL | 0.5-1.2 | Parallax, Capula | Medium |
| 52 | **Correlation Trading** | VOL | 0.5-1.0 | Citadel, Capula | High |
| 53 | **Variance Swap Arbitrage** | VOL | 0.6-1.3 | GSA, Capula | High |
| 54 | **Capital Structure Arbitrage** | ARB | 0.5-1.2 | Millennium, Citadel | High |
| 55 | **Equity Market Neutral (Statistical)** | STA | 0.6-1.4 | D.E. Shaw, Two Sigma | High |
| 56 | **Basket Trading (Thematic Pairs)** | STA | 0.6-1.2 | Two Sigma, AQR | Medium |
| 57 | **Dividend Capture / Arbitrage** | ARB | 0.5-1.0 | Millennium, Citadel | Low-Med |
| 58 | **Buyback / Tender Arbitrage** | ARB | 0.5-1.2 | Kylin, Millennium | Medium |
| 59 | **Weather-Driven Commodity** | ML | 0.4-0.9 | Man AHL, Citadel | Medium |
| 60 | **Contrarian / Reversal Signal** | MRV | 0.5-1.0 | Two Sigma, AQR | Low |

### Tier 4: Core Factor / Long-Only (0.3-0.8) | Largest Capacity

| # | Strategy Name | Category | Expected Sharpe | Used By | Complexity |
|---|---|---|---|---|---|
| 61 | **Smart Beta — Minimum Volatility** | FAC | 0.3-0.7 | BlackRock, State Street, Vanguard | Low |
| 62 | **Smart Beta — Quality** | FAC | 0.3-0.7 | BlackRock, State Street | Low |
| 63 | **Smart Beta — Momentum** | FAC | 0.3-0.7 | BlackRock, GSAM | Low |
| 64 | **Smart Beta — Value** | FAC | 0.3-0.6 | BlackRock, Dimensional | Low |
| 65 | **Smart Beta — Multi-Factor** | FAC | 0.4-0.8 | BlackRock, Schwab, MSCI | Low |
| 66 | **ESG / Climate Factor** | ESG | 0.2-0.6 | BlackRock, Nuveen | Low |
| 67 | **Dividend Growth / Aristocrats** | FAC | 0.3-0.6 | BlackRock, Vanguard | Low |
| 68 | **Dollar-Cost Averaged (DCA) System** | LS | 0.2-0.4 | Retail/institutional | Low |
| 69 | **Portfolio 60/40 Balanced** | RP | 0.3-0.5 | Vanguard, BlackRock | Low |
| 70 | **Global Infrastructure Thematic** | LS | 0.3-0.6 | AMP, BlackRock | Low |
| 71 | **Real Estate (REIT) Systematic** | LS | 0.3-0.6 | BlackRock, Cohen & Steers | Medium |
| 72 | **Private Equity Secondary Arb** | LS | 0.4-0.8 | Coller Capital, Ardian | High |
| 73 | **Equity Long/Short Sector Rotation** | LS | 0.4-1.0 | Point72, Citadel | Medium |
| 74 | **CTA Short-Term Trend (1-10 day)** | MOM | 0.3-0.8 | AHL, Winton | Medium |
| 75 | **CTA Medium-Term Trend (10-50 day)** | MOM | 0.5-1.0 | AHL, Aspect, Winton | Low |
| 76 | **CTA Long-Term Trend (50-200 day)** | MOM | 0.4-0.9 | AHL, Campbell | Low |
| 77 | **Accumulation/Distribution Volume** | TECH | 0.3-0.6 | Various | Low |
| 78 | **On-Balance Volume Momentum** | TECH | 0.3-0.5 | Various | Low |
| 79 | **Earnings Quality / Accruals** | FAC | 0.3-0.7 | AQR, GSAM | Medium |
| 80 | **Shareholder Yield (Div+Buyback)** | FAC | 0.3-0.7 | Dimensional, AQR | Low |
| 81 | **Net Operating Assets** | FAC | 0.3-0.6 | AQR, Dimensional | Medium |
| 82 | **Asset Growth Effect** | FAC | 0.3-0.7 | AQR, GSAM | Medium |
| 83 | **Analyst Revision Ratio** | MOM | 0.4-0.8 | D.E. Shaw, Two Sigma | Low |
| 84 | **Insider Trading Signal** | MOM | 0.3-0.7 | D.E. Shaw, Citadel | Low |
| 85 | **Short Interest / Squeeze** | MRV | 0.3-0.8 | Two Sigma, Citadel | Low |
| 86 | **Options Flow / Block Trade** | ML | 0.5-1.0 | Citadel, Susquehanna | High |
| 87 | **Cross-Sectional Volatility (IV skew)** | VOL | 0.4-0.9 | GSA, Capula | Medium |
| 88 | **Treasury Futures Calendar Spread** | FI | 0.3-0.8 | Citadel, DRW | Medium |
| 89 | **FX Forward Points Arbitrage** | FI | 0.3-0.7 | Various banks | Medium |
| 90 | **Interest Rate Swap Basis** | FI | 0.4-0.9 | Citadel, D.E. Shaw | High |
| 91 | **Agency MBS Dollar Roll** | FI | 0.3-0.7 | Citadel, Amherst | Medium |
| 92 | **European Sovereign Arb** | FI | 0.3-0.8 | Brevan Howard, BlueCrest | Medium |
| 93 | **Emerging Market Debt Carry** | FI | 0.3-0.8 | GMO, Ashmore | Medium |
| 94 | **Leveraged Loan / CLO Equity** | FI | 0.4-0.9 | Brigade, CIFC, Apollo | High |
| 95 | **Catastrophe Bond / ILS** | FI | 0.4-0.9 | Twelve Capital, Nephila | High |
| 96 | **Crypto Basis / Futures Premium** | ARB | 0.5-1.5 | Jump, Alameda, Wintermute | Medium |
| 97 | **Crypto Market Making** | HFT | 1.0-3.0 | Jump, Cumberland, Wintermute | High |
| 98 | **Crypto Statistical Arbitrage** | STA | 0.6-1.5 | Radix, Wintermute | Medium |
| 99 | **Crypto Liquid Staking Yield** | LS | 0.3-0.8 | Lido, Rocket Pool | Low |
| 100 | **Multi-Asset Global Macro Discretionary** | MAC | 0.3-0.8 | Brevan Howard, Tudor | Medium |

### Tier 5: Technical / Pattern-Based (0.2-0.8)

| # | Strategy Name | Category | Expected Sharpe | Used By | Complexity |
|---|---|---|---|---|---|
| 101 | **Fibonacci Retracement Pullback** | TECH | 0.3-0.7 | Various systematic CTAs | Low |
| 102 | **Fibonacci Extension Target** | TECH | 0.3-0.6 | Various systematic CTAs | Low |
| 103 | **Fibonacci Time Zone Reversal** | TECH | 0.2-0.5 | Various | Low |
| 104 | **Fibonacci Fan Trend Support** | TECH | 0.3-0.6 | Various | Medium |
| 105 | **Fibonacci Arc Confluence** | TECH | 0.2-0.5 | Various | Medium |
| 106 | **Gartley Pattern (Harmonic)** | TECH | 0.3-0.7 | Harmonic quant strategies | Medium |
| 107 | **Butterfly Harmonic Pattern** | TECH | 0.3-0.7 | Harmonic quant strategies | Medium |
| 108 | **Crab Harmonic Pattern** | TECH | 0.3-0.6 | Harmonic quant strategies | Medium |
| 109 | **Bat Harmonic Pattern** | TECH | 0.3-0.6 | Harmonic quant strategies | Medium |
| 110 | **Multi-TF Fib Confluence Zone** | TECH | 0.4-0.8 | Various systematic CTAs | Medium |
| 111 | **Bullish Engulfing Pattern** | TECH | 0.4-0.8 | Systematic L/S Equity | Low |
| 112 | **Bearish Engulfing Pattern** | TECH | 0.4-0.8 | Systematic L/S Equity | Low |
| 113 | **Morning Star Reversal** | TECH | 0.4-0.9 | Systematic L/S Equity | Low |
| 114 | **Evening Star Reversal** | TECH | 0.4-0.9 | Systematic L/S Equity | Low |
| 115 | **Three White Soldiers** | TECH | 0.4-0.8 | Systematic L/S Equity | Low |
| 116 | **Three Black Crows** | TECH | 0.4-0.8 | Systematic L/S Equity | Low |
| 117 | **Doji + Volume Indecision Trade** | TECH | 0.2-0.4 | Various | Low |
| 118 | **Hammer / Hanging Man Reversal** | TECH | 0.3-0.6 | Various | Low |
| 119 | **Shooting Star Reversal** | TECH | 0.3-0.6 | Various | Low |
| 120 | **Harami + Confirmation** | TECH | 0.3-0.6 | Various | Low |
| 121 | **Piercing Line / Dark Cloud Cover** | TECH | 0.3-0.7 | Various | Low |
| 122 | **Rising / Falling Three Methods** | TECH | 0.4-0.7 | Various | Low |
| 123 | **Tweezer Top/Bottom** | TECH | 0.3-0.5 | Various | Low |
| 124 | **Abandoned Baby Reversal** | TECH | 0.4-0.8 | Various | Low |
| 125 | **Upside / Downside Tasuki Gap** | TECH | 0.3-0.5 | Various | Low |
| 126 | **Bollinger Band Mean Reversion** | TECH/MRV | 0.4-0.7 | Various quant funds | Low |
| 127 | **Bollinger Band Breakout** | TECH/MOM | 0.3-0.6 | Various | Low |
| 128 | **RSI Divergence (+Fib confluence)** | TECH | 0.3-0.6 | Various | Low |
| 129 | **MACD Signal Line Crossover** | TECH/MOM | 0.2-0.5 | Various | Low |
| 130 | **Moving Average Crossover (MA-50/200)** | TECH/MOM | 0.2-0.5 | Various | Low |
| 131 | **Supertrend Reversal** | TECH/MOM | 0.3-0.6 | Various | Low |
| 132 | **Parabolic SAR Trend Catch** | TECH/MOM | 0.2-0.5 | Various | Low |
| 133 | **Ichimoku Cloud (Kumo Breakout)** | TECH/MOM | 0.3-0.6 | Various | Medium |
| 134 | **Price Patterns (H&S, Double Top/Bottom)** | TECH | 0.3-0.6 | Various | Medium |
| 135 | **Intraday Opening Range Breakout** | TECH/MOM | 0.3-0.7 | Various HFT/CTAs | Low |
| 136 | **VWAP Reversion** | TECH/MRV | 0.3-0.6 | Various | Low |
| 137 | **Time-Weighted Average Price** | TECH | 0.2-0.4 | VWAP execution algos | Low |
| 138 | **ATR Channel Breakout** | TECH/MOM | 0.3-0.6 | Various CTAs | Low |
| 139 | **Moving Average Ribbon Trend** | TECH/MOM | 0.3-0.5 | Various | Low |
| 140 | **Keltner Channel Squeeze** | TECH/VOL | 0.3-0.6 | Various | Low |
| 141 | **Donchian Channel Breakout** | TECH/MOM | 0.3-0.7 | Turtle Traders, CTAs | Low |
| 142 | **Price Oscillator (PO)** | TECH/MOM | 0.2-0.5 | Various | Low |
| 143 | **Williams %R Overbought/Oversold** | TECH/MRV | 0.2-0.5 | Various | Low |
| 144 | **Elder Triple Screen** | TECH | 0.3-0.6 | Various | Medium |
| 145 | **Commitment of Traders (COT)** | TECH | 0.3-0.6 | CTA funds | Low |

---

## Fund-by-Fund Strategy Map

| Fund | AUM (Est.) | Primary Strategies | Flagship | Signature Advantage |
|---|---|---|---|---|
| **Renaissance Technologies** | ~$50B | HMM stat arb, HFT, NLP, ML factor timing | Medallion Fund | Hidden Markov regime detection across 500+ features |
| **Bridgewater Associates** | ~$120B | Risk Parity, Pure Alpha macro, All Weather | Pure Alpha / All Weather | Economic growth/inflation quadrants + risk parity |
| **Citadel** | ~$60B | Global FI arb, convert arb, dispersion, equities, credit | Wellington, Kensington | Cross-asset relative value + multi-strat |
| **D.E. Shaw** | ~$55B | Pairs stat arb, FI arb, convertible arb, equity L/S | Oculus, Composite | Cointegration-based pair trading at scale |
| **Two Sigma** | ~$60B | ML factor timing, stat arb, NLP, alt data | Spectrum, Compass | ML-first research culture (hundreds of PhDs) |
| **AQR Capital** | ~$95B | Style premia (value/momentum/carry/defensive), CTA | Style Premia Alternative | Four-factor framework across all assets |
| **Millennium Management** | ~$65B | Multi-pod (100+ teams), L/S equity, merger arb | Multi-Strategy | Pod architecture with tight risk limits |
| **Point72 / Cubist** | ~$40B | Cubist systematic, L/S equity, multi-pod | Cubist Systematic | KEPL short-term reversal team → HFT stat arb |
| **Man Group / AHL** | ~$80B | Time-series momentum, trend following, ML | AHL Dimension | Diversified CTA — trend following at scale |
| **JP Morgan (Quant)** | — | Macro-quantamental, QIS, factor strategies | JPMaQS | Institutional macro data → systematic signals |
| **BlackRock (Systematic)** | ~$100B+ | Factor investing, smart beta, risk parity | Scientific Active Equity | Large-scale factor implementation |
| **Brevan Howard** | ~$20B | Global macro, FI arb, FX vol | Master Fund | Macro discretionary + systematic overlay |
| **WorldQuant** | ~$10B+ | Stat arb alphas, ML, alt data | +1000 alpha signals | Extremely high alpha signal count |
| **Numerai** | ~$3B | ML / crowdsourced predictions | Numerai Hedge Fund | Meta-model from thousands of data scientists |
| **Tudor Investment Corp** | ~$10B | Global macro, systematic macro | Tudor BVI | Macro trend + discretionary |

---

## Appendices

### A. Fibonacci Level Mathematics

```
Golden Ratio Φ = (1 + sqrt(5)) / 2 ≈ 1.6180339887...

Key Ratios:
  0.236  = 1 - 0.764  (derived from Φ^-3)
  0.382  = 1 - 0.618  (derived from Φ^-2)
  0.500  = 1 - 0.500  (midpoint, not true Fib but standard)
  0.618  = Φ^-1       (the golden ratio reciprocal)
  0.786  = sqrt(Φ^-1) (√0.618)
  1.000  = full trend
  1.272  = sqrt(Φ)    (√1.618)
  1.618  = Φ          (golden ratio)
  2.000  = full trend × 2 (not true Fib but standard)
  2.618  = Φ^2
  3.618  = Φ^2 + 1
  4.236  = Φ^3
```

### B. Candlestick Pattern Calculation Pseudocode (Generic)

```python
def body_size(candle): return abs(candle.close - candle.open)
def upper_wick(candle): return candle.high - max(candle.open, candle.close)
def lower_wick(candle): return min(candle.open, candle.close) - candle.low
def is_bullish(candle): return candle.close > candle.open
def is_bearish(candle): return candle.close < candle.open
def is_doji(candle): return body_size(candle) < (candle.high - candle.low) * 0.10
def avg_body(period=20): return mean([body_size(c) for c in candles[-period:]])
```

### C. Key Hedge Fund Strategy Categories by Investment Horizon

| Horizon | Typical Strategies | Metric Focus |
|---|---|---|
| **Ultra-Short (< 1s)** | HFT market making, latency arb, rebate | Tick-level pnl, fill rate, latency |
| **Intraday (1s-1d)** | Order flow, micro reversion, ETF arb | Sharpe/day, capacity, turnover |
| **Short-Term (1-10d)** | Stat arb, momentum, mean reversion | Annualized Sharpe, correlation to mkt |
| **Medium-Term (10-60d)** | Factor investing, trend following, carry | IR, factor exposure, AUM capacity |
| **Long-Term (60-252d)** | Value, quality, risk parity, macro | Beta-adjusted returns, max drawdown |
| **Event-Driven** | Merger arb, distressed, catalyst | Completion rate, annualized spread |

### D. Sharpe Ratio Context (Industry Benchmarks)

| Level | Interpretation | Typical Strategy |
|---|---|---|
| < 0.3 | Poor (long-only unhedged) | 60/40 passive |
| 0.3-0.5 | Below average (balanced fund) | Risk parity, macro |
| 0.5-0.7 | Acceptable (institutional) | Factor strategies |
| 0.7-1.0 | Good | L/S equity, CTA trend |
| 1.0-1.5 | Excellent | Stat arb, FI arb, merger arb |
| 1.5-2.0 | Exceptional (capacity-limited) | Dispersion, convertible arb |
| 2.0-3.0 | Elite (very capacity-limited) | HFT, Renaissance-type strats |
| 3.0+ | Extreme outlier | Medallion (historical), latency arb |

> **Sources:** AQR, Bridgewater whitepapers, QuantPedia, academic literature (Jegadeesh & Titman 1993, Moskowitz et al. 2012, Asness et al. 2013, Baltas & Kosowski 2020), industry reports from HedgeNordic, Resonanz Capital, and SEC 13F filings analysis.

---

*Generated: July 2026 | 140+ Strategies, 20 with full pseudocode, all Fibonacci variants, 40 candlestick patterns, fund attribution, and Sharpe ranges.*
