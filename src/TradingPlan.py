from ibapi.common import *
from TradingPlanItem import TradingPlanItem


class TradingPlan:

    def __init__(self, planName: str):
        self.name = planName
        self.plan = {}
        self.planKeyedBySymbol = {}

    def addPlanItem(self, item: TradingPlanItem):
        self.plan.update({item.reqId: item})
        self.planKeyedBySymbol.update({item.symbol: item})

    def parseYaml(self, yml, startingReqId: TickerId):
        reqId = startingReqId

        for item in yml:
            reqId = reqId + 1
            tpItem = TradingPlanItem()
            targetBuyPrice = item["TARGET_BUY_PRICE"]
            targetSellPrice = round(targetBuyPrice * 0.9985, 2)
            tpItem.setup(item["SYMBOL"], reqId, targetBuyPrice, targetSellPrice,
                         item["TARGET_LONG_POS"], item["TARGET_SHORT_POS"],
                         item["AUTO_MODE"])
            self.addPlanItem(tpItem)

    def display(self):
        print("Info about TradingPlan {}:".format(self.name))
        print("===============================================================")
        for item in self.plan.values():
            print(item)
        print("===============================================================")
        print("Info about TradingPlan {} done.".format(self.name))
