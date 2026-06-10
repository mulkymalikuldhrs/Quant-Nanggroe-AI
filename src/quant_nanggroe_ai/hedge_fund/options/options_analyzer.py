"""
Options Analysis Module
Options pricing, Greeks calculation, and strategy analysis.
Based on Black-Scholes and binomial models.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from math import log, sqrt, exp
from scipy.stats import norm
from scipy.optimize import brentq, newton

logger = logging.getLogger(__name__)


class OptionType(Enum):
    """Option types"""
    CALL = "CALL"
    PUT = "PUT"


class ExerciseStyle(Enum):
    """Exercise styles"""
    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"


@dataclass
class OptionGreeks:
    """Option Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    vanna: float = 0
    charm: float = 0


@dataclass
class ImpliedVolatility:
    """Implied volatility result"""
    iv: float
    success: bool
    error: Optional[str] = None


class BlackScholes:
    """
    Black-Scholes option pricing model.
    
    Supports:
    - European options on non-dividend paying stocks
    - Greeks calculation
    - Implied volatility calculation
    """
    
    def __init__(self, S: float, K: float, T: float, r: float, sigma: float):
        """
        Initialize Black-Scholes model.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to maturity (in years)
            r: Risk-free rate
            sigma: Volatility (annual)
        """
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        
        # Calculate d1 and d2
        if T > 0 and sigma > 0:
            self.d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
            self.d2 = self.d1 - sigma * sqrt(T)
        else:
            self.d1 = 0
            self.d2 = 0
    
    def price(self, option_type: OptionType) -> float:
        """
        Calculate option price.
        
        Args:
            option_type: CALL or PUT
            
        Returns:
            Option price
        """
        if self.T <= 0:
            # At expiration
            if option_type == OptionType.CALL:
                return max(0, self.S - self.K)
            else:
                return max(0, self.K - self.S)
        
        if option_type == OptionType.CALL:
            return (self.S * norm.cdf(self.d1) - 
                    self.K * exp(-self.r * self.T) * norm.cdf(self.d2))
        else:
            return (self.K * exp(-self.r * self.T) * norm.cdf(-self.d2) - 
                    self.S * norm.cdf(-self.d1))
    
    def greeks(self, option_type: OptionType) -> OptionGreeks:
        """
        Calculate option Greeks.
        
        Args:
            option_type: CALL or PUT
            
        Returns:
            OptionGreeks dataclass
        """
        sqrt_T = sqrt(self.T) if self.T > 0 else 0
        
        # Delta
        if option_type == OptionType.CALL:
            delta = norm.cdf(self.d1)
        else:
            delta = norm.cdf(self.d1) - 1
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(self.d1) / (self.S * self.sigma * sqrt_T) if self.T > 0 else 0
        
        # Vega (same for calls and puts)
        vega = self.S * norm.pdf(self.d1) * sqrt_T / 100  # Per 1% vol change
        
        # Theta
        if self.T > 0:
            if option_type == OptionType.CALL:
                theta = (-(self.S * norm.pdf(self.d1) * self.sigma / (2 * sqrt_T)) 
                        - self.r * self.K * exp(-self.r * self.T) * norm.cdf(self.d2)) / 365
            else:
                theta = (-(self.S * norm.pdf(self.d1) * self.sigma / (2 * sqrt_T)) 
                        + self.r * self.K * exp(-self.r * self.T) * norm.cdf(-self.d2)) / 365
        else:
            theta = 0
        
        # Rho
        if option_type == OptionType.CALL:
            rho = self.K * self.T * exp(-self.r * self.T) * norm.cdf(self.d2) / 100  # Per 1% rate
        else:
            rho = -self.K * self.T * exp(-self.r * self.T) * norm.cdf(-self.d2) / 100
        
        return OptionGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho
        )
    
    def implied_volatility(
        self,
        market_price: float,
        option_type: OptionType,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> ImpliedVolatility:
        """
        Calculate implied volatility.
        
        Args:
            market_price: Market price of the option
            option_type: CALL or PUT
            max_iterations: Maximum Newton-Raphson iterations
            tolerance: Convergence tolerance
            
        Returns:
            ImpliedVolatility result
        """
        if market_price <= 0:
            return ImpliedVolatility(0, False, "Invalid market price")
        
        # Check for arbitrage bounds
        if option_type == OptionType.CALL:
            if market_price < max(0, self.S - self.K * exp(-self.r * self.T)):
                return ImpliedVolatility(0, False, "Price below intrinsic value")
        else:
            if market_price < max(0, self.K * exp(-self.r * self.T) - self.S):
                return ImpliedVolatility(0, False, "Price below intrinsic value")
        
        # Use Newton-Raphson method
        sigma = 0.5  # Initial guess
        
        for _ in range(max_iterations):
            bs = BlackScholes(self.S, self.K, self.T, self.r, sigma)
            price = bs.price(option_type)
            greeks = bs.greeks(option_type)
            
            diff = market_price - price
            
            if abs(diff) < tolerance:
                return ImpliedVolatility(sigma * 100, True)
            
            # Newton-Raphson update
            if greeks.vega != 0:
                sigma = sigma + diff / (greeks.vega * 100)  # Adjust for vega scaling
            
            # Bound sigma
            sigma = max(0.01, min(sigma, 5.0))
        
        return ImpliedVolatility(sigma * 100, False, "Did not converge")


class OptionsAnalyzer:
    """
    Comprehensive Options Analyzer.
    
    Features:
    - Black-Scholes pricing
    - Greeks calculation
    - Implied volatility surface
    - Strategy analysis
    - Volatility analysis
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize options analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate
        """
        self.risk_free_rate = risk_free_rate
    
    def price_option(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        option_type: OptionType
    ) -> Tuple[float, OptionGreeks]:
        """
        Price an option and calculate Greeks.
        
        Args:
            S: Stock price
            K: Strike price
            T: Time to maturity (years)
            sigma: Volatility (annual)
            option_type: CALL or PUT
            
        Returns:
            Tuple of (price, greeks)
        """
        bs = BlackScholes(S, K, T, self.risk_free_rate, sigma)
        price = bs.price(option_type)
        greeks = bs.greeks(option_type)
        
        return price, greeks
    
    def calculate_implied_volatility(
        self,
        S: float,
        K: float,
        T: float,
        market_price: float,
        option_type: OptionType
    ) -> ImpliedVolatility:
        """
        Calculate implied volatility from market price.
        
        Args:
            S: Stock price
            K: Strike price
            T: Time to maturity
            market_price: Observed option price
            option_type: CALL or PUT
            
        Returns:
            Implied volatility result
        """
        bs = BlackScholes(S, K, T, self.risk_free_rate, 0.5)
        return bs.implied_volatility(market_price, option_type)
    
    def calculate_option_chain_greeks(
        self,
        S: float,
        T: float,
        strikes: List[float],
        sigma: float,
        option_type: OptionType
    ) -> List[Dict]:
        """
        Calculate Greeks for a chain of strikes.
        
        Args:
            S: Current stock price
            T: Time to expiration
            strikes: List of strike prices
            sigma: Volatility
            option_type: CALL or PUT
            
        Returns:
            List of dictionaries with prices and Greeks
        """
        results = []
        
        for K in strikes:
            price, greeks = self.price_option(S, K, T, sigma, option_type)
            
            results.append({
                'strike': K,
                'price': price,
                'delta': greeks.delta,
                'gamma': greeks.gamma,
                'theta': greeks.theta,
                'vega': greeks.vega,
                'rho': greeks.rho,
                'moneyness': 'ITM' if (option_type == OptionType.CALL and S > K) or 
                                         (option_type == OptionType.PUT and S < K) else 'OTM'
            })
        
        return results
    
    def analyze_covered_call(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        dividend_yield: float = 0
    ) -> Dict:
        """
        Analyze covered call strategy.
        
        Returns:
            Strategy analysis
        """
        bs_call = BlackScholes(S, K, T, self.risk_free_rate - dividend_yield, sigma)
        call_price = bs_call.price(OptionType.CALL)
        
        # Breakeven = Stock Price - Call Premium
        breakeven = S - call_price
        
        # Max profit = (K - S) + Premium (if exercised)
        max_profit = (K - S + call_price) if K > S else call_price
        max_profit_pct = (max_profit / S) * 100
        
        # Downside protection from premium
        downside_protection = (call_price / S) * 100
        
        return {
            'strategy': 'Covered Call',
            'premium': call_price,
            'breakeven': breakeven,
            'max_profit': max_profit,
            'max_profit_pct': max_profit_pct,
            'downside_protection_pct': downside_protection,
            'upside_cap': max_profit_pct,
            'delta': bs_call.greeks(OptionType.CALL).delta
        }
    
    def analyze_protective_put(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float
    ) -> Dict:
        """
        Analyze protective put strategy.
        
        Returns:
            Strategy analysis
        """
        bs_put = BlackScholes(S, K, T, self.risk_free_rate, sigma)
        put_price = bs_put.price(OptionType.PUT)
        
        # Breakeven = Stock Price + Put Premium
        breakeven = S + put_price
        
        # Max loss = Put Premium (plus stock decline to K)
        max_loss = put_price + (S - K) if S > K else put_price
        max_loss_pct = (max_loss / S) * 100
        
        # Upside potential = Unlimited
        downside_protection = (put_price / S) * 100
        
        return {
            'strategy': 'Protective Put',
            'premium': put_price,
            'breakeven': breakeven,
            'max_loss': max_loss,
            'max_loss_pct': max_loss_pct,
            'downside_protection_pct': downside_protection,
            'upside_potential': 'Unlimited',
            'delta': bs_put.greeks(OptionType.PUT).delta
        }
    
    def analyze_straddle(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float
    ) -> Dict:
        """
        Analyze long straddle strategy.
        
        Returns:
            Strategy analysis
        """
        bs_call = BlackScholes(S, K, T, self.risk_free_rate, sigma)
        bs_put = BlackScholes(S, K, T, self.risk_free_rate, sigma)
        
        call_price = bs_call.price(OptionType.CALL)
        put_price = bs_put.price(OptionType.PUT)
        total_premium = call_price + put_price
        
        # Breakeven points
        upper_breakeven = K + total_premium
        lower_breakeven = K - total_premium
        
        # Implied move
        implied_move_pct = (total_premium / S) * 100
        
        return {
            'strategy': 'Long Straddle',
            'call_premium': call_price,
            'put_premium': put_price,
            'total_premium': total_premium,
            'upper_breakeven': upper_breakeven,
            'lower_breakeven': lower_breakeven,
            'implied_move_pct': implied_move_pct,
            'delta_neutral': bs_call.greeks(OptionType.CALL).delta + bs_put.greeks(OptionType.PUT).delta
        }
    
    def calculate_volatility_smile(
        self,
        S: float,
        T: float,
        strikes: List[float],
        market_prices: Dict[float, Tuple[float, OptionType]],
        risk_free_rate: float = None
    ) -> Dict[float, float]:
        """
        Calculate implied volatility smile/smirk.
        
        Args:
            S: Stock price
            T: Time to expiration
            strikes: Strike prices
            market_prices: Dict of {strike: (price, option_type)}
            
        Returns:
            Dict of {strike: implied_volatility}
        """
        rate = risk_free_rate or self.risk_free_rate
        ivs = {}
        
        for K, (price, opt_type) in market_prices.items():
            iv_result = self.calculate_implied_volatility(S, K, T, price, opt_type)
            if iv_result.success:
                ivs[K] = iv_result.iv
        
        return ivs
    
    def options_risk_profile(
        self,
        positions: List[Dict],
        S: float,
        T: float,
        sigma: float,
        price_range: List[float] = None
    ) -> Dict:
        """
        Calculate P&L profile for option positions.
        
        Args:
            positions: List of option positions
            S: Current stock price
            T: Time to expiration
            sigma: Volatility
            
        Returns:
            Risk profile analysis
        """
        if price_range is None:
            price_range = [S * (1 - 0.3 + i * 0.02) for i in range(31)]
        
        pnl_at_expiry = []
        pnl_now = []
        
        for price in price_range:
            expiry_pnl = 0
            current_pnl = 0
            
            for pos in positions:
                K = pos['strike']
                opt_type = pos['type']
                quantity = pos['quantity']
                entry_price = pos['entry_price']
                
                # P&L at expiry
                if opt_type == OptionType.CALL:
                    payoff = max(0, price - K)
                else:
                    payoff = max(0, K - price)
                expiry_pnl += (payoff - entry_price) * quantity
                
                # P&L now (with time value)
                current_val, _ = self.price_option(price, K, T, sigma, opt_type)
                current_pnl += (current_val - entry_price) * quantity
            
            pnl_at_expiry.append(expiry_pnl)
            pnl_now.append(current_pnl)
        
        return {
            'prices': price_range,
            'pnl_at_expiry': pnl_at_expiry,
            'pnl_now': pnl_now,
            'max_loss': min(min(pnl_at_expiry), min(pnl_now)),
            'max_gain': max(max(pnl_at_expiry), max(pnl_now)),
            'breakeven_points': self._find_breakevens(price_range, pnl_at_expiry)
        }
    
    def _find_breakevens(self, prices: List[float], pnls: List[float]) -> List[float]:
        """Find breakeven points from P&L array"""
        breakevens = []
        
        for i in range(1, len(pnls)):
            if pnls[i-1] < 0 <= pnls[i] or pnls[i-1] > 0 >= pnls[i]:
                # Linear interpolation
                x1, x2 = prices[i-1], prices[i]
                y1, y2 = pnls[i-1], pnls[i]
                breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                breakevens.append(breakeven)
        
        return breakevens


# Example usage
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = OptionsAnalyzer(risk_free_rate=0.02)
    
    # Sample parameters
    S = 100  # Stock price
    K = 100  # Strike price
    T = 0.25  # 3 months
    sigma = 0.3  # 30% volatility
    
    # Price a call option
    call_price, greeks = analyzer.price_option(S, K, T, sigma, OptionType.CALL)
    print(f"Call Option Price: ${call_price:.2f}")
    print(f"Greeks: Delta={greeks.delta:.3f}, Gamma={greeks.gamma:.4f}, Theta={greeks.theta:.4f}, Vega={greeks.vega:.4f}")
    
    # Calculate implied volatility
    market_price = 10.50
    iv_result = analyzer.calculate_implied_volatility(S, K, T, market_price, OptionType.CALL)
    print(f"\nImplied Volatility: {iv_result.iv:.2f}% (Success: {iv_result.success})")
    
    # Analyze covered call
    cc_analysis = analyzer.analyze_covered_call(S, K, T, sigma)
    print(f"\nCovered Call Analysis:")
    for k, v in cc_analysis.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    
    # Analyze straddle
    straddle = analyzer.analyze_straddle(S, K, T, sigma)
    print(f"\nStraddle Analysis:")
    for k, v in straddle.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
