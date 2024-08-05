class DataModel:
    def __init__(self):
        self.itemList = []
        self.stockBalanceList = []
        self.outstandingBalanceList = []
        self.autoTradeCoditionList = []

    class ItemInfo:
        def __init__(self, itemCode, itemName):
            self.itemCode = itemCode
            self.itemName = itemName

    class StockBalance:
        def __init__(self, itemCode, itemName, amount, buyingPrice, currentPrice, estimateProfit, profitRate):
            self.itemCode = itemCode
            self.itemName = itemName
            self.amount = amount
            self.buyingPrice = buyingPrice
            self.currentPrice = currentPrice
            self.estimateProfit = estimateProfit
            self.profitRate = profitRate

    class OutstandingBalance:
        def __init__(self, itemCode, itemName, orderNumber, orderVolume, orderPrice, outstandingVolume, tradeGubun, orderTime, currentPrice):
            self.itemCode = itemCode
            self.itemName = itemName
            self.orderNumber = orderNumber
            self.orderVolume = orderVolume
            self.orderPrice = orderPrice
            self.outstandingVolume = outstandingVolume
            self.tradeGubun = tradeGubun
            self.orderTime = orderTime
            self.currentPrice = currentPrice

    class AutoTradeCoditionInfo:
        def __init__(self, startTime, endTime, code, name, autoTradeGubun):
            self.startTime = startTime
            self.endTime = endTime
            self.code = code
            self.name = name
            self.autoTradeGubun = autoTradeGubun


