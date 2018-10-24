
import sys
from TradingPlanItem import TradingPlanItem

class TradingPlan:

    def __init__(self, planName:str):
        self.name = planName;
        self.plan = {};
        self.planKeyedBySymbol = {};

    def addPlanItem(self, item:TradingPlanItem):
        self.plan.update({ item.reqID : item })
        self.planKeyedBySymbol.update({ item.symbol: item })

    def display(self):
        print("Info about TradingPlan {}:".format(self.name))
        for item in self.plan.values():
            print(item)
        print("Info about TradingPlan {} done.".format(self.name))

