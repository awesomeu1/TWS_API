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
            targetSellPrice = round(targetBuyPrice * 0.9983, 2)
            tpItem.setup(item["SYMBOL"],
                         item["BUY_MODE"],
                         item["SELL_MODE"],
                         reqId,
                         targetBuyPrice, targetSellPrice,
                         item["TARGET_LONG_POS"],
                         item["TARGET_SHORT_POS"],
                         item["TARGET_BUY_ATTEMPT"],
                         item["TARGET_SELL_ATTEMPT"])
            self.addPlanItem(tpItem)

    def __str__(self):
        msg = []
        msg.append("Info about TradingPlan {}:\n".format(self.name))
        msg.append("===============================================================\n")
        for item in self.plan.values():
            msg.append(str(item) + "\n")
        msg.append("===============================================================")
        return " ".join(msg)
