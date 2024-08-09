import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from PyQt5.QAxContainer import *

#차트 생성 라이브러리
import matplotlib.pyplot as plt
import mpl_finance as matfin
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FiqureCanvas
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker

import datetime
from datetime import date

import time
from time import strftime




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
        self.kiwoom.OnReceiveChejanData.connect(self.receive_chejanData)
        self.kiwoom.OnReceiveConditionVer.connect(self.receive_condition)
        self.kiwoom.OnReceiveTrCondition.connect(self.receive_trCondition)
        self.kiwoom.OnReceiveRealCondition.connect(self.receive_realCondition)

        #Ui_Trigger
        self.searchItemButton.clicked.connect(self.searchItem)
        self.buyPushButton.clicked.connect(self.itemBuy)
        self.sellPushButton.clicked.connect(self.itemSell)
        self.outstandingTableWidget.itemSelectionChanged.connect(self.selectOutstandingOrder)
        self.stocklistTableWidget.itemSelectionChanged.connect(self.selectStockListOrder)
        self.changePushButton.clicked.connect(self.itemCorrect)
        self.cancelPushButton.clicked.connect(self.itemCancel)
        self.charPushButton.clicked.connect(self.chartShow)
        self.addAutoTradePushButton.clicked.connect(self.addAutoTradeCondition)
        self.removeAutoTradePushButton.clicked.connect(self.removeAutoTradeCondition)
        self.conditionSearchPushButton.clicked.connect(self.conditionSearch)
        self.autoTradePushButton.clicked.connect(self.autoTrade)

        #조건검색 시작 유무 변수
        self.boolCondition = 0
        #자동매매 시작 유무 변수
        self.boolAutoTrade = 0
        self.screenNumber = 9000


    def setUI(self):
        # 반드시 pyqt 실행시 필요한 메소드
        self.setupUi(self)

        column_head = ["00 : 지정가","03 : 시장가","05 : 조건부지정가","05 : 조건부지정가",
                        "05 : 조건부지정가", "06 : 최유리지정가", "07 : 최우선지정가",
                        "10 : 지정가IOC", "13 : 시장가IOC", "16 : 최유리IOC",
                        "20 : 지정가FOK", "23 : 시장가FOK", "26 : 최유리FOK",
                        "61 : 장전시간외종가","62 : 시간외단일가매매","81 : 장후시간외종가"]

        self.gubunComboBox.addItems(column_head)

        self.realGubunComboBox.addItems(column_head)

        column_head = ["매수", "매도", "매수/매도"]
        self.autoTradeGubunComboBox.addItems(column_head)

        column_head = [ "매수", "매도", "매수취소", "매도취소",
                        "매수정정", "매도정정" ]

        self.tradeGubunComboBox.addItems(column_head)

        #차트생성
        self.fig = plt.figure(figsize = (8,5))
        self.canvas = FiqureCanvas(self.fig)
        self.chartLayout.addWidget(self.canvas)

    def login(self):
        self.kiwoom.dynamicCall("CommConnect()")

    def event_connect(self, nErrcode):
        if nErrcode == 0 :
            print("로그인 성공")
            self.statusbar.showMessage("로그인성공")
            self.get_login_info()
            self.getItemList()
            self.getMyAccount()
            self.getCoditionList()
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

    def getCoditionList(self):
        if self.kiwoom.dynamicCall("GetConditionLoad()") == 1:
            print("조건식 목록 호출 성공")
        else:
            print("조건식 목록 호출 실패")
            return

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
                    self.drawDayChart(item.itemCode)

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
            else :
                # 조건식에 따라 편입된 종목 매수/매도
                itemCode = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드").strip(" ")
                itemName = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목명").strip(" ")
                currentPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,"현재가").strip(" ")))
                fluctuationRate = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode,sRQName, 0, "등락율").strip(" ")
                priceDiffYes = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,0, "전일대비").strip(" ")
                volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,"거래량").strip(" ")
                openPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,"시가").strip(" ")))
                highPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,"고가").strip(" ")))
                lowPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,"저가").strip(" ")))

                check = 0

                for item in self.myModel.stockBalanceList:
                    if item.itemCode.strip(" ") ==  itemCode:
                        check = 1
                        if sRQName.strip(" ") == "프로그램추가매수식":
                            pass #추가매수 진행
                            #if self.boolAutoTrade == 1:
                            #매입가의 4프로 이하일경우 매수 실시
                            #수량, 가격, 구분 매수 실행할수 있다.
                            #수량 : 가격 / 현재가 예시) 10000 / 1000 10개

                        elif sRQName.strip(" ") == "프로그램전량매도식":
                            pass #매도진행
                            #if self.boolAutoTrade == 1:

                if check == 0 :
                    # 신규매수
                    num = 0
                    for codition in self.myModel.conditionItemList:
                        for item in self.myModel.conditionItemList[codition]:
                            if item.itemCode.strip(" ") == itemCode:
                                num = 1
                                print("조건식 종목이 있습니다.-", itemCode)
                                break
                        if num == 1 :
                            break

                    if num == 0 :
                        conditionItem = dm.DataModel.CondtionItemInfo(itemCode, itemName, currentPrice, fluctuationRate, priceDiffYes, volume, openPrice, highPrice, lowPrice, sRQName)
                        self.myModel.conditionItemList[sRQName].append(conditionItem)

                        #조건식 종목 테이블 업데이트 작업
                        self.conditionTableModify(itemCode)

                        if self.boolAutoTrade == 1:
                            #신규매수
                            acc = self.accComboBox.currentText()
                            amount = self.enabledMoneyTextEdit.toPlainText() / currentPrice
                            price = currentPrice
                            hogaGb = self.realGubunComboBox.currentText()[0:2]
                            if hogaGb == "03" :
                                price = 0

                            self.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", ["주식주문", "6000", acc, 1, itemCode, amount, price, hogaGb, ""])














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
        elif sTrCode == "opt10081":
            if sRQName == "주식일봉차트조회요청":
                rowCount = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

                dateList = []
                openPrice = []
                closePrice = []
                highPrice = []
                lowPrice = []
                volume = []

                if self.candlenumberTextEdit.toPlainText() != None and self.candlenumberTextEdit.toPlainText() != "":
                    candlenumber = int(self.candlenumberTextEdit.toPlainText())
                else :
                    candlenumber = 60

                if candlenumber > rowCount :
                    candlenumber = rowCount

                for index in range(candlenumber):
                    m_date = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "일자").strip(" ")
                    m_newDate = datetime.datetime(int(m_date[0:4]), int(m_date[4:6]), int(m_date[6:8]))
                    m_openPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "시가").strip(" ")))
                    m_closePrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "현재가").strip(" ")))
                    m_highPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "고가").strip(" ")))
                    m_lowPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "저가").strip(" ")))
                    m_volume = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "거래량").strip(" "))

                    dateList.insert(0, m_newDate)
                    openPrice.insert(0, m_openPrice)
                    closePrice.insert(0, m_closePrice)
                    highPrice.insert(0, m_highPrice)
                    lowPrice.insert(0, m_lowPrice)
                    volume.insert(0, m_volume)

                dayList = []
                nameList = []

                for i, day in enumerate(dateList):
                    if day.weekday() == 0:
                        dayList.append(i)
                        nameList.append(str(day.strftime("%Y-%m-%d")))

                gs = gridspec.GridSpec(2, 1 , height_ratios=[3,1])
                axes = []
                axes.append(plt.subplot(gs[0]))
                axes.append(plt.subplot(gs[1], sharex=axes[0]))
                axes[0].get_xaxis().set_visible(False)

                axes[1].set_xticks(dayList)
                axes[1].set_xticklabels(nameList, rotation=45)

                matfin.candlestick2_ochl(axes[0], openPrice, closePrice, highPrice, lowPrice, width=0.5, colorup='r', colordown='b')
                axes[1].bar(range(len(dateList)), volume, color='k', width=0.6, align='center')
                plt.tight_layout()

                self.canvas.draw()
        elif sTrCode == "OPTKWFID":
            if sScrNo == "8000":
                if self.conditionItemTableWidget.rowCount() == None or self.conditionItemTableWidget.rowCount() == 0 :
                    # 데이터가 없을경우
                    column_head = ["종목번호", "종목명", "현재가", "등락률",
                               "전일대비", "거래량", "시가", "고가", "저가", "조건식명"]

                    colCount = len(column_head)
                    rowCount = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

                    self.conditionItemTableWidget.setColumnCount(colCount)
                    self.conditionItemTableWidget.setRowCount(rowCount)
                    self.conditionItemTableWidget.setHorizontalHeaderLabels(column_head)

                    for index in range(rowCount):
                        itemCode = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "종목코드").strip(" ")
                        itemName = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "종목명").strip(" ")
                        currentPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "현재가").strip(" ")))
                        fluctuationRate = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "등락율").strip(" ")
                        priceDiffYes = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "전일대비").strip(" ")
                        volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "거래량").strip(" ")
                        openPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "시가").strip(" ")))
                        highPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "고가").strip(" ")))
                        lowPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "저가").strip(" ")))

                        conditionItem = dm.DataModel.CondtionItemInfo(itemCode, itemName, currentPrice, fluctuationRate, priceDiffYes, volume, openPrice, highPrice, lowPrice, sRQName)
                        self.myModel.conditionItemList[sRQName].append(conditionItem)

                        self.conditionItemTableWidget.setItem(index, 0, QTableWidgetItem(str(itemCode)))
                        self.conditionItemTableWidget.setItem(index, 1, QTableWidgetItem(str(itemName)))
                        self.conditionItemTableWidget.setItem(index, 2, QTableWidgetItem(str(currentPrice)))
                        self.conditionItemTableWidget.setItem(index, 3, QTableWidgetItem(str(fluctuationRate)))
                        self.conditionItemTableWidget.setItem(index, 4, QTableWidgetItem(str(priceDiffYes)))
                        self.conditionItemTableWidget.setItem(index, 5, QTableWidgetItem(str(volume)))
                        self.conditionItemTableWidget.setItem(index, 6, QTableWidgetItem(str(openPrice)))
                        self.conditionItemTableWidget.setItem(index, 7, QTableWidgetItem(str(highPrice)))
                        self.conditionItemTableWidget.setItem(index, 8, QTableWidgetItem(str(lowPrice)))
                        self.conditionItemTableWidget.setItem(index, 9, QTableWidgetItem(str(sRQName)))
                else:
                    rowCount = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
                    rowIndex = self.conditionItemTableWidget.rowCount()
                    self.conditionItemTableWidget.setRowCount(rowIndex + rowCount)

                    for index in range(rowCount):
                        itemCode = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "종목코드").strip(" ")
                        itemName = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "종목명").strip(" ")
                        currentPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,index, "현재가").strip(" ")))
                        fluctuationRate = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)",sTrCode, sRQName, index, "등락율").strip(" ")
                        priceDiffYes = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "전일대비").strip(" ")
                        volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "거래량").strip(" ")
                        openPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "시가").strip(" ")))
                        highPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, index, "고가").strip(" ")))
                        lowPrice = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,index, "종가").strip(" ")))

                        conditionItem = dm.DataModel.CondtionItemInfo(itemCode, itemName, currentPrice, fluctuationRate, priceDiffYes, volume, openPrice, highPrice, lowPrice, sRQName)
                        self.myModel.conditionItemList[sRQName].append(conditionItem)

                        newIndex = rowIndex + index
                        self.conditionItemTableWidget.setItem(newIndex, 0, QTableWidgetItem(str(itemCode)))
                        self.conditionItemTableWidget.setItem(newIndex, 1, QTableWidgetItem(str(itemName)))
                        self.conditionItemTableWidget.setItem(newIndex, 2, QTableWidgetItem(str(currentPrice)))
                        self.conditionItemTableWidget.setItem(newIndex, 3, QTableWidgetItem(str(fluctuationRate)))
                        self.conditionItemTableWidget.setItem(newIndex, 4, QTableWidgetItem(str(priceDiffYes)))
                        self.conditionItemTableWidget.setItem(newIndex, 5, QTableWidgetItem(str(volume)))
                        self.conditionItemTableWidget.setItem(newIndex, 6, QTableWidgetItem(str(openPrice)))
                        self.conditionItemTableWidget.setItem(newIndex, 7, QTableWidgetItem(str(highPrice)))
                        self.conditionItemTableWidget.setItem(newIndex, 8, QTableWidgetItem(str(lowPrice)))
                        self.conditionItemTableWidget.setItem(newIndex, 9, QTableWidgetItem(str(sRQName)))

    def receive_chejanData(self, sGubun, nItemCnt, sFIdList):
        if sGubun == "0" : # 접수 & 체결
            conClusionVolume = self.kiwoom.dynamicCall("GetChejanData(int)", 911)
            if len(conClusionVolume) > 0 : #체결이 있을경우
                itemCode = self.kiwoom.dynamicCall("GetChejanData(int)", 9001).strip(" ").strip("A")
                itemName = self.kiwoom.dynamicCall("GetChejanData(int)", 302).strip(" ")
                orderNumber = self.kiwoom.dynamicCall("GetChejanData(int)", 9203).strip(" ")
                orderPrice = self.kiwoom.dynamicCall("GetChejanData(int)", 901).strip(" ")
                orderVolume = self.kiwoom.dynamicCall("GetChejanData(int)", 900).strip(" ")
                outStandingVolume = int(self.kiwoom.dynamicCall("GetChejanData(int)", 902).strip(" "))
                tradeGubun = self.kiwoom.dynamicCall("GetChejanData(int)", 905).strip(" ").strip("+").strip("-")
                orderTime = self.kiwoom.dynamicCall("GetChejanData(int)", 908).strip(" ")
                currentPrice = self.kiwoom.dynamicCall("GetChejanData(int)", 10).strip(" ")

                for itemIndex in range(len(self.myModel.outstandingBalanceList)):
                    if self.myModel.outstandingBalanceList[itemIndex].orderNumber == orderNumber :
                        if outStandingVolume > 0 : #미체결량이 있을경우
                            for rowIndex in range(self.outstandingTableWidget.rowCount()):
                                if self.outstandingTableWidget.item(rowIndex, 2).text() == orderNumber:
                                    # 데이터 update
                                    self.myModel.outstandingBalanceList[itemIndex].outstandingVolume = outStandingVolume
                                    self.myModel.outstandingBalanceList[itemIndex].currentPrice = currentPrice

                                    # 테이블 update
                                    self.outStandingTableWidget.setItem(rowIndex, 0, QTableWidgetItem(str(itemCode)))
                                    self.outStandingTableWidget.setItem(rowIndex, 1, QTableWidgetItem(str(itemName)))
                                    self.outStandingTableWidget.setItem(rowIndex, 2, QTableWidgetItem(str(orderNumber)))
                                    self.outStandingTableWidget.setItem(rowIndex, 3, QTableWidgetItem(str(orderVolume)))
                                    self.outStandingTableWidget.setItem(rowIndex, 4, QTableWidgetItem(str(orderPrice)))
                                    self.outStandingTableWidget.setItem(rowIndex, 5, QTableWidgetItem(str(outStandingVolume)))
                                    self.outStandingTableWidget.setItem(rowIndex, 6, QTableWidgetItem(str(tradeGubun)))
                                    self.outStandingTableWidget.setItem(rowIndex, 7, QTableWidgetItem(str(orderTime)))
                                    self.outStandingTableWidget.setItem(rowIndex, 8, QTableWidgetItem(str(currentPrice)))
                                    break

                        else : # 전량 체결된 경우
                            #데이터 삭제
                            for itemIndex in range(len(self.myModel.outstandingBalanceList)):
                                if self.myModel.outstandingBalanceList[itemIndex].orderNumber == orderNumber :
                                    del self.myModel.outstandingBalanceList[itemIndex]
                                    break

                            for rowIndex in range(self.outstandingTableWidget.rowCount()):
                                if self.outstandingTableWidget.item(rowIndex, 2).text() == orderNumber:
                                    self.outstandingTableWidget.removeRow(rowIndex)
                                    break
            else: #접수
                itemCode = self.kiwoom.dynamicCall("GetChejanData(int)", 9001).strip(" ").strip("A")
                itemName = self.kiwoom.dynamicCall("GetChejanData(int)", 302).strip(" ")
                orderNumber = self.kiwoom.dynamicCall("GetChejanData(int)", 9203).strip(" ")
                orderPrice = self.kiwoom.dynamicCall("GetChejanData(int)", 901).strip(" ")
                orderVolume = self.kiwoom.dynamicCall("GetChejanData(int)", 900).strip(" ")
                outStandingVolume = self.kiwoom.dynamicCall("GetChejanData(int)", 902).strip(" ")
                tradeGubun = self.kiwoom.dynamicCall("GetChejanData(int)", 905).strip(" ").strip("+").strip("-")
                orderTime = self.kiwoom.dynamicCall("GetChejanData(int)", 908).strip(" ")
                currentPrice = abs(int(self.kiwoom.dynamicCall("GetChejanData(int)", 10).strip(" ")))

                for rowIndex in range(self.outstandingTableWidget.rowCount()):
                    if self.outstandingTableWidget.item(rowIndex, 2).text() == orderNumber \
                        and self.outstandingTableWidget.item(rowIndex, 3).text() == orderVolume \
                        and self.outstandingTableWidget.item(rowIndex, 4).text() == orderPrice :
                        if self.outstandingTableWidget.item(rowIndex, 5).text() == outStandingVolume :
                            # 정정 확인 주문
                            return
                        else:
                            # 원주문 삭제
                            self.outstandingTableWidget.removeRow(rowIndex)
                            for itemIndex in range(len(self.myModel.outstandingBalanceList)):
                                if self.myModel.outstandingBalanceList[itemIndex].orderNumber == orderNumber \
                                    and self.myModel.outstandingBalanceList[itemIndex].orderVolume == orderVolume \
                                    and self.myModel.outstandingBalanceList[itemIndex].orderPrice == orderPrice  \
                                    and self.myModel.outstandingBalanceList[itemIndex].outstandingVolume != outStandingVolume:
                                    del self.myModel.outstandingBalanceList[itemIndex]
                                    break
                            break

                #취소시 주문 삭제
                if outStandingVolume == "0" :
                    for itemIndex in range(len(self.myModel.outstandingBalanceList)):
                        if self.myModel.outstandingBalanceList[itemIndex].orderNumber == orderNumber :
                            del self.myModel.outstandingBalanceList[itemIndex]
                            break

                    for rowIndex in range(self.outstandingTableWidget.rowCount()):
                        if self.outstandingTableWidget.item(rowIndex, 2).text() == orderNumber :
                            self.outstandingTableWidget.removeRow(rowIndex)
                            break
                    return

                #데이터 추가
                outStandingOrder = dm.DataModel.OutstandingBalance(itemCode, itemName, orderNumber, orderVolume, orderPrice, outStandingVolume,tradeGubun, orderTime, currentPrice)
                self.myModel.outstandingBalanceList.append(outStandingOrder)

                #테이블 추가
                self.outstandingTableWidget.setRowCount(self.outstandingTableWidget.rowCount() + 1)
                index = self.outstandingTableWidget.rowCount() - 1

                self.outstandingTableWidget.setItem(index, 0, QTableWidgetItem(str(itemCode)))
                self.outstandingTableWidget.setItem(index, 1, QTableWidgetItem(str(itemName)))
                self.outstandingTableWidget.setItem(index, 2, QTableWidgetItem(str(orderNumber)))
                self.outstandingTableWidget.setItem(index, 3, QTableWidgetItem(str(orderVolume)))
                self.outstandingTableWidget.setItem(index, 4, QTableWidgetItem(str(orderPrice)))
                self.outstandingTableWidget.setItem(index, 5, QTableWidgetItem(str(outStandingVolume)))
                self.outstandingTableWidget.setItem(index, 6, QTableWidgetItem(str(tradeGubun)))
                self.outstandingTableWidget.setItem(index, 7, QTableWidgetItem(str(orderTime)))
                self.outstandingTableWidget.setItem(index, 8, QTableWidgetItem(str(currentPrice)))

        # 잔고데이터
        if sGubun == "1":
            itemCode = self.kiwoom.dynamicCall("GetChejanData(int)", 9001).strip(" ").strip("A")
            itemName = self.kiwoom.dynamicCall("GetChejanData(int)", 302).strip(" ")
            amount = self.kiwoom.dynamicCall("GetChejanData(int)", 930).strip(" ")
            buyingPrice = self.kiwoom.dynamicCall("GetChejanData(int)", 931).strip(" ")
            currentPrice = abs(int(self.kiwoom.dynamicCall("GetChejanData(int)", 10)))
            estimateProfit = (currentPrice - int(buyingPrice)) * int(amount)

            if buyingPrice != "0":
                profitRate = estimateProfit / (int(buyingPrice)*amount) * 100
            else :
                profitRate = 0

            check = 0
            for item in self.myModel.stockBalanceList:
                if item.itemName.strip(" ") == itemName.strip(" ") :
                    check = 1
                    if amount == "0":
                        for rowIndex in range(self.stocklistTableWidget.rowCount()):
                            if self.stocklistTableWidget.item(rowIndex, 0).text() == itemCode:
                                self.stocklistTableWidget.removeRow(rowIndex)
                                break
                        self.myModel.stockBalanceList.remove(item)
                        break

                    #데이터 Update
                    item.amount = amount
                    item.buyingPrice = buyingPrice
                    item.currentPrice = currentPrice
                    item.estimateProfit = estimateProfit
                    item.profitRate = profitRate

                    #테이블 Update
                    for rowIndex in range(self.myModel.stockBalanceList):
                        if self.stocklistTableWidget.item(rowIndex, 0).text().strip(" ") == itemCode:
                            self.stocklistTableWidget.setItem(rowIndex, 0, QTableWidgetItem(str(itemCode)))
                            self.stocklistTableWidget.setItem(rowIndex, 1, QTableWidgetItem(str(itemName)))
                            self.stocklistTableWidget.setItem(rowIndex, 2, QTableWidgetItem(str(amount)))
                            self.stocklistTableWidget.setItem(rowIndex, 3, QTableWidgetItem(str(buyingPrice)))
                            self.stocklistTableWidget.setItem(rowIndex, 4, QTableWidgetItem(str(currentPrice)))
                            self.stocklistTableWidget.setItem(rowIndex, 5, QTableWidgetItem(str(estimateProfit)))
                            self.stocklistTableWidget.setItem(rowIndex, 6, QTableWidgetItem(str(profitRate)))
                            break

            if check == 0 :
                if amount == "0":
                    for rowIndex in range(self.stocklistTableWidget.rowCount()):
                        if self.stocklistTableWidget.item(rowIndex, 0).text().strip(" ") == itemCode:
                            self.stocklistTableWidget.removeRow(rowIndex)
                            break

                    for item in self.myModel.stockBalanceList:
                        if item.itemCode.strip(" ") == itemName.strip(" ") :
                            self.myModel.stockBalanceList.remove(item)
                            break
                    return

                stockBalance = dm.DataModel.StockBalance(itemCode, itemName, amount, buyingPrice, currentPrice, estimateProfit, profitRate)
                self.myModel.stockBalanceList.append(stockBalance)

                self.stocklistTableWidget.setRowCount(self.stocklistTableWidget.rowCount() + 1)
                index = self.stocklistTableWidget.rowCount() - 1

                self.stocklistTableWidget.setItem(index, 0, QTableWidgetItem(str(itemCode)))
                self.stocklistTableWidget.setItem(index, 1, QTableWidgetItem(str(itemName)))
                self.stocklistTableWidget.setItem(index, 2, QTableWidgetItem(str(amount)))
                self.stocklistTableWidget.setItem(index, 3, QTableWidgetItem(str(buyingPrice)))
                self.stocklistTableWidget.setItem(index, 4, QTableWidgetItem(str(currentPrice)))
                self.stocklistTableWidget.setItem(index, 5, QTableWidgetItem(str(estimateProfit)))
                self.stocklistTableWidget.setItem(index, 6, QTableWidgetItem(str(profitRate)))

    def receive_condition(self, lRet, sMsg):
        #조건목록 검색 이벤트 함수
        if lRet == 1: #호출 성공
            conditionListTotal = self.kiwoom.dynamicCall("GetConditionNameList()").split(";")
            conditionListTotal.pop()
            conditionList = {}
            conditionList["code"]=[]
            conditionList["name"]=[]

            for condition in conditionListTotal:
                temp = condition.split("^")
                conditionList["code"].append(temp[0])
                conditionList["name"].append(temp[1])

            column_head = ["조건코드", "조건명"]
            colCount = len(column_head)
            rowCount = len(conditionListTotal)

            self.conditionTableWidget.setColumnCount(colCount)
            self.conditionTableWidget.setRowCount(rowCount)
            self.conditionTableWidget.setHorizontalHeaderLabels(column_head)

            for index in range(rowCount):
                self.conditionTableWidget.setItem(index, 0, QTableWidgetItem(str(conditionList["code"][index])))
                self.conditionTableWidget.setItem(index, 1, QTableWidgetItem(str(conditionList["name"][index])))

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
                        self.drawDayChart(self.outstandingTableWidget.item(rowIndex, 0).text())
            if check == 1:
                break

    def selectStockListOrder(self):
        check = 0
        for rowIndex in range(self.stocklistTableWidget.rowCount()):
            for colIndex in range(self.stocklistTableWidget.columnCount()):
                if self.stocklistTableWidget.item(rowIndex, colIndex) != None :
                    if self.stocklistTableWidget.item(rowIndex, colIndex).isSelected() == True:
                        check = 1
                        self.searchItemTextEdit.setText(self.stocklistTableWidget.item(rowIndex, 1).text())
                        self.itemCodeTextEdit.setText(self.stocklistTableWidget.item(rowIndex, 0).text())
                        self.volumeSpinBox.setValue(int(self.stocklistTableWidget.item(rowIndex, 2).text()))
                        self.priceSpinBox.setValue(int(self.stocklistTableWidget.item(rowIndex, 3).text()))
                        self.drawDayChart(self.stocklistTableWidget.item(rowIndex, 0).text())
                        break
            if check == 1:
                break

    def itemCorrect(self):
        # 정정
        acc = self.accComboBox.currentText().strip(" ")
        code = self.itemCodeTextEdit.toPlainText().strip(" ")
        amount = int(self.volumeSpinBox.value())
        price = int(self.priceSpinBox.value())
        hogaGb = self.gubunComboBox.currentText()[0:2]
        orderType = self.tradeGubunComboBox.currentText().strip(" ")
        if orderType == "매수" or orderType == "매수정정":
            orderType = 5
        elif orderType == "매도" or orderType == "매도정정":
            orderType = 6
        #원주문번호
        orderNumber = self.orderNumberTextEdit.toPlainText().strip(" ")

        self.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                ["주식주문", "6700", acc, orderType, code, amount, price, hogaGb, orderNumber])
        print("정정 주문 확인")

    def itemCancel(self):
        acc = self.accComboBox.currentText().strip(" ")
        code = self.itemCodeTextEdit.toPlainText().strip(" ")
        amount = int(self.volumeSpinBox.value())
        price = int(self.priceSpinBox.value())
        hogaGb = self.gubunComboBox.currentText()[0:2]
        orderType = self.tradeGubunComboBox.currentText().strip(" ")
        if orderType == "매수취소" or orderType == "매수":
            orderType = 3
        elif orderType == "매도취소" or orderType == "매도":
            orderType = 4
        # 원주문번호
        orderNumber = self.orderNumberTextEdit.toPlainText().strip(" ")

        self.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                ["주식주문", "6800", acc, orderType, code, amount, price, hogaGb, orderNumber])


    def drawDayChart(self, itemCode):

        #차트 그리기
        now = datetime.datetime.now()
        nowDate = now.strftime("%Y%m%d") #YYYYMMDD
        # opt10081 데이터 요청
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", itemCode)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "기준일자", nowDate)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")

        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회요청", "opt10081", 0, "5300")

    def chartShow(self):
        #차트 조회 함수
        if self.itemCodeTextEdit.toPlainText() != None and self.itemCodeTextEdit.toPlainText() != "":
            code = self.itemCodeTextEdit.toPlainText().strip(" ")
            self.drawDayChart(code)


    def addAutoTradeCondition(self):
        #조건식 추가 함수
        check = 0
        for rowIndex in range(self.conditionTableWidget.rowCount()):
            for colIndex in range(self.conditionTableWidget.columnCount()):
                if self.conditionTableWidget.item(rowIndex, colIndex).isSelected() == True:
                    check = 1
                    code = self.conditionTableWidget.item(rowIndex, 0).text()
                    name = self.conditionTableWidget.item(rowIndex, 1).text()
                    break

            if check == 1:
                break

        autoTradeCondition = dm.DataModel.AutoTradeCoditionInfo(self.startTimeEdit.time(), self.endTimeEdit.time(), code, name, self.autoTradeGubunComboBox.currentText())
        self.myModel.autoTradeCoditionList.append(autoTradeCondition)

        self.updateAutoTradeeCodtionTable()

    def removeAutoTradeCondition(self):
        #조건식 제거 함수
        print("remove Auto trade condition")
        check = 0
        for rowIndex in range(self.autoTradeconditionTableWidget.rowCount()):
            for colIndex in range(self.autoTradeconditionTableWidget.columnCount()):
                if self.autoTradeconditionTableWidget.item(rowIndex, colIndex).isSelected() == True:
                    check = 1
                    del self.myModel.autoTradeCoditionList[rowIndex]
                    break
            if check == 1 :
                break

        self.updateAutoTradeeCodtionTable()

    def updateAutoTradeeCodtionTable(self):
        column_head = ["시작시간", "종료시간", "조건식번호", "조건식이름", "자동매매상태"]

        colCount = len(column_head)
        rowcount = len(self.myModel.autoTradeCoditionList)

        self.autoTradeconditionTableWidget.setColumnCount(colCount)
        self.autoTradeconditionTableWidget.setRowCount(rowcount)

        self.autoTradeconditionTableWidget.setHorizontalHeaderLabels(column_head)

        for index in range(rowcount):
            self.autoTradeconditionTableWidget.setItem(index, 0, QTableWidgetItem(str(self.myModel.autoTradeCoditionList[index].startTime.toString())))
            self.autoTradeconditionTableWidget.setItem(index, 1, QTableWidgetItem(str(self.myModel.autoTradeCoditionList[index].endTime.toString())))
            self.autoTradeconditionTableWidget.setItem(index, 2, QTableWidgetItem(str(self.myModel.autoTradeCoditionList[index].code)))
            self.autoTradeconditionTableWidget.setItem(index, 3, QTableWidgetItem(str(self.myModel.autoTradeCoditionList[index].name)))
            self.autoTradeconditionTableWidget.setItem(index, 4, QTableWidgetItem(str(self.myModel.autoTradeCoditionList[index].autoTradeGubun)))


    def conditionSearch(self):
        # 조건 검색 버튼 클릭시
        if self.boolCondition == 0 :
        # 처음 버튼 확인후 라벨 변경 (시작 -> 종료)
            self.conditionSearchPushButton.setText("조건검색종료")
            self.boolCondition = 1
        else :
        # 시작 상태 체크 후 (종료 -> 시작)
            self.conditionSearchPushButton.setText("조건검색시작")
            self.boolCondition = 0

        for rowIndex in range(self.autoTradeconditionTableWidget.rowCount()):
            code = self.autoTradeconditionTableWidget.item(rowIndex, 2).text().strip("")
            name = self.autoTradeconditionTableWidget.item(rowIndex, 3).text().strip("")

            # 조건 검색 시작시
            if self.boolCondition == 1:
                # 화면번호 기준으로 종목 (7000 + rowIndex * 100)
                sCrNo = 7000 + rowIndex * 100
                # lRet = SendCondition 함수 호출 -> OnReceiveTrCondition이벤트 발생 -> CommKwRqData() 함수를 통해관심종목데이터(OPTKWFID)tr 목록
                ret = self.kiwoom.dynamicCall("SendCondition(QString, QString, int, int)", str(sCrNo), name, code, 1)

                if ret == 1 :
                    print("조건검색정보요청 성공 -", name)
                    # mymodel condtion list add
                    self.myModel.conditionItemList[name]=[]
                else :
                    print("조건검색정보요청 실패 -", name)
            elif self.boolCondition == 0 :
                # 화면번호 기준으로 종목 (7000 + rowIndex * 100)
                sCrNo = 7000 + rowIndex * 100
                # SendConditionStop 함수 호출
                self.kiwoom.dynamicCall("SendConditionStop(QString, QString, int)", str(sCrNo), name, code)
                print("조건검색종료-", name)

            time.sleep(0.5)

    def receive_trCondition(self, sScrNo, strCodeList, strConditionName, nIndex, nNext):
        # 조건검색식 이벤트 함수
        condtionName = strConditionName
        codeList = strCodeList.split(";")
        codeList.pop()

        # CommKwRqData()호출 작업
        self.kiwoom.dynamicCall("CommKwRqData(QString, bool, int, int, QString, QString)", strCodeList, nNext, len(codeList), 0, condtionName, "8000")

    def receive_realCondition(self, strCode, strType, strConditionName, strConditionIndex):
        if strType == "I":
            # 종목 편입
            print("종목 편입 - ", strConditionName)
            self.screenNumber = self.screenNumber + 1

            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", strCode)
            self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", strConditionName, "opt10001", 0, self.screenNumber)

        elif strType == "D":
            # 종목 이탈
            print("종목 이탈 - ", strConditionName)

    def conditionTableModify(self, code):
        # 조건식 종목 테이블 업데이트 작업
        # 1. 조건식 테이블에 데이터가 없는 경우
        # - head 생성 하고 테이블 작성
        if self.conditionItemTableWidget.rowCount() == 0 or self.conditionItemTableWidget.rowCount() == None:
            column_head = ["종목번호", "종목명", "현재가", "등락률", "전일대비", "거래량", "시가", "고가", "저가", "조건식명"]
            colCount = len(column_head)

            self.conditionItemTableWidget.setColumnCount(colCount)
            self.conditionItemTableWidget.setRowCount(1)
            self.conditionItemTableWidget.setHorizontalHeaderLabels(column_head)
            index = self.conditionItemTableWidget.rowCount() - 1

            check = 0
            for condition in self.myModel.conditionItemList:
                for item in self.myModel.conditionItemList[condition]:
                    if item.itemCode.strip(" ") == code.strip(" "):
                        check = 1
                        self.conditionItemTableWidget.setItem(index, 0, QTableWidgetItem(str(item.itemCode)))
                        self.conditionItemTableWidget.setItem(index, 1, QTableWidgetItem(str(item.itemName)))
                        self.conditionItemTableWidget.setItem(index, 2, QTableWidgetItem(str(item.currentPrice)))
                        self.conditionItemTableWidget.setItem(index, 3, QTableWidgetItem(str(item.fluctuationRate)))
                        self.conditionItemTableWidget.setItem(index, 4, QTableWidgetItem(str(item.priceDiffYes)))
                        self.conditionItemTableWidget.setItem(index, 5, QTableWidgetItem(str(item.volume)))
                        self.conditionItemTableWidget.setItem(index, 6, QTableWidgetItem(str(item.openPrice)))
                        self.conditionItemTableWidget.setItem(index, 7, QTableWidgetItem(str(item.highPrice)))
                        self.conditionItemTableWidget.setItem(index, 8, QTableWidgetItem(str(item.lowPrice)))
                        self.conditionItemTableWidget.setItem(index, 9, QTableWidgetItem(str(item.sRQName)))
                        break
                if check == 1 :
                    break
        else:
        # 2. 조건식 테이블에 데이터가 있는 경우
        # - 기존 종목 데이터가 있는 경우 현재 데이터로 Update
            check = 0
            for itemIndex in range(self.conditionItemTableWidget.rowCount()):
                if self.conditionItemTableWidget.item(itemIndex, 0).text().strip(" ") == code.strip(" "):
                    check = 1
                    check2 = 0
                    for condition in self.myModel.conditionItemList:
                        for item in self.myModel.conditionItemList[condition]:
                            if item.itemCode.strip("") == code.strip(""):
                                check2 = 1
                                self.conditionItemTableWidget.setItem(itemIndex, 0, QTableWidgetItem(str(item.itemCode)))
                                self.conditionItemTableWidget.setItem(itemIndex, 1, QTableWidgetItem(str(item.itemName)))
                                self.conditionItemTableWidget.setItem(itemIndex, 2, QTableWidgetItem(str(item.currentPrice)))
                                self.conditionItemTableWidget.setItem(itemIndex, 3, QTableWidgetItem(str(item.fluctuationRate)))
                                self.conditionItemTableWidget.setItem(itemIndex, 4, QTableWidgetItem(str(item.priceDiffYes)))
                                self.conditionItemTableWidget.setItem(itemIndex, 5, QTableWidgetItem(str(item.volume)))
                                self.conditionItemTableWidget.setItem(itemIndex, 6, QTableWidgetItem(str(item.openPrice)))
                                self.conditionItemTableWidget.setItem(itemIndex, 7, QTableWidgetItem(str(item.highPrice)))
                                self.conditionItemTableWidget.setItem(itemIndex, 8, QTableWidgetItem(str(item.lowPrice)))
                                self.conditionItemTableWidget.setItem(itemIndex, 9, QTableWidgetItem(str(item.sRQName)))
                                break
                        if check2 == 1 :
                            break
                    break
        # - 기존 종목 데이터가 없는 경우 추가 add
            if check == 0 :
                self.conditionItemTableWidget.setRowCount(self.conditionItemTableWidget.rowCount() + 1)
                index = self.conditionItemTableWidget.rowCount() - 1
                check3 = 0
                for condition in self.myModel.conditionItemList:
                    for item in self.myModel.conditionItemList[condition]:
                        if item.itemCode.strip("") == code.strip(""):
                            check3 = 1
                            self.conditionItemTableWidget.setItem(index, 0, QTableWidgetItem(str(item.itemCode)))
                            self.conditionItemTableWidget.setItem(index, 1, QTableWidgetItem(str(item.itemName)))
                            self.conditionItemTableWidget.setItem(index, 2, QTableWidgetItem(str(item.currentPrice)))
                            self.conditionItemTableWidget.setItem(index, 3, QTableWidgetItem(str(item.fluctuationRate)))
                            self.conditionItemTableWidget.setItem(index, 4, QTableWidgetItem(str(item.priceDiffYes)))
                            self.conditionItemTableWidget.setItem(index, 5, QTableWidgetItem(str(item.volume)))
                            self.conditionItemTableWidget.setItem(index, 6, QTableWidgetItem(str(item.openPrice)))
                            self.conditionItemTableWidget.setItem(index, 7, QTableWidgetItem(str(item.highPrice)))
                            self.conditionItemTableWidget.setItem(index, 8, QTableWidgetItem(str(item.lowPrice)))
                            self.conditionItemTableWidget.setItem(index, 9, QTableWidgetItem(str(item.sRQName)))
                            break
                    if check3 == 1 :
                        break

    def autoTrade(self):
        # 조건 검색 버튼 클릭시
        if self.boolAutoTrade == 0:
            # 처음 버튼 확인후 라벨 변경 (시작 -> 종료)
            self.autoTradePushButton.setText("자동매매종료")
            self.boolAutoTrade = 1
        else:
            # 시작 상태 체크 후 (종료 -> 시작)
            self.autoTradePushButton.setText("자동매매시작")
            self.boolAutoTrade = 0


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myApp = MyBot()
    myApp.show()
    app.exec()

