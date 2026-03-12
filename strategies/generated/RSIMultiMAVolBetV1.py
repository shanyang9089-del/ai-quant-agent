from datetime import datetime
from typing import Any

import talib.abstract as ta
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class RSIMultiMAVolBetV1(IStrategy):
    """
    RSIMultiMAVolBetV1
    - 15m 周期、仅做多、futures 使用场景
    - 低过滤、偏“反转起点下注”的原型策略
    - 通过 leverage() 固定 20x（受交易所 max_leverage 限制）
    """

    INTERFACE_VERSION = 3

    # 仅做多
    can_short = False
    timeframe = "15m"
    startup_candle_count = 120

    # 固定止盈：1:2 风格（约 5%）
    minimal_roi = {
        "0": 0.05,
    }

    # 仅作为系统兜底，给固定止损，保持单变量实验
    stoploss = -0.02

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        """固定 20x 杠杆，但不超过交易所/市场允许上限。"""
        return min(20.0, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """只使用 RSI + 多 EMA + 成交量均线（无额外指标）。"""
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=8)
        dataframe["ema_mid"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=55)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["volume_ma"] = dataframe["volume"].rolling(20, min_periods=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """
        入场尽量简化，强调“反转起点”：
        1) 价格重新站上快线
        2) RSI 从偏弱区重新上穿
        3) 成交量高于均量
        4) 仅加一个轻量结构过滤，避免在明显弱势末端盲目抄底
        """
        rsi_threshold = 45

        entry_condition = (
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["close"].shift(1) <= dataframe["ema_fast"].shift(1))
            & (dataframe["rsi"] > rsi_threshold)
            & (dataframe["rsi"].shift(1) <= rsi_threshold)
            & (dataframe["volume"] > dataframe["volume_ma"])
            & (dataframe["volume"] > 0)
            # 轻量结构：中线不低于慢线，避免在明显下行尾段频繁接刀
            & (dataframe["ema_mid"] >= dataframe["ema_slow"])
            # 避免站上快线后已经离快线过远，减少追高概率
            & (dataframe["close"] <= dataframe["ema_mid"] * 1.02)
        )

        dataframe.loc[entry_condition, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """
        出场保持极简：主要依赖 minimal_roi 固定止盈。
        这里不增加复杂技术离场条件。
        """
        dataframe["exit_long"] = 0
        return dataframe
