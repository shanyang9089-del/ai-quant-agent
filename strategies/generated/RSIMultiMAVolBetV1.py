from datetime import datetime
from typing import Any

import talib.abstract as ta
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class RSIMultiMAVolBetV1(IStrategy):
    """
    RSIMultiMAVolBetV1
    - 15m / futures / 仅做多
    - 简单、低过滤、趋势跟随
    - 固定 20x 杠杆 + 固定 20 USDT 小仓位实验策略
    """

    INTERFACE_VERSION = 3

    # 仅做多
    can_short = False
    timeframe = "15m"
    startup_candle_count = 120

    # 固定大目标止盈（实验设定）
    minimal_roi = {
        "0": 1.0,
    }

    # 固定极宽兜底止损（实验设定）
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
        """简单趋势跟随入场：仅保留 3 个核心条件。"""
        entry_condition = (
            # 核心条件 1：多均线趋势成立
            (dataframe["ema_fast"] > dataframe["ema_mid"])
            & (dataframe["ema_mid"] > dataframe["ema_slow"])
            # 核心条件 2：RSI 动量成立
            & (dataframe["rsi"] > 55)
            # 核心条件 3：成交量确认
            & (dataframe["volume"] > dataframe["volume_ma"])
            # 基础数据清洗，避免无效成交量K线
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[entry_condition, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        """离场保持极简：不叠加复杂技术离场，主要由 ROI 与止损控制。"""
        dataframe["exit_long"] = 0
        return dataframe
