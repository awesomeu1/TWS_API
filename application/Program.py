"""
Copyright (C) 2019 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""

import argparse
import datetime
import collections
import inspect

import logging
import time
import os.path

from ibapi import wrapper
from ibapi import utils
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import * # @UnusedWildImport
from ibapi.order_condition import * # @UnusedWildImport
from ibapi.contract import * # @UnusedWildImport
from ibapi.order import * # @UnusedWildImport
from ibapi.order_state import * # @UnusedWildImport
from ibapi.ticktype import * # @UnusedWildImport
from ibapi.tag_value import TagValue

from ibapi.account_summary_tags import *

from Contracts import Contracts
from Orders import Orders
from TradingPlanItem import TradingPlanItem
from TradingPlan import TradingPlan


def SetupLogger():
    if not os.path.exists("log"):
        os.makedirs("log")

    time.strftime("pyibapi.%Y%m%d_%H%M%S.log")

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'

    timefmt = '%y%m%d_%H:%M:%S'

    # logging.basicConfig( level=logging.DEBUG,
    #                    format=recfmt, datefmt=timefmt)
    logging.basicConfig(filename=time.strftime("log/pyibapi.%y%m%d_%H%M%S.log"),
                        filemode="w",
                        level=logging.INFO,
                        format=recfmt, datefmt=timefmt)
    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logger.addHandler(console)


# ! [socket_declare]
class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        # ! [socket_declare]

        # how many times a method is called to see test coverage
        self.clntMeth2callCount = collections.defaultdict(int)
        self.clntMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nReq = collections.defaultdict(int)
        self.setupDetectReqId()

    def countReqId(self, methName, fn):
        def countReqId_(*args, **kwargs):
            self.clntMeth2callCount[methName] += 1
            idx = self.clntMeth2reqIdIdx[methName]
            if idx >= 0:
                sign = -1 if 'cancel' in methName else 1
                self.reqId2nReq[sign * args[idx]] += 1
            return fn(*args, **kwargs)

        return countReqId_

    def setupDetectReqId(self):

        methods = inspect.getmembers(EClient, inspect.isfunction)
        for (methName, meth) in methods:
            if methName != "send_msg":
                # don't screw up the nice automated logging in the send_msg()
                self.clntMeth2callCount[methName] = 0
                # logging.debug("meth %s", name)
                sig = inspect.signature(meth)
                for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                    (paramName, param) = pnameNparam # @UnusedVariable
                    if paramName == "reqId":
                        self.clntMeth2reqIdIdx[methName] = idx

                setattr(TestClient, methName, self.countReqId(methName, meth))

                # print("TestClient.clntMeth2reqIdIdx", self.clntMeth2reqIdIdx)


# ! [ewrapperimpl]
class TestWrapper(wrapper.EWrapper):
    # ! [ewrapperimpl]
    def __init__(self):
        wrapper.EWrapper.__init__(self)

        self.wrapMeth2callCount = collections.defaultdict(int)
        self.wrapMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nAns = collections.defaultdict(int)
        self.setupDetectWrapperReqId()

    # TODO: see how to factor this out !!

    def countWrapReqId(self, methName, fn):
        def countWrapReqId_(*args, **kwargs):
            self.wrapMeth2callCount[methName] += 1
            idx = self.wrapMeth2reqIdIdx[methName]
            if idx >= 0:
                self.reqId2nAns[args[idx]] += 1
            return fn(*args, **kwargs)

        return countWrapReqId_

    def setupDetectWrapperReqId(self):

        methods = inspect.getmembers(wrapper.EWrapper, inspect.isfunction)
        for (methName, meth) in methods:
            self.wrapMeth2callCount[methName] = 0
            # logging.debug("meth %s", name)
            sig = inspect.signature(meth)
            for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                (paramName, param) = pnameNparam # @UnusedVariable
                # we want to count the errors as 'error' not 'answer'
                if 'error' not in methName and paramName == "reqId":
                    self.wrapMeth2reqIdIdx[methName] = idx

            setattr(TestWrapper, methName, self.countWrapReqId(methName, meth))

            # print("TestClient.wrapMeth2reqIdIdx", self.wrapMeth2reqIdIdx)


# this is here for documentation generation
"""
#! [ereader]
        # You don't need to run this in your code!
        self.reader = reader.EReader(self.conn, self.msg_queue)
        self.reader.start()   # start thread
