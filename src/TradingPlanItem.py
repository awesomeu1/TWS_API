import logging
from ibapi.common import *


class TradingPlanItem:

    readOnly: bool

    def __init__(self):
        self.symbol = None
        self.buyMode = "off"
        self.sellMode = "off"
        self.targetBuyPrice = None
        self.targetSellPrice = None
        self.targetLongPos = None
        self.targetShortPos = None
        self.targetBuyAttempt = 0
        self.targetSellAttempt = 0
        self.reqId = None
        self.readOnly = False
        self.priceFiveSecsAgo = None
        self.buyAttempt = 0
        self.sellAttempt = 0
        self.latestPos = 0
        self.lastPos = 0
        self.lastOrderId = None
        self.positionInitialized = False
        self.todayOpenPrice = None

    def __str__(self):
        return ("symbol=%s; \tbuyMode=%s;\tsellMode=%s;\treqId=%d;\ttargetBuyPrice=%10f;\ttargetSellPrice=%10f;\t"
                "targetLongPos=%d;\ttargetShortPos=%d;\ttargetBuyAttempt=%d;\ttargetSellAttempt=%d." %
                (self.symbol,
                 self.buyMode,
                 self.sellMode,
                 self.reqId,
                 self.targetBuyPrice,
                 self.targetSellPrice,
                 self.targetLongPos,
                 self.targetShortPos,
                 self.targetBuyAttempt,
                 self.targetSellAttempt))

    def setup(self,
              symbol: str,
              buyMode: str,
              sellMode: str,
              reqId: TickerId,
              targetBuyPrice: float,
              targetSellPrice: float,
              targetLongPos: int,
              targetShortPos: int,
              targetBuyAttempt: int,
              targetSellAttempt: int):
        if not self.readOnly:
            self.symbol = symbol
            self.buyMode = buyMode
            self.sellMode = sellMode
            self.reqId = reqId
            self.targetBuyPrice = targetBuyPrice
            self.targetSellPrice = targetSellPrice
            self.targetLongPos = targetLongPos
            self.targetShortPos = targetShortPos
            self.targetBuyAttempt = targetBuyAttempt
            self.targetSellAttempt = targetSellAttempt
            self.readOnly = True
        else:
            logging.error("ERROR. You're trying to override the TrandingPlanItem of: ", self)
