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
import threading

from ibapi import wrapper
from ibapi import utils
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import *
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState

# My own modules
from Contracts import Contracts
from Orders import Orders
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

    def setupTradingPlan(self, firstTime: bool):
        # ReqId begins at 8800
        self.tradingPlan.parseYaml("trading_plan.yml", firstTime, 8800)
        if firstTime:
            logging.critical("First time setting up the trading plan.")
        else:
            logging.critical("Refreshing trading plan.")
        logging.critical(self.tradingPlan)

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

            # Request position updates
            self.reqPositions()

            queryTime = (datetime.datetime.today()).strftime("%Y%m%d %H:%M:%S")

            # Request market data and today's Open price
            for reqId,v in self.tradingPlan.plan.items():
                self.reqRealTimeBars(reqId, Contracts.USStockAtSmart(v.symbol), 5, "TRADES", True, [])
                self.reqHistoricalData(reqId, Contracts.USStockAtSmart(v.symbol), queryTime,
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
        for reqId, v in self.tradingPlan.plan.items():
            self.cancelRealTimeBars(reqId)
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
            logging.critical("lastPos & latestPos of {} is initialized to {}".format(tpItem.symbol, position))

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
        if (tpItem.buyAttempted >= tpItem.buyAttemptLimit and
            tpItem.targetLongPos > 0):

            logging.critical(f"Resetting targetLongPos for {tpItem.symbol} to 0; buyAttempted is {tpItem.buyAttempted}")
            tpItem.targetLongPos = 0

        if (tpItem.sellAttempted >= tpItem.sellAttemptLimit and
            tpItem.targetShortPos < 0):

            logging.critical(f"Resetting targetShortPos for {tpItem.symbol} to 0; sellAttempted is {tpItem.sellAttempted}")
            tpItem.targetShortPos   = 0

        # Detect price movement with reference to the price target
        # Buy
        if (tpItem.enabled and
            tpItem.latestPos < tpItem.targetLongPos and
            tpItem.priceFiveSecsAgo is not None and
            close >= targetBuyPrice and
            close >= tpItem.priceFiveSecsAgo and
            targetBuyPrice >= tpItem.priceFiveSecsAgo):

            ## Cancel the open order. Maybe the order has not been filled already.
            #if (tpItem.lastOrderId is not None):
            #    self.cancelOrder(tpItem.lastOrderId)

            # Place a buy order
            myContract  = Contracts.USStockAtSmart(tpItem.symbol)
            myOrderId   = self.nextOrderId()
            myOrderSize = tpItem.targetLongPos - tpItem.latestPos
            #myOrder     = Orders.PeggedToMarket("BUY", myOrderSize, 0.1)
            myOrder     = Orders.MarketOrder("BUY", myOrderSize)

            self.placeOrder(myOrderId, myContract, myOrder)

            tpItem.lastOrderId = myOrderId

            # Increment buy attempt count
            tpItem.buyAttempted += 1

            logging.critical("@@@ BUY {} is triggered. "
                             " current price={}"
                             " targetBuyPrice={}"
                             " priceFiveSecsAgo={}"
                             " targetLongPos={}"
                             " latestPos={}"
                             " buyAttempted={}".format(tpItem.symbol,
                                                        close,
                                                        targetBuyPrice,
                                                        tpItem.priceFiveSecsAgo,
                                                        tpItem.targetLongPos,
                                                        tpItem.latestPos,
                                                        tpItem.buyAttempted))

        # Sell
        if (tpItem.enabled and
            tpItem.latestPos > tpItem.targetShortPos and
            tpItem.priceFiveSecsAgo is not None and
            close < targetSellPrice and
            close < tpItem.priceFiveSecsAgo and
            targetSellPrice <= tpItem.priceFiveSecsAgo):

            ## Cancel the open order. Maybe the order has not been filled already.
            #if (tpItem.lastOrderId != None):
            #    self.cancelOrder(tpItem.lastOrderId)

            # Place a sell order
            myContract  = Contracts.USStockAtSmart(tpItem.symbol)
            myOrderId   = self.nextOrderId()
            myOrderSize = tpItem.latestPos - tpItem.targetShortPos
            myOrder     = Orders.MarketOrder("SELL", myOrderSize)

            self.placeOrder(myOrderId, myContract, myOrder)

            tpItem.lastOrderId = myOrderId

            # Increment sell attempt count
            tpItem.sellAttempted += 1

            logging.critical("@@@ SELL {} is triggered."
                   " current price={}"
                   " targetSellPrice={}"
                   " priceFiveSecsAgo={}"
                   " targetShortPos={}"
                   " latestPos={}"
                   " sellAttempted={}".format(tpItem.symbol,
                                              close,
                                              targetSellPrice,
                                              tpItem.priceFiveSecsAgo,
                                              tpItem.targetShortPos,
                                              tpItem.latestPos,
                                              tpItem.sellAttempted))

        if tpItem.priceFiveSecsAgo is None:
            logging.critical("priceFiveSecsAgo of {} is initialized to {}".format(tpItem.symbol, close))

        # Update priceFiveSecsAgo
        tpItem.priceFiveSecsAgo = close

    # ! [realtimebar]

    @iswrapper
    # ! [historicaldata]
    def historicalData(self, reqId:int, bar: BarData):
        tpItem = self.tradingPlan.plan[reqId]
        if (tpItem.todayOpenPrice == None):
            tpItem.todayOpenPrice = bar.open
            logging.critical("Set %s Open price to %f" % (tpItem.symbol, bar.open))
        super().historicalData(reqId, bar)
    # ! [historicaldata]


def wait_and_refresh_trading_plan(app: TestApp):
    while True:
        do_refresh = input("Do you want to refresh trading plan?[yes or no]:\n")
        if do_refresh == "yes":
            app.setupTradingPlan(firstTime=False)

def main():
    SetupLogger()
    logging.getLogger().setLevel(logging.INFO)
    logging.info("now is %s", datetime.datetime.now())

    try:
        app = TestApp()
        # ! [connect]
        # Paper trading port number: 7497
        # Live trading port number:  7496
        app.connect("127.0.0.1", 7496, clientId=95131)
        # ! [connect]
        print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                      app.twsConnectionTime()))

        # setup tranding plan
        app.tradingPlan = TradingPlan("MarketWatcher")
        app.setupTradingPlan(firstTime=True)

        refresh_tplan = threading.Thread(target=wait_and_refresh_trading_plan, args=(app,))
        refresh_tplan.start()

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
