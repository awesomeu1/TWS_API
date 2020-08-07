import yaml
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

    def parseYaml(self, tPlanFileName: str, firstTime: bool, startingReqId: TickerId):
        tPlanFile = open(tPlanFileName, "r")
        tPlanYaml = yaml.load(tPlanFile, Loader=yaml.FullLoader)
        tPlanFile.close()

        reqId = startingReqId

        for item in tPlanYaml:
            reqId = reqId + 1

            if firstTime:
                tpItem = TradingPlanItem()
            else:
                tpItem = self.planKeyedBySymbol[item["SYMBOL"]]

            targetBuyPrice = item["TARGET_BUY_PRICE"]
            targetSellPrice = round(targetBuyPrice * 0.997, 2)
            tpItem.setup(item["SYMBOL"],
                         item["ENABLED"],
                         reqId,
                         targetBuyPrice, targetSellPrice,
                         item["TARGET_LONG_POS"],
                         item["TARGET_SHORT_POS"],
                         item["BUY_ATTEMPT_LIMIT"],
                         item["SELL_ATTEMPT_LIMIT"])
            self.addPlanItem(tpItem)

    def __str__(self):
        msg = []
        msg.append("Info about TradingPlan {}:\n".format(self.name))
        msg.append("===============================================================\n")
        for item in self.plan.values():
            msg.append(str(item) + "\n")
        msg.append("===============================================================")
        return " ".join(msg)
