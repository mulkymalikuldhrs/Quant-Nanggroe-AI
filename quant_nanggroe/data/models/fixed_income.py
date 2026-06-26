class FixedIncomeCalculator:
    def __init__(self):
        self._ql = None
        try:
            import PyQL as ql

            self._ql = ql
        except ImportError:
            pass

    def bond_price(
        self, face_value: float, coupon_rate: float, maturity_years: float, yield_rate: float
    ) -> float | None:
        if not self._ql:
            return None
        return (
            face_value * coupon_rate
            * (1 - (1 + yield_rate) ** -maturity_years)
            / yield_rate
            + face_value / (1 + yield_rate) ** maturity_years
        )
