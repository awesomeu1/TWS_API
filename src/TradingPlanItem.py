import logging
from ibapi.common import *


class TradingPlanItem:

    readOnly: bool

    def __init__(self):
        self.symbol = None
        self.targetBuyPrice = None
        self.targetSellPrice = None
        self.targetLongPos = None
        self.targetShortPos = None
        self.targetBuyAttempt = 100
        self.targetSellAttempt = 100
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
        self.autoMode = False

    def __str__(self):
        return ("symbol = %s;\tautoMode=%s;\ttargetBuyPrice=%10f;\ttargetSellPrice=%10f;\t"
                "targetLongPos=%d;\ttargetShortPos=%d;" %
                (self.symbol,
                 self.autoMode,
                 self.targetBuyPrice,
                 self.targetSellPrice,
                 self.targetLongPos,
                 self.targetShortPos))

    def setup(self,
              symbol: str,
              reqId: TickerId,
              targetBuyPrice: float,
              targetSellPrice: float,
              targetLongPos: int,
              targetShortPos: int,
              autoMode: bool = False):
        if not self.readOnly:
            self.symbol = symbol
            self.reqId = reqId
            self.targetBuyPrice = targetBuyPrice
            self.targetSellPrice = targetSellPrice
            self.targetLongPos = targetLongPos
            self.targetShortPos = targetShortPos
            self.autoMode = autoMode
            self.readOnly = True
        else:
            logging.error("ERROR. You're trying to override the TrandingPlanItem of: ", self)
