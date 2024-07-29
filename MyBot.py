import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from PyQt5.QAxContainer import *

import dataModel as dm

form_class = uic.loadUiType('main_window.ui')[0]


class MyBot(QMainWindow, form_class):
    # 생성자
    def __init__(self):
        super().__init__()
        self.setUI()
        self.myModel = dm.DataModel()
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.login()

        #kiwoom event
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.receive_trData)

        #Ui_Trigger
        self.searchItemButton.clicked.connect(self.searchItem)
        self.buyPushButton.clicked.connect(self.itemBuy)
        self.sellPushButton.clicked.connect(self.itemSell)
        self.outstandingTableWidget.itemSelectionChanged.connect(self.selectOutstandingOrder)

    def setUI(self):
        # 반드시 pyqt 실행시 필요한 메소드
        self.setupUi(self)

        column_head = ["00 : 지정가","03 : 시장가","05 : 조건부지정가","05 : 조건부지정가",
                        "05 : 조건부지정가", "06 : 최유리지정가", "07 : 최우선지정가",
                        "10 : 지정가IOC", "13 : 시장가IOC", "16 : 최유리IOC",
                        "20 : 지정가FOK", "23 : 시장가FOK", "26 : 최유리FOK",
                        "61 : 장전시간외종가","62 : 시간외단일가매매","81 : 장후시간외종가"]

        self.gubunComboBox.addItems(column_head)

        column_head = [ "매수", "매도", "매수취소", "매도취소",
                        "매수정정", "매도정정" ]

        self.tradeGubunComboBox.addItems(column_head)

    def login(self):
        self.kiwoom.dynamicCall("CommConnect()")

    def event_connect(self, nErrcode):
        if nErrcode == 0 :
            print("로그인 성공")
            self.statusbar.showMessage("로그인성공")
            self.get_login_info()
            self.getItemList()
            self.getMyAccount()
        elif nErrcode == -100:
            print("사용자 정보교환 실패")
        elif nErrcode == -101:
            print("서버접속 실패")
        elif nErrcode == -102:
            print("버전처리 실패")

    def get_login_info(self):
        #로그인 정보 (보유계좌, 사용자ID, 접속서버 구성 1.모의투자, 나머지 : 실거래)
        accCnt = self.kiwoom.dynamicCall("GetLoginInfo(QString)", "ACCOUNT_CNT")
        accList = self.kiwoom.dynamicCall("GetLoginInfo(QString)", "ACCLIST")
        accList = accList.split(";")
        accList.pop()
        userId = self.kiwoom.dynamicCall("GetLoginInfo(QString)", "USER_ID")
        serverGubun = self.kiwoom.dynamicCall("GetLoginInfo(QString)", "GetServerGubun")

        if serverGubun == "1":
            serverGubun = "모의투자"
        else:
            serverGubun = "실서버"

        self.statusbar.showMessage(serverGubun)
        self.accComboBox.addItems(accList)

    def getItemList(self):
        # 종목코드 리스트 생성
        marketList = ["0", "10"]

        for market in marketList:
            codeList = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", market).split(";")
            for code in codeList:
                name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)

                item = dm.DataModel.ItemInfo(code, name)
                self.myModel.itemList.append(item)

        # print(self.myModel.itemList[0].itemName)

    def searchItem(self):
        #조회 버튼 클릭시 호출 함수
        itemName = self.searchItemTextEdit.toPlainText()
        if itemName != "":
            for item in self.myModel.itemList:
                if item.itemName == itemName:
                    self.itemCodeTextEdit.setPlainText(item.itemCode)
                    self.getitemInfo(item.itemCode)

    def getitemInfo(self, code):
        # 종목 정보 TRData
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "주식기본정보요청", "opt10001", 0, "5000")

    def receive_trData(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext, nDataLength, sErrorCode, sMessage, sSplmMsg):
        # Tr 이벤트 함수
        if sTrCode == "opt10001":
            if sRQName == "주식기본정보요청":
                #현재가
                currentPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "현재가")))
                self.priceSpinBox.setValue(currentPrice)
        elif sTrCode == "opw00018":
            if sRQName == "계좌잔고평가내역":
                column_head = ["종목번호", "종목명", "보유수량", "매입가", "현재가", "평가손익", "수익률(%)"]
                colCount = len(column_head)
                rowCount = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
                self.stocklistTableWidget.setColumnCount(colCount)
                self.stocklistTableWidget.setRowCount(rowCount)
                self.stocklistTableWidget.setHorizontalHeaderLabels(column_head)

                totalBuyingPrice = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총매입금액"))
                currentTotalPrice = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                   "총평가금액"))
                balanceAsset = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                   "추정예탁자산"))
                totalEstmateProfit = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                   "총평가손익금액"))

                self.totalBuyingPriceLabel.setText(str(totalBuyingPrice))
                self.currentTotalPriceLabel.setText(str(currentTotalPrice))
                self.balanceAssetLabel.setText(str(balanceAsset))
                self.totalEstimateProfitLabel.setText(str(totalEstmateProfit))

                for index in range(rowCount):
                    itemCode = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "종목번호").strip(" ").strip("A")
                    itemName = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "종목명")
                    amount = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "보유수량"))
                    buyingPrice = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "매입가"))
                    currentPrice = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "현재가"))
                    estmateProfit = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "평가손익"))
                    profitRate = float(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "수익률(%)")) / 100

                    stockBalance = dm.DataModel.StockBalance(itemCode, itemName, amount, buyingPrice, currentPrice, estmateProfit, profitRate)
                    self.myModel.stockBalanceList.append(stockBalance)

                    self.stocklistTableWidget.setItem(index, 0, QTableWidgetItem(str(itemCode)))
                    self.stocklistTableWidget.setItem(index, 1, QTableWidgetItem(str(itemName)))
                    self.stocklistTableWidget.setItem(index, 2, QTableWidgetItem(str(amount)))
                    self.stocklistTableWidget.setItem(index, 3, QTableWidgetItem(str(buyingPrice)))
                    self.stocklistTableWidget.setItem(index, 4, QTableWidgetItem(str(currentPrice)))
                    self.stocklistTableWidget.setItem(index, 5, QTableWidgetItem(str(estmateProfit)))
                    self.stocklistTableWidget.setItem(index, 6, QTableWidgetItem(str(profitRate)))
        elif sTrCode == "opt10075":
            if sRQName == "미체결요청":
                column_head = ["종목번호", "종목명", "주문번호", "주문수량",
		                        "주문가격", "미체결수량", "주문구분", "시간", "현재가"]
                colCount = len(column_head)
                rowCount = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
                self.outstandingTableWidget.setColumnCount(colCount)
                self.outstandingTableWidget.setRowCount(rowCount)
                self.outstandingTableWidget.setHorizontalHeaderLabels(column_head)

                for index in range(rowCount):
                    itemCode = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "종목코드").strip(" ").strip("A")
                    itemName = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "종목명").strip(" ")
                    orderNumber = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "주문번호").strip(" ")
                    orderVolume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "주문수량").strip(" ")
                    orderPrice = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "주문가격").strip(" ")
                    outstandingVolume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "미체결수량").strip(" ")
                    tradeGubun = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "주문구분").strip(" ").strip("+").strip("-")
                    orderTime = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "시간").strip(" ")
                    currentPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index,
                                            "현재가").strip(" ")))

                    outstandingBalance = dm.DataModel.OutstandingBalance(itemCode, itemName, orderNumber, orderVolume, orderPrice, outstandingVolume, tradeGubun, orderTime, currentPrice)
                    self.myModel.outstandingBalanceList.append(outstandingBalance)

                    self.outstandingTableWidget.setItem(index, 0, QTableWidgetItem(str(itemCode)))
                    self.outstandingTableWidget.setItem(index, 1, QTableWidgetItem(str(itemName)))
                    self.outstandingTableWidget.setItem(index, 2, QTableWidgetItem(str(orderNumber)))
                    self.outstandingTableWidget.setItem(index, 3, QTableWidgetItem(str(orderVolume)))
                    self.outstandingTableWidget.setItem(index, 4, QTableWidgetItem(str(orderPrice)))
                    self.outstandingTableWidget.setItem(index, 5, QTableWidgetItem(str(outstandingVolume)))
                    self.outstandingTableWidget.setItem(index, 6, QTableWidgetItem(str(tradeGubun)))
                    self.outstandingTableWidget.setItem(index, 7, QTableWidgetItem(str(orderTime)))
                    self.outstandingTableWidget.setItem(index, 8, QTableWidgetItem(str(currentPrice)))

    def itemBuy(self):
        #매수 함수
        print("매수버튼")
        acc = self.accComboBox.currentText() #계좌정보
        code = self.itemCodeTextEdit.toPlainText() #종목코드
        amount = int(self.volumeSpinBox.value()) #수량
        price = int(self.priceSpinBox.value()) # 가격
        hogaGb = self.gubunComboBox.currentText()[0:2] #호가구분
        if hogaGb == "03":
            price = 0

        self.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", ["주식주문", "6000", acc, 1, code, amount, price, hogaGb, ""])

    def itemSell(self):
        #매도 함수
        print("매수버튼")
        acc = self.accComboBox.currentText()  # 계좌정보
        code = self.itemCodeTextEdit.toPlainText()  # 종목코드
        amount = int(self.volumeSpinBox.value())  # 수량
        price = int(self.priceSpinBox.value())  # 가격
        hogaGb = self.gubunComboBox.currentText()[0:2]  # 호가구분
        if hogaGb == "03":
            price = 0

        self.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                ["주식주문", "6500", acc, 2, code, amount, price, hogaGb, ""])

    def getMyAccount(self):
        #계좌 잔고 호출
        account = self.accComboBox.currentText()
        #Tr - opw00018
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "계좌번호", account)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "조회구분", "2")

        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "계좌잔고평가내역", "opw00018", 0, "5100")

        # Tr - opt10075
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "계좌번호", account)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "체결구분", "1")

        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "미체결요청", "opt10075", 0, "5200")

    def selectOutstandingOrder(self):
        #미체결 선택 함수
        check = 0
        for rowIndex in range(self.outstandingTableWidget.rowCount()):
            for colIndex in range(self.outstandingTableWidget.columnCount()):
                if self.outstandingTableWidget.item(rowIndex, colIndex) != None:
                    if self.outstandingTableWidget.item(rowIndex, colIndex).isSelected() == True:
                        check = 1
                        self.searchItemTextEdit.setText(self.outstandingTableWidget.item(rowIndex, 1).text())
                        self.itemCodeTextEdit.setText(self.outstandingTableWidget.item(rowIndex, 0).text())
                        self.volumeSpinBox.setValue(int(self.outstandingTableWidget.item(rowIndex, 5).text()))
                        self.priceSpinBox.setValue(int(self.outstandingTableWidget.item(rowIndex, 4).text()))
                        self.orderNumberTextEdit.setText(self.outstandingTableWidget.item(rowIndex, 2).text())
                        index = self.tradeGubunComboBox.findText(self.outstandingTableWidget.item(rowIndex, 6).text())
                        self.tradeGubunComboBox.setCurrentIndex(index)

            if check == 1:
                break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    myApp = MyBot()
    myApp.show()
    app.exec()

