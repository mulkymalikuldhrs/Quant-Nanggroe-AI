"""Bisect which import hangs."""
from quant_nanggroe.config import get_settings
print("1. config OK")

from quant_nanggroe.api.middleware import AuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
print("2. middleware OK")

from quant_nanggroe.security.auth import APIKeyAuth, JWTAuth, UserRole
print("3. auth OK")

# Now try the routes
try:
    from quant_nanggroe.api.routes import market
    print("4. market OK")
except Exception as e:
    print(f"4. market FAIL: {e}")

try:
    from quant_nanggroe.api.routes import trading
    print("5. trading OK")
except Exception as e:
    print(f"5. trading FAIL: {e}")

try:
    from quant_nanggroe.api.routes import agents
    print("6. agents OK")
except Exception as e:
    print(f"6. agents FAIL: {e}")

try:
    from quant_nanggroe.api.routes import backtest
    print("7. backtest OK")
except Exception as e:
    print(f"7. backtest FAIL: {e}")

try:
    from quant_nanggroe.api.routes import portfolio
    print("8. portfolio OK")
except Exception as e:
    print(f"8. portfolio FAIL: {e}")

try:
    from quant_nanggroe.api.routes import ws
    print("9. ws OK")
except Exception as e:
    print(f"9. ws FAIL: {e}")

try:
    from quant_nanggroe.api.routes import memory
    print("10. memory OK")
except Exception as e:
    print(f"10. memory FAIL: {e}")

try:
    from quant_nanggroe.api.routes import ecosystem
    print("11. ecosystem OK")
except Exception as e:
    print(f"11. ecosystem FAIL: {e}")

try:
    from quant_nanggroe.api.routes import colony
    print("12. colony OK")
except Exception as e:
    print(f"12. colony FAIL: {e}")

try:
    from quant_nanggroe.api.routes import channels
    print("13. channels OK")
except Exception as e:
    print(f"13. channels FAIL: {e}")

try:
    from quant_nanggroe.api.routes import council
    print("14. council OK")
except Exception as e:
    print(f"14. council FAIL: {e}")

try:
    from quant_nanggroe.api.routes import debate
    print("15. debate OK")
except Exception as e:
    print(f"15. debate FAIL: {e}")

try:
    from quant_nanggroe.api.routes import fred
    print("16. fred OK")
except Exception as e:
    print(f"16. fred FAIL: {e}")

try:
    from quant_nanggroe.api.routes import geopolitics
    print("17. geopolitics OK")
except Exception as e:
    print(f"17. geopolitics FAIL: {e}")

try:
    from quant_nanggroe.api.routes import personas
    print("18. personas OK")
except Exception as e:
    print(f"18. personas FAIL: {e}")

try:
    from quant_nanggroe.api.routes import sec_edgar
    print("19. sec_edgar OK")
except Exception as e:
    print(f"19. sec_edgar FAIL: {e}")

try:
    from quant_nanggroe.api.routes import signal_generator
    print("20. signal_generator OK")
except Exception as e:
    print(f"20. signal_generator FAIL: {e}")

try:
    from quant_nanggroe.api.routes import strategy
    print("21. strategy OK")
except Exception as e:
    print(f"21. strategy FAIL: {e}")

try:
    from quant_nanggroe.api.routes import monitor
    print("22. monitor OK")
except Exception as e:
    print(f"22. monitor FAIL: {e}")

try:
    from quant_nanggroe.api.routes import options
    print("23. options OK")
except Exception as e:
    print(f"23. options FAIL: {e}")

try:
    from quant_nanggroe.api.routes import rl
    print("24. rl OK")
except Exception as e:
    print(f"24. rl FAIL: {e}")

try:
    from quant_nanggroe.api.routes import analytics
    print("25. analytics OK")
except Exception as e:
    print(f"25. analytics FAIL: {e}")

try:
    from quant_nanggroe.api.routes import agentic
    print("26. agentic OK")
except Exception as e:
    print(f"26. agentic FAIL: {e}")

print("ALL DONE")
