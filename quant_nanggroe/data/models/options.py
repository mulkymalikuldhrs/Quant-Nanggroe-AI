from dataclasses import dataclass
from typing import Optional


@dataclass
class OptionPrice:
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class OptionsPricer:
    def __init__(self):
        self._vollib = None
        self._gs = None
        self._init_engines()

    def _init_engines(self):
        try:
            import vollib

            self._vollib = vollib
        except ImportError:
            pass
        try:
            import gs_quant

            self._gs = gs_quant
        except ImportError:
            pass

    def black_scholes(
        self, flag: str, S: float, K: float, t: float, r: float, sigma: float
    ) -> Optional[OptionPrice]:
        if self._vollib:
            from vollib.black_scholes import black_scholes as bs

            price = bs(flag, S, K, t, r, sigma, return_value="price")
            return OptionPrice(
                price=price, delta=0, gamma=0, vega=0, theta=0, rho=0
            )
        return None
