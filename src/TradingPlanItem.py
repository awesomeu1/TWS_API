import logging
from ibapi.common import *


class TradingPlanItem:

    readOnly: bool

    def __init__(self):
        self.symbol = None
        self.enabled = False
        self.targetBuyPrice = None
        self.targetSellPrice = None
        self.targetLongPos = None
        self.targetShortPos = None
        self.buyAttemptLimit = 0
        self.sellAttemptLimit = 0
        self.reqId = None
        self.readOnly = False
        self.priceFiveSecsAgo = None
        self.buyAttempted = 0
        self.sellAttempted = 0
        self.latestPos = 0
        self.lastPos = 0
        self.lastOrderId = None
        self.positionInitialized = False
        self.todayOpenPrice = None

    def __str__(self):
        return ("symbol=%s; \tenabled=%s;\treqId=%d;\ttargetBuyPrice=%10f;\ttargetSellPrice=%10f;\t"
                "targetLongPos=%d;\ttargetShortPos=%d;\tbuyAttemptLimit=%d;\tsellAttemptLimit=%d." %
                (self.symbol,
                 self.enabled,
                 self.reqId,
                 self.targetBuyPrice,
                 self.targetSellPrice,
                 self.targetLongPos,
                 self.targetShortPos,
                 self.buyAttemptLimit,
                 self.sellAttemptLimit))

    def setup(self,
              symbol: str,
              enabled: bool,
              reqId: TickerId,
              targetBuyPrice: float,
              targetSellPrice: float,
              targetLongPos: int,
              targetShortPos: int,
              buyAttemptLimit: int,
              sellAttemptLimit: int):
        if not self.readOnly:
            self.symbol = symbol
            self.enabled = enabled
            self.reqId = reqId
            self.targetBuyPrice = targetBuyPrice
            self.targetSellPrice = targetSellPrice
            self.targetLongPos = targetLongPos
            self.targetShortPos = targetShortPos
            self.buyAttemptLimit = buyAttemptLimit
            self.sellAttemptLimit = sellAttemptLimit
            self.readOnly = True
        else:
            logging.error("ERROR. You're trying to override the TrandingPlanItem of: ", self)
