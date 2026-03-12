from functools import reduce
from typing import Any

import talib.abstract as ta
from freqtrade.strategy import DecimalParameter, IStrategy, IntParameter
from pandas import DataFrame


class TrendPullbackStrategyV1(IStrategy):
    """
    TrendPullbackStrategyV1
    - 15m 周期下的趋势回踩做多策略
    - 适配 Binance USDT Futures，当前仅做多
    """

    INTERFACE_VERSION = 3

    # 仅做多
    can_short = False

    timeframe = "15m"
    startup_candle_count = 240

    # 将止盈/止损设计为可优化参数
    stoploss_param = DecimalParameter(-0.03, -0.02, default=-0.025, decimals=3, space="sell", optimize=True)
    minimal_roi_param = DecimalParameter(0.04, 0.06, default=0.05, decimals=3, space="sell", optimize=True)

    # 趋势和过滤参数（可做后续 hyperopt）
    fast_ema_period = IntParameter(8, 30, default=12, space="buy", optimize=True)
    slow_ema_period = IntParameter(20, 80, default=26, space="buy", optimize=True)
    trend_ema_period = IntParameter(100, 240, default=200, space="buy", optimize=True)
    rsi_entry_threshold = IntParameter(50, 60, default=52, space="buy", optimize=True)
    volume_window = IntParameter(10, 40, default=20, space="buy", optimize=True)

    # 出场侧动量参数
    rsi_exit_threshold = IntParameter(40, 52, default=46, space="sell", optimize=True)

    @property
    def minimal_roi(self) -> dict[str, float]:
        """固定止盈，后续可通过 hyperopt 优化。"""
        return {"0": float(self.minimal_roi_param.value)}

    @property
    def stoploss(self) -> float:
        """固定止损，后续可通过 hyperopt 优化。"""
        return float(self.stoploss_param.value)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """计算策略所需指标。"""
        fast_period = int(self.fast_ema_period.value)
        slow_period = int(self.slow_ema_period.value)
        trend_period = int(self.trend_ema_period.value)
        vol_period = int(self.volume_window.value)

        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=fast_period)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=slow_period)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=trend_period)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["vol_ma"] = dataframe["volume"].rolling(vol_period, min_periods=vol_period).mean()

        # 额外定义回踩参考：价格与快线的相对位置（不使用未来数据）
        dataframe["pullback_ref"] = dataframe["close"] / dataframe["ema_fast"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """入场：上涨趋势 + 回踩后恢复 + 动量/成交量确认。"""
        conditions = [
            # 大趋势向上
            dataframe["close"] > dataframe["ema_trend"],
            # 快慢线结构维持多头
            dataframe["ema_fast"] > dataframe["ema_slow"],
            # 回踩位置：价格不远离快线，避免追高（0.985~1.01 之间）
            dataframe["pullback_ref"].between(0.985, 1.01),
            # 动量确认：RSI 不低于中性值阈值
            dataframe["rsi"] >= int(self.rsi_entry_threshold.value),
            # 成交量过滤：当前成交量高于均量
            dataframe["volume"] > dataframe["vol_ma"],
            dataframe["volume"] > 0,
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """出场：趋势减弱或动量转差时离场。"""
        conditions = [
            # 快线跌破慢线，趋势结构破坏
            dataframe["ema_fast"] < dataframe["ema_slow"],
            # 或 RSI 回落至较弱区域
            dataframe["rsi"] < int(self.rsi_exit_threshold.value),
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), "exit_long"] = 1

        return dataframe