#! [ereader]
"""

# ! [socket_init]
class TestApp(TestWrapper, TestClient):
    def __init__(self):
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper=self)
        # ! [socket_init]
        self.nKeybInt = 0
        self.started = False
        self.nextValidOrderId = None
        self.permId2ord = {}
        self.reqId2nErr = collections.defaultdict(int)
        self.globalCancelOnly = False
        self.simplePlaceOid = None

    def dumpTestCoverageSituation(self):
        for clntMeth in sorted(self.clntMeth2callCount.keys()):
            logging.debug("ClntMeth: %-30s %6d" % (clntMeth,
                                                   self.clntMeth2callCount[clntMeth]))

        for wrapMeth in sorted(self.wrapMeth2callCount.keys()):
            logging.debug("WrapMeth: %-30s %6d" % (wrapMeth,
                                                   self.wrapMeth2callCount[wrapMeth]))

    def dumpReqAnsErrSituation(self):
        logging.debug("%s\t%s\t%s\t%s" % ("ReqId", "#Req", "#Ans", "#Err"))
        for reqId in sorted(self.reqId2nReq.keys()):
            nReq = self.reqId2nReq.get(reqId, 0)
            nAns = self.reqId2nAns.get(reqId, 0)
            nErr = self.reqId2nErr.get(reqId, 0)
            logging.debug("%d\t%d\t%s\t%d" % (reqId, nReq, nAns, nErr))

    @iswrapper
    # ! [connectack]
    def connectAck(self):
        if self.asynchronous:
            self.startApi()
    # ! [connectack]

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)
    # ! [nextvalidid]

        # we can start now
        self.start()

    def setupTradingPlan(self):
        self.tradingPlan = TradingPlan("MarketWatcher")

        # ReqId begins at 8800
        reqId = 8800

        reqId = reqId + 1
        tpItem = TradingPlanItem()
        targetBuyPrice  = 152.00
        targetSellPrice = round(targetBuyPrice * 0.9995, 2)
        tpItem.setup("FB", reqId, targetBuyPrice, targetSellPrice, 100, 0)
        self.tradingPlan.addPlanItem(tpItem)

        reqId = reqId + 1
        tpItem = TradingPlanItem()
        targetBuyPrice  = 152.00
        targetSellPrice = round(targetBuyPrice * 0.9995, 2)
        tpItem.setup("NVDA", reqId, targetBuyPrice, targetSellPrice, 200, 0)
        self.tradingPlan.addPlanItem(tpItem)

        reqId = reqId + 1
        tpItem = TradingPlanItem()
        targetBuyPrice  = 63.80
        targetSellPrice = round(targetBuyPrice * 0.9995, 2)
        tpItem.setup("QCOM", reqId, targetBuyPrice, targetSellPrice, 200, 0)
        self.tradingPlan.addPlanItem(tpItem)

        self.tradingPlan.display()

    def start(self):
        if self.started:
            return

        self.started = True

        if self.globalCancelOnly:
            print("Executing GlobalCancel only")
            self.reqGlobalCancel()
        else:
            print("Executing requests")
            # Cancel all orders
            self.reqGlobalCancel()
            # Request RealTime market data
            self.reqMarketDataType(MarketDataTypeEnum.REALTIME)
            #self.accountOperations_req()

            # Request position updates
            self.reqPositions()

            queryTime = (datetime.datetime.today()).strftime("%Y%m%d %H:%M:%S")

            # Request market data and today's Open price
            for reqId,v in self.tradingPlan.plan.items():
                self.reqRealTimeBars(reqId, ContractSamples.USStockAtSmart(v.symbol), 5, "TRADES", True, [])
                self.reqHistoricalData(reqId, ContractSamples.USStockAtSmart(v.symbol), queryTime,
                                       "1 D", "1 day", "TRADES", 1, 1, False, [])

            print("Executing requests ... finished")

    def keyboardInterrupt(self):
        self.nKeybInt += 1
        if self.nKeybInt == 1:
            self.stop()
        else:
            print("Finishing test")
            self.done = True

    def stop(self):
        print("Executing cancels")
        self.orderOperations_cancel()
        self.accountOperations_cancel()
        self.tickDataOperations_cancel()
        self.marketDepthOperations_cancel()
        self.realTimeBars_cancel()
        self.historicalDataRequests_cancel()
        self.optionsOperations_cancel()
        self.marketScanners_cancel()
        self.reutersFundamentals_cancel()
        self.bulletins_cancel()
        print("Executing cancels ... finished")

    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    @iswrapper
    # ! [orderstatus]
    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
                            avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,
              "Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
              "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",
              lastFillPrice, "ClientId:", clientId, "WhyHeld:",
              whyHeld, "MktCapPrice:", mktCapPrice)
    # ! [orderstatus]

    @iswrapper
    # ! [position]
    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        super().position(account, contract, position, avgCost)
        print("Position.", "Account:", account, "Symbol:", contract.symbol, "SecType:",
              contract.secType, "Currency:", contract.currency,
              "Position:", position, "Avg cost:", avgCost)

        tpItem = self.tradingPlan.planKeyedBySymbol[contract.symbol]
        # Update position info
        if (tpItem.positionInitialized):
            tpItem.lastPos     = tpItem.latestPos
            tpItem.latestPos   = position
        else:
            tpItem.positionInitialized = True
            tpItem.lastPos   = position
            tpItem.latestPos = position

        #if (tpItem.latestPos > tpItem.lastPos):
        #    tpItem.buyAttempt = 0
        #elif (tpItem.latestPos < tpItem.lastPos):
        #    tpItem.sellAttempt = 0
    # ! [position]

    @iswrapper
    # ! [realtimebar]
    def realtimeBar(self, reqId: TickerId, time:int, open_: float, high: float, low: float, close: float,
                        volume: int, wap: float, count: int):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)

        tpItem = self.tradingPlan.plan[reqId]

        targetBuyPrice  = tpItem.targetBuyPrice
        targetSellPrice = tpItem.targetSellPrice

        # If we've tried more than X times to establish a position, we'll clear
        # our target position, so we'd stay away from the stock for a while.
        if (tpItem.buyAttempt >= tpItem.targetBuyAttempt and
            tpItem.targetLongPos > 0):

            print("Resetting targetLongPos for %s to 0; buyAttempt is %d" %
                  (tpItem.symbol, tpItem.buyAttempt))
            logging.info("Resetting targetLongPos for %s to 0; buyAttempt is %d" %
                         (tpItem.symbol, tpItem.buyAttempt))
            tpItem.targetLongPos = 0

        if (tpItem.sellAttempt >= tpItem.targetSellAttempt and
            tpItem.targetShortPos < 0):

            print("Resetting targetShortPos for %s to 0; sellAttempt is %d" %
                  (tpItem.symbol, tpItem.sellAttempt))
            logging.info("Resetting targetShortPos for %s to 0; sellAttempt is %d" %
                         (tpItem.symbol, tpItem.sellAttempt))
            tpItem.targetShortPos   = 0

        # Detect price movement with reference to the price target
        # Buy
        if (tpItem.latestPos < tpItem.targetLongPos and
            tpItem.priceFiveSecsAgo != None and
            close >= targetBuyPrice and
            close >= tpItem.priceFiveSecsAgo and
            targetBuyPrice >= tpItem.priceFiveSecsAgo):

            # Cancel the open order. Maybe the order has been filled already.
            if (tpItem.lastOrderId != None):
                self.cancelOrder(tpItem.lastOrderId)

            # Increment buy attempt count
            tpItem.buyAttempt += 1

            print("@@@ BUY ", tpItem.symbol, "is triggered. @@@",
                  " autoMode is ", tpItem.autoMode,
                  " Today's Open price is ", tpItem.todayOpenPrice,
                  " Its current price is ", close,
                  " targetBuyPrice is ", targetBuyPrice,
                  " priceFiveSecsAgo is ", tpItem.priceFiveSecsAgo,
                  " targetLongPos is ", tpItem.targetLongPos,
                  " latestPos is ", tpItem.latestPos,
                  " buyAttempt is ", tpItem.buyAttempt)

            logging.info("@@@ BUY %s is triggered. @@@" \
                         " autoMode is %s;"\
                         " Its current price is %f;" \
                         " targetBuyPrice is %f;"\
                         " priceFiveSecsAgo is %f;"\
                         " targetLongPos is %d;"\
                         " latestPos is %d;" \
                         " buyAttempt is %d;" %
                         (tpItem.symbol,
                          tpItem.autoMode,
                          close,
                          targetBuyPrice,
                          tpItem.priceFiveSecsAgo,
                          tpItem.targetLongPos,
                          tpItem.latestPos,
                          tpItem.buyAttempt))

            # Place a buy order
            myContract  = ContractSamples.USStockAtSmart(tpItem.symbol)
            myOrderId   = self.nextOrderId()
            myOrderSize = tpItem.targetLongPos - tpItem.latestPos
            myOrder     = OrderSamples.LimitOrder("BUY", myOrderSize, targetBuyPrice)

            self.placeOrder(myOrderId, myContract, myOrder)

            tpItem.lastOrderId = myOrderId

        # Sell
        if (tpItem.latestPos > tpItem.targetShortPos and
            tpItem.priceFiveSecsAgo != None and
            close < targetSellPrice and
            close < tpItem.priceFiveSecsAgo and
            targetSellPrice <= tpItem.priceFiveSecsAgo):

            # Cancel the open order. Maybe the order has been filled already.
            if (tpItem.lastOrderId != None):
                self.cancelOrder(tpItem.lastOrderId)

            # Increment sell attempt count
            tpItem.sellAttempt += 1

            print("@@@ SELL", tpItem.symbol, "is triggered. @@@",
                  " autoMode is ", tpItem.autoMode,
                  " Today's Open price is ", tpItem.todayOpenPrice,
                  " Its current price is ", close,
                  " targetSellPrice is ", targetSellPrice,
                  " priceFiveSecsAgo is ", tpItem.priceFiveSecsAgo,
                  " targetShortPos is ", tpItem.targetShortPos,
                  " latestPos is ", tpItem.latestPos,
                  " sellAttempt is ", tpItem.sellAttempt)

            logging.info("@@@ SELL %s is triggered. @@@" \
                         " autoMode is %s;" \
                         " current price is %f;" \
                         " targetSellPrice is %f;" \
                         " priceFiveSecsAgo is %f;" \
                         " targetShortPos is %d;" \
                         " latestPos is %d;" \
                         " sellAttempt is %d;" %
                         (tpItem.symbol,
                          tpItem.autoMode,
                          close,
                          targetSellPrice,
                          tpItem.priceFiveSecsAgo,
                          tpItem.targetShortPos,
                          tpItem.latestPos,
                          tpItem.sellAttempt))

            # Place a sell order
            myContract  = ContractSamples.USStockAtSmart(tpItem.symbol)
            myOrderId   = self.nextOrderId()
            myOrderSize = tpItem.latestPos - tpItem.targetShortPos
            myOrder     = OrderSamples.LimitOrder("SELL", myOrderSize, targetSellPrice)

            self.placeOrder(myOrderId, myContract, myOrder)

            tpItem.lastOrderId = myOrderId

        # Update priceFiveSecsAgo
        tpItem.priceFiveSecsAgo = close

    # ! [realtimebar]

    @iswrapper
    # ! [historicaldata]
    def historicalData(self, reqId:int, bar: BarData):
        print("HistoricalData. ReqId:", reqId, "BarData.", bar)
        tpItem = self.tradingPlan.plan[reqId]
        if (tpItem.todayOpenPrice == None):
            tpItem.todayOpenPrice = bar.open
            print("Set ", tpItem.symbol, " Open price to ", bar.open)
            logging.info("Set %s Open price to %f" % (tpItem.symbol, bar.open))
        super().historicalData(reqId, bar)
    # ! [historicaldata]

    @iswrapper
    # ! [historicaldataend]
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)
    # ! [historicaldataend]

    @iswrapper
    # ! [completedorder]
    def completedOrder(self, contract: Contract, order: Order,
                  orderState: OrderState):
        super().completedOrder(contract, order, orderState)
        print("CompletedOrder. PermId:", order.permId, "ParentPermId:", utils.longToStr(order.parentPermId), "Account:", order.account,
              "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:", contract.exchange,
              "Action:", order.action, "OrderType:", order.orderType, "TotalQty:", order.totalQuantity,
              "CashQty:", order.cashQty, "FilledQty:", order.filledQuantity,
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status,
              "Completed time:", orderState.completedTime, "Completed Status:" + orderState.completedStatus)
    # ! [completedorder]

    @iswrapper
    # ! [completedordersend]
    def completedOrdersEnd(self):
        super().completedOrdersEnd()
        print("CompletedOrdersEnd")
    # ! [completedordersend]

def main():
    SetupLogger()
    logging.debug("now is %s", datetime.datetime.now())
    logging.getLogger().setLevel(logging.INFO)

    # enable logging when member vars are assigned
    from ibapi import utils
    from ibapi.order import Order
    Order.__setattr__ = utils.setattr_log
    from ibapi.contract import Contract, DeltaNeutralContract
    Contract.__setattr__ = utils.setattr_log
    DeltaNeutralContract.__setattr__ = utils.setattr_log
    from ibapi.tag_value import TagValue
    TagValue.__setattr__ = utils.setattr_log
    TimeCondition.__setattr__ = utils.setattr_log
    ExecutionCondition.__setattr__ = utils.setattr_log
    MarginCondition.__setattr__ = utils.setattr_log
    PriceCondition.__setattr__ = utils.setattr_log
    PercentChangeCondition.__setattr__ = utils.setattr_log
    VolumeCondition.__setattr__ = utils.setattr_log

    try:
        app = TestApp()
        # ! [connect]
        # Paper trading port number: 7497
        # Live trading port number:  7496
        app.connect("127.0.0.1", 7497, clientId=95131)
        # ! [connect]
        print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                      app.twsConnectionTime()))

        # setup tranding plan
        app.setupTradingPlan()

        # ! [clientrun]
        app.run()
        # ! [clientrun]
    except:
        raise
    finally:
        app.dumpTestCoverageSituation()
        app.dumpReqAnsErrSituation()


if __name__ == "__main__":
    main()
