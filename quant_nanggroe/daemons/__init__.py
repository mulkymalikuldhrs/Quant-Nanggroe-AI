# Daemons directory — all TradeBobby port daemons removed.
# COT, crypto pulse, macro pulse, news scanner were deleted:
#   - Zero Python consumers for their JSON output
#   - Dashboard API routes return graceful 503 fallback
# If these data feeds are needed, wire them into the DataProviderManager
# at quant_nanggroe.data.manager.DataProviderManager instead.
