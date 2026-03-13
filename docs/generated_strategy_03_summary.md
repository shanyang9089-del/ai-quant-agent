# RSIMultiMAVolBetV1 策略说明（严格覆盖更新版）

## 1. 策略名称
RSIMultiMAVolBetV1

## 2. 策略定位
15m / futures / 仅做多的小仓位高杠杆实验策略：
- 固定 20x 杠杆（受 `max_leverage` 限制）
- 固定每次开仓 20 USDT
- 只做“刚转强第一脚”

## 3. 指标限制
仅使用以下指标：
1. RSI
2. EMA（8/21/55）
3. 成交量均线（20）

未新增其他指标。

## 4. 入场逻辑（严格条件）
`enter_long` 必须同时满足：
1. `ema_fast > ema_mid > ema_slow`
2. `ema_fast > ema_fast.shift(1)`
3. `ema_mid > ema_mid.shift(1)`
4. `close > ema_fast`
5. `close.shift(1) <= ema_fast.shift(1)`
6. `rsi > 50`
7. `rsi.shift(1) <= 50`
8. `volume > volume_ma * 1.2`
9. `close <= ema_fast * 1.01`

## 5. 退出与风控
- `minimal_roi = {"0": 1.0}`
- `stoploss = -0.99`
- `populate_exit_trend()` 保持极简，不增加复杂技术离场

## 6. 仓位与杠杆
- `custom_stake_amount()` 固定返回 `20.0`
- `leverage()` 固定返回 `min(20.0, max_leverage)`
