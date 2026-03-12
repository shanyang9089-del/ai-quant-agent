# Generated Strategy 01 Summary

## 1. 策略名称
`TrendPullbackStrategyV1`

## 2. 策略类型
趋势回踩（Trend Pullback）做多策略

## 3. 核心逻辑摘要
该策略在 `15m` 周期中，先用长期 EMA 判断是否处于上行大趋势，再用快慢 EMA 判断短中期结构是否保持多头。只有在价格回踩至快线附近（避免盲目追高）且 RSI 与成交量同时确认时才触发做多。出场使用两层机制：
- 信号出场：趋势结构转弱（快线下穿慢线）或 RSI 转弱；
- 风险收益出场：固定止损与固定止盈（均为可优化参数）。

## 4. 入场条件
以下条件同时满足时触发 `enter_long = 1`：
1. `close > ema_trend`（位于长期趋势线上方）；
2. `ema_fast > ema_slow`（快线高于慢线，结构偏多）；
3. `close / ema_fast` 在 `0.985 ~ 1.01` 之间（回踩后不过度偏离快线）；
4. `rsi >= rsi_entry_threshold`（默认 52）；
5. `volume > vol_ma` 且 `volume > 0`（成交量强于均量，过滤低质量信号）。

## 5. 出场条件
满足以下任一条件时触发 `exit_long = 1`：
1. `ema_fast < ema_slow`（趋势结构破坏）；
2. `rsi < rsi_exit_threshold`（默认 46，动量转弱）。

此外，策略同时启用：
- 固定止损：`stoploss_param`，范围 `-0.03 ~ -0.02`，默认 `-0.025`；
- 固定止盈：`minimal_roi_param`，范围 `0.04 ~ 0.06`，默认 `0.05`。

## 6. 风险点
1. 在宽幅震荡行情中，EMA 多头结构可能反复失效，造成连续小亏；
2. 极端消息驱动行情下，回踩区间约束可能导致错过快速单边拉升；
3. 固定止盈在强趋势中可能过早离场，利润延展能力有限。

## 7. 最适合后续优化的 3 个参数
1. `trend_ema_period`：决定大趋势过滤的灵敏度；
2. `rsi_entry_threshold`：决定入场时的动量强度要求；
3. `minimal_roi_param`：决定止盈位置（平衡胜率与盈亏比）。
