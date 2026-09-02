# VECTOR ARBITRAGE — QNA v8.0.20 Real Trade Ready

**SSOT:** CANONICAL.md v8.0.20 — BAL 1445, weekly 0 WIB, probe 0/32, CPCV 207

## 1. Currency Graph `engine/currency_graph.py:1` V 7→28
Node EUR USD GBP JPY AUD CAD CHF, Edge R_A/B, check `R_A/B*R_B/C*R_C/A=1`, `find_triangular_cycles` C(28,3)=3276 threshold 0.0002.

## 2. Cross Matrix `engine/cross_matrix.py:1` N×N
`M[i][j]=R_ij` `diag 1` `reciprocity 1/R` `implied CAD/JPY=USDJPY/USDCAD` 1.4065 137.01.

## 3. Tri Arb `engine/tri_arb_detector.py:Δ`
`Δ=quoted - R_A/C*R_C/B` `buy Ac+Cb sell Ab` if Δ>0, HFT 3-leg IOC `TRADE_ACTION_DEAL` KillSwitch.

## 4. Vector `engine/vector_manifold.py:Point*`
`origin 0,0,0` `P=xî+yĵ+zk` `PointYEN/CHF/CAD` `plane purple/green` `origin USD-base`.

## 5. Euclid `engine/euclidean_mispricing.py:d`
`d=||P-P0||` `√2 45°` `CADJPY/√2=95.98` `box sigma 0.05*√2` `d>threshold trigger`.

## 6. Grid `engine/grid_executor.py:0.05`
`grid 0.05σ` `eigenvector` `limit mesh x,y,z` `hedged` `TRADE_ACTION_PENDING` lot 0.01 risk 0.5%.

**Verify:** `py_compile 6` `tsc clean` `grep Math.random 0` `probe 0/32` `weekly 0 WIB`.
