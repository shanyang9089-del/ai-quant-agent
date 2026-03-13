from datetime import datetime
from typing import Any

import talib.abstract as ta
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class RSIMultiMAVolBetV1(IStrategy):
    """
    RSIMultiMAVolBetV1
    - 15m / futures / 仅做多
    - 小仓位 + 20x 杠杆的“第一脚转强下注”策略
    - 不做复杂量化系统，只保留最少指标与最少决策
    """

    INTERFACE_VERSION = 3

    # 仅做多
    can_short = False
    timeframe = "15m"
    startup_candle_count = 120

    # 固定目标：单笔 100%
    minimal_roi = {
        "0": 1.0,
    }

    # 按实验设计固定为极宽兜底止损
    stoploss = -0.99

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
        """固定 20x，但不超过交易所允许的最大杠杆。"""
        return min(20.0, max_leverage)

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        """固定每次开仓 20 USDT。"""
        return 20.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """只使用 RSI + 多 EMA + 成交量均线。"""
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=8)
        dataframe["ema_mid"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=55)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["volume_ma"] = dataframe["volume"].rolling(20, min_periods=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """严格按实验设计执行“刚转强第一脚”入场条件。"""
        entry_condition = (
            (dataframe["ema_fast"] > dataframe["ema_mid"])
            & (dataframe["ema_mid"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"] > dataframe["ema_fast"].shift(1))
            & (dataframe["ema_mid"] > dataframe["ema_mid"].shift(1))
            & (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["close"].shift(1) <= dataframe["ema_fast"].shift(1))
            & (dataframe["rsi"] > 50)
            & (dataframe["rsi"].shift(1) <= 50)
            & (dataframe["volume"] > dataframe["volume_ma"] * 1.2)
            & (dataframe["close"] <= dataframe["ema_fast"] * 1.01)
        )

        dataframe.loc[entry_condition, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """极简离场：不叠加技术离场，主要由 ROI 与止损控制。"""
        dataframe["exit_long"] = 0
        return dataframe
