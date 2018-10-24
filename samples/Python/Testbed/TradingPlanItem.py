
import sys

class TradingPlanItem():

    def __init__(self):
        self.symbol                 = None
        self.targetBuyPrice         = None
        self.targetSellPrice        = None
        self.targetLongPos          = None
        self.targetShortPos         = None
        self.reqID                  = None
        self.readOnly               = False
        self.priceFiveSecsAgo       = None
        self.buyAttempt             = 0
        self.sellAttempt            = 0
        self.latestPos              = 0
        self.lastPos                = 0
        self.lastOrderId            = None
        self.positionInitialized    = False
        self.isActive               = False
        self.todayOpenPrice         = None
        self.autoMode               = False

    def __str__(self):
        return ("symbol %s isActive %s; autoMode %s; targetBuyPrice %f; targetSellPrice %f;"\
                " targetLongPos %d; targetShortPos %d;" %
                (self.symbol, self.isActive, self.autoMode,
                 self.targetBuyPrice, self.targetSellPrice,
                 self.targetLongPos, self.targetShortPos))

    def setup(self, symbol:str, reqID:int,
                    targetBuyPrice:float, targetSellPrice:float,
                    targetLongPos:int, targetShortPos:int,
                    active:bool, autoMode:bool=False):
        if (not self.readOnly):
            self.symbol         = symbol
            self.targetBuyPrice = targetBuyPrice
            self.targetSellPrice= targetSellPrice
            self.targetLongPos  = targetLongPos
            self.targetShortPos = targetShortPos
            self.readOnly       = True
            self.reqID          = reqID
            self.isActive       = active
            self.autoMode       = autoMode
        else:
            logging.error("ERROR. You're trying to override the TrandingPlanItem of: ", self)