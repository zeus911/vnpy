# encoding: UTF-8


from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QProgressBar,
    QPushButton, QApplication)
from PyQt5.QtCore import QBasicTimer

import os,json,time

import json
import csv
import os
from collections import OrderedDict

from PyQt5 import QtGui, QtCore,QtWidgets

from eventEngine import *
from vtFunction import *
from vtGateway import *
from ctaBase import *
from ctaTemplate import CtaTemplate

########################################################################
class TradingWidget(QtWidgets.QFrame):
    """简单交易组件"""
    signal = QtCore.pyqtSignal(type(Event()))
    
    directionList = [DIRECTION_LONG,
                     DIRECTION_SHORT]

    offsetList = [OFFSET_OPEN,
                  OFFSET_CLOSE,
                  OFFSET_CLOSEYESTERDAY,
                  OFFSET_CLOSETODAY]
    
    priceTypeList = [PRICETYPE_LIMITPRICE,
                     PRICETYPE_MARKETPRICE,
                     PRICETYPE_FAK,
                     PRICETYPE_FOK]
    
    exchangeList = [EXCHANGE_NONE,
                    EXCHANGE_CFFEX,
                    EXCHANGE_SHFE,
                    EXCHANGE_DCE,
                    EXCHANGE_CZCE,
                    EXCHANGE_SSE,
                    EXCHANGE_SZSE,
                    EXCHANGE_SGE,
                    EXCHANGE_HKEX,
                    EXCHANGE_HKFE,
                    EXCHANGE_SMART,
                    EXCHANGE_ICE,
                    EXCHANGE_CME,
                    EXCHANGE_NYMEX,
                    EXCHANGE_GLOBEX,
                    EXCHANGE_IDEALPRO]
    
    currencyList = [CURRENCY_NONE,
                    CURRENCY_CNY,
                    CURRENCY_HKD,
                    CURRENCY_USD]
    
    productClassList = [PRODUCT_NONE,
                        PRODUCT_EQUITY,
                        PRODUCT_FUTURES,
                        PRODUCT_OPTION,
                        PRODUCT_FOREX]
    
    gatewayList = ['']

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(TradingWidget, self).__init__(parent)
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        self.symbol = ''
        
        # 添加交易接口
        #self.gatewayList.extend(mainEngine.getAllGatewayNames())
        # use CTP as default
        self.gatewayList = mainEngine.getAllGatewayNames() 

        self.initUi()
        self.connectSignal()

    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'交易')
        self.setMaximumWidth(400)
        self.setFrameShape(self.Box)    # 设置边框
        self.setLineWidth(1)           

        # 左边部分
        labelSymbol = QtWidgets.QLabel(u'代码')
        labelName =  QtWidgets.QLabel(u'名称')
        labelDirection = QtWidgets.QLabel(u'方向类型')
        labelOffset = QtWidgets.QLabel(u'开平')
        labelPrice = QtWidgets.QLabel(u'价格')
        self.checkFixed = QtWidgets.QCheckBox(u'')  # 价格固定选择框
        labelVolume = QtWidgets.QLabel(u'数量')
        labelPriceType = QtWidgets.QLabel(u'价格类型')
        labelExchange = QtWidgets.QLabel(u'交易所') 
        labelCurrency = QtWidgets.QLabel(u'货币')
        labelProductClass = QtWidgets.QLabel(u'产品类型')
        labelGateway = QtWidgets.QLabel(u'交易接口')

        self.lineSymbol = QtWidgets.QLineEdit()
        self.lineName = QtWidgets.QLineEdit()

        self.comboDirection = QtWidgets.QComboBox()
        self.comboDirection.addItems(self.directionList)

        self.comboOffset = QtWidgets.QComboBox()
        self.comboOffset.addItems(self.offsetList)

        self.spinPrice = QtWidgets.QDoubleSpinBox()
        self.spinPrice.setDecimals(4)
        self.spinPrice.setMinimum(0)
        self.spinPrice.setMaximum(100000)

        self.spinVolume = QtWidgets.QSpinBox()
        self.spinVolume.setMinimum(0)
        self.spinVolume.setMaximum(1000000)

        self.comboPriceType = QtWidgets.QComboBox()
        self.comboPriceType.addItems(self.priceTypeList)
        
        self.comboExchange = QtWidgets.QComboBox()
        self.comboExchange.addItems(self.exchangeList)      
        
        self.comboCurrency = QtWidgets.QComboBox()
        self.comboCurrency.addItems(self.currencyList)
        
        self.comboProductClass = QtWidgets.QComboBox()
        self.comboProductClass.addItems(self.productClassList)     
        
        self.comboGateway = QtWidgets.QComboBox()
        self.comboGateway.addItems(self.gatewayList)          

        gridleft = QtWidgets.QGridLayout()
        gridleft.addWidget(labelSymbol, 0, 0)
        gridleft.addWidget(labelName, 1, 0)
        gridleft.addWidget(labelDirection, 2, 0)
        gridleft.addWidget(labelOffset, 3, 0)
        gridleft.addWidget(labelPrice, 4, 0)
        gridleft.addWidget(labelVolume, 5, 0)
        gridleft.addWidget(labelPriceType, 6, 0)
        gridleft.addWidget(labelExchange, 7, 0)
        gridleft.addWidget(labelCurrency, 8, 0)
        gridleft.addWidget(labelProductClass, 9, 0)   
        gridleft.addWidget(labelGateway, 10, 0)
        
        gridleft.addWidget(self.lineSymbol, 0, 1, 1, -1)
        gridleft.addWidget(self.lineName, 1, 1, 1, -1)
        gridleft.addWidget(self.comboDirection, 2, 1, 1, -1)
        gridleft.addWidget(self.comboOffset, 3, 1, 1, -1)
        gridleft.addWidget(self.checkFixed, 4, 1)
        gridleft.addWidget(self.spinPrice, 4, 2)
        gridleft.addWidget(self.spinVolume, 5, 1, 1, -1)
        gridleft.addWidget(self.comboPriceType, 6, 1, 1, -1)
        gridleft.addWidget(self.comboExchange, 7, 1, 1, -1)
        gridleft.addWidget(self.comboCurrency, 8, 1, 1, -1)
        gridleft.addWidget(self.comboProductClass, 9, 1, 1, -1)
        gridleft.addWidget(self.comboGateway, 10, 1, 1, -1)

        # 右边部分
        labelBid1 = QtWidgets.QLabel(u'买一')
        labelBid2 = QtWidgets.QLabel(u'买二')
        labelBid3 = QtWidgets.QLabel(u'买三')
        labelBid4 = QtWidgets.QLabel(u'买四')
        labelBid5 = QtWidgets.QLabel(u'买五')

        labelAsk1 = QtWidgets.QLabel(u'卖一')
        labelAsk2 = QtWidgets.QLabel(u'卖二')
        labelAsk3 = QtWidgets.QLabel(u'卖三')
        labelAsk4 = QtWidgets.QLabel(u'卖四')
        labelAsk5 = QtWidgets.QLabel(u'卖五')

        self.labelBidPrice1 = QtWidgets.QLabel()
        self.labelBidPrice2 = QtWidgets.QLabel()
        self.labelBidPrice3 = QtWidgets.QLabel()
        self.labelBidPrice4 = QtWidgets.QLabel()
        self.labelBidPrice5 = QtWidgets.QLabel()
        self.labelBidVolume1 = QtWidgets.QLabel()
        self.labelBidVolume2 = QtWidgets.QLabel()
        self.labelBidVolume3 = QtWidgets.QLabel()
        self.labelBidVolume4 = QtWidgets.QLabel()
        self.labelBidVolume5 = QtWidgets.QLabel()	

        self.labelAskPrice1 = QtWidgets.QLabel()
        self.labelAskPrice2 = QtWidgets.QLabel()
        self.labelAskPrice3 = QtWidgets.QLabel()
        self.labelAskPrice4 = QtWidgets.QLabel()
        self.labelAskPrice5 = QtWidgets.QLabel()
        self.labelAskVolume1 = QtWidgets.QLabel()
        self.labelAskVolume2 = QtWidgets.QLabel()
        self.labelAskVolume3 = QtWidgets.QLabel()
        self.labelAskVolume4 = QtWidgets.QLabel()
        self.labelAskVolume5 = QtWidgets.QLabel()	

        labelLast = QtWidgets.QLabel(u'最新')
        self.labelLastPrice = QtWidgets.QLabel()
        self.labelReturn = QtWidgets.QLabel()

        self.labelLastPrice.setMinimumWidth(60)
        self.labelReturn.setMinimumWidth(60)

        gridRight = QtWidgets.QGridLayout()
        gridRight.addWidget(labelAsk5, 0, 0)
        gridRight.addWidget(labelAsk4, 1, 0)
        gridRight.addWidget(labelAsk3, 2, 0)
        gridRight.addWidget(labelAsk2, 3, 0)
        gridRight.addWidget(labelAsk1, 4, 0)
        gridRight.addWidget(labelLast, 5, 0)
        gridRight.addWidget(labelBid1, 6, 0)
        gridRight.addWidget(labelBid2, 7, 0)
        gridRight.addWidget(labelBid3, 8, 0)
        gridRight.addWidget(labelBid4, 9, 0)
        gridRight.addWidget(labelBid5, 10, 0)

        gridRight.addWidget(self.labelAskPrice5, 0, 1)
        gridRight.addWidget(self.labelAskPrice4, 1, 1)
        gridRight.addWidget(self.labelAskPrice3, 2, 1)
        gridRight.addWidget(self.labelAskPrice2, 3, 1)
        gridRight.addWidget(self.labelAskPrice1, 4, 1)
        gridRight.addWidget(self.labelLastPrice, 5, 1)
        gridRight.addWidget(self.labelBidPrice1, 6, 1)
        gridRight.addWidget(self.labelBidPrice2, 7, 1)
        gridRight.addWidget(self.labelBidPrice3, 8, 1)
        gridRight.addWidget(self.labelBidPrice4, 9, 1)
        gridRight.addWidget(self.labelBidPrice5, 10, 1)	

        gridRight.addWidget(self.labelAskVolume5, 0, 2)
        gridRight.addWidget(self.labelAskVolume4, 1, 2)
        gridRight.addWidget(self.labelAskVolume3, 2, 2)
        gridRight.addWidget(self.labelAskVolume2, 3, 2)
        gridRight.addWidget(self.labelAskVolume1, 4, 2)
        gridRight.addWidget(self.labelReturn, 5, 2)
        gridRight.addWidget(self.labelBidVolume1, 6, 2)
        gridRight.addWidget(self.labelBidVolume2, 7, 2)
        gridRight.addWidget(self.labelBidVolume3, 8, 2)
        gridRight.addWidget(self.labelBidVolume4, 9, 2)
        gridRight.addWidget(self.labelBidVolume5, 10, 2)

        # 发单按钮
        buttonSendOrder = QtWidgets.QPushButton(u'发单')
        
        size = buttonSendOrder.sizeHint()
        buttonSendOrder.setMinimumHeight(size.height()*2)   # 把按钮高度设为默认两倍

        # 整合布局
        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(gridleft)
        hbox.addLayout(gridRight)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(buttonSendOrder)
        vbox.addStretch()

        self.setLayout(vbox)

        # 关联更新
        #buttonSendOrder.clicked.connect(self.sendOrder)
        self.buttonSendOrder = buttonSendOrder

        self.lineSymbol.returnPressed.connect(self.updateSymbol)

    #----------------------------------------------------------------------
    def updateSymbol(self):
        """合约变化"""
        # 读取组件数据
        symbol = str(self.lineSymbol.text())
        exchange = str(self.comboExchange.currentText())
        currency = str(self.comboCurrency.currentText())
        productClass = str(self.comboProductClass.currentText())           
        gatewayName = str(self.comboGateway.currentText())
        
        # 查询合约
        if exchange:
            vtSymbol = '.'.join([symbol, exchange])
            contract = self.mainEngine.getContract(vtSymbol)
        else:
            vtSymbol = symbol
            contract = self.mainEngine.getContract(symbol)   
        
        if contract:
            vtSymbol = contract.vtSymbol
            gatewayName = contract.gatewayName
            self.lineName.setText(contract.name)
            exchange = contract.exchange    # 保证有交易所代码
            
        # 清空价格数量
        self.spinPrice.setValue(0)
        self.spinVolume.setValue(0)

        # 清空行情显示
        self.labelBidPrice1.setText('')
        self.labelBidPrice2.setText('')
        self.labelBidPrice3.setText('')
        self.labelBidPrice4.setText('')
        self.labelBidPrice5.setText('')
        self.labelBidVolume1.setText('')
        self.labelBidVolume2.setText('')
        self.labelBidVolume3.setText('')
        self.labelBidVolume4.setText('')
        self.labelBidVolume5.setText('')	
        self.labelAskPrice1.setText('')
        self.labelAskPrice2.setText('')
        self.labelAskPrice3.setText('')
        self.labelAskPrice4.setText('')
        self.labelAskPrice5.setText('')
        self.labelAskVolume1.setText('')
        self.labelAskVolume2.setText('')
        self.labelAskVolume3.setText('')
        self.labelAskVolume4.setText('')
        self.labelAskVolume5.setText('')
        self.labelLastPrice.setText('')
        self.labelReturn.setText('')

        # 重新注册事件监听
        # self.eventEngine.unregister(EVENT_TICK + self.symbol, self.signal.emit)
        # self.eventEngine.register(EVENT_TICK + vtSymbol, self.signal.emit)

        self.eventEngine.unregister(EVENT_TICK + self.symbol, self.updateTick)
        self.eventEngine.register(EVENT_TICK + vtSymbol, self.updateTick)
        self.destroyed.connect( lambda:self.eventEngine.unregister(EVENT_TICK + self.symbol, self.updateTick))

        # 订阅合约
        req = VtSubscribeReq()
        req.symbol = symbol
        req.exchange = exchange
        req.currency = currency
        req.productClass = productClass

        # 默认跟随价
        self.checkFixed.setChecked(False)

        self.mainEngine.subscribe(req, gatewayName)

        # 更新组件当前交易的合约
        self.symbol = vtSymbol

    #----------------------------------------------------------------------
    def updateTick(self, event):
        """更新行情"""
        tick = event.dict_['data']

        if tick.vtSymbol == self.symbol:
            if not self.checkFixed.isChecked():
                self.spinPrice.setValue(tick.lastPrice)
            self.labelBidPrice1.setText(str(tick.bidPrice1))
            self.labelAskPrice1.setText(str(tick.askPrice1))
            self.labelBidVolume1.setText(str(tick.bidVolume1))
            self.labelAskVolume1.setText(str(tick.askVolume1))
            
            if tick.bidPrice2:
                self.labelBidPrice2.setText(str(tick.bidPrice2))
                self.labelBidPrice3.setText(str(tick.bidPrice3))
                self.labelBidPrice4.setText(str(tick.bidPrice4))
                self.labelBidPrice5.setText(str(tick.bidPrice5))
    
                self.labelAskPrice2.setText(str(tick.askPrice2))
                self.labelAskPrice3.setText(str(tick.askPrice3))
                self.labelAskPrice4.setText(str(tick.askPrice4))
                self.labelAskPrice5.setText(str(tick.askPrice5))
    
                self.labelBidVolume2.setText(str(tick.bidVolume2))
                self.labelBidVolume3.setText(str(tick.bidVolume3))
                self.labelBidVolume4.setText(str(tick.bidVolume4))
                self.labelBidVolume5.setText(str(tick.bidVolume5))
                
                self.labelAskVolume2.setText(str(tick.askVolume2))
                self.labelAskVolume3.setText(str(tick.askVolume3))
                self.labelAskVolume4.setText(str(tick.askVolume4))
                self.labelAskVolume5.setText(str(tick.askVolume5))	

            self.labelLastPrice.setText(str(tick.lastPrice))
            
            if tick.preClosePrice:
                rt = (tick.lastPrice/tick.preClosePrice)-1
                self.labelReturn.setText(('%.2f' %(rt*100))+'%')
            else:
                self.labelReturn.setText('')

    #----------------------------------------------------------------------
    def connectSignal(self):
        """连接Signal"""
        self.signal.connect(self.updateTick)

    #----------------------------------------------------------------------
    def sendOrder(self):
        """发单"""
        symbol = str(self.lineSymbol.text())
        exchange = str(self.comboExchange.currentText())
        currency = str(self.comboCurrency.currentText())
        productClass = str(self.comboProductClass.currentText())           
        gatewayName = str(self.comboGateway.currentText())        

        # 查询合约
        if exchange:
            vtSymbol = '.'.join([symbol, exchange])
            contract = self.mainEngine.getContract(vtSymbol)
        else:
            vtSymbol = symbol
            contract = self.mainEngine.getContract(symbol)
        
        if contract:
            gatewayName = contract.gatewayName
            exchange = contract.exchange    # 保证有交易所代码
            
        req = VtOrderReq()
        req.symbol = symbol
        req.exchange = exchange
        req.price = self.spinPrice.value()
        req.volume = self.spinVolume.value()
        req.direction = str(self.comboDirection.currentText())
        req.priceType = str(self.comboPriceType.currentText())
        req.offset = str(self.comboOffset.currentText())
        req.currency = currency
        req.productClass = productClass
        
        self.mainEngine.sendOrder(req, gatewayName)
            
            
    #----------------------------------------------------------------------
    def closePosition(self, symbol,position,direction):
        """根据持仓信息自动填写交易组件"""
        # 读取持仓数据，cell是一个表格中的单元格对象
        
        # 更新交易组件的显示合约
        self.lineSymbol.setText(symbol)
        self.updateSymbol()
        
        # 自动填写信息
        self.comboPriceType.setCurrentIndex(self.priceTypeList.index(PRICETYPE_LIMITPRICE))
        self.spinVolume.setValue(position)

        if direction == CTAORDER_SHORT or direction == CTAORDER_COVER:
            self.comboDirection.setCurrentIndex(self.directionList.index(DIRECTION_SHORT))
        else:
            self.comboDirection.setCurrentIndex(self.directionList.index(DIRECTION_LONG))

        if direction == CTAORDER_BUY or direction == CTAORDER_SHORT:
            self.comboOffset.setCurrentIndex(self.offsetList.index(OFFSET_OPEN))
        else:
            self.comboOffset.setCurrentIndex(self.offsetList.index(OFFSET_CLOSE))

        # 价格留待更新后由用户输入，防止有误操作

class OrderConfirmProgess(QtWidgets.QDialog):
    
    def __init__(self,mainEngine, eventEngine, symbol, pos, direction, callback):
        super().__init__()
        self.callback = callback
        self.initUI(mainEngine,eventEngine,symbol,pos,direction)


    def initUI(self,mainEngine, eventEngine,symbol, pos, direction):

        self.tradingWidget = TradingWidget(mainEngine, eventEngine)
        self.tradingWidget.closePosition(symbol,pos,direction)
        self.tradingWidget.buttonSendOrder.clicked.connect(self.doAction)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tradingWidget)
        self.setLayout(layout)

        self.pbar = QProgressBar(self)
        #self.pbar.setGeometry(30, 40, 200, 25)
        layout.addWidget(self.pbar)


        self.timer = QBasicTimer()
        self.step = 1

        #self.setGeometry(300, 300, 280, 170)
        self.setWindowTitle('倒计时确认执行定单')
        self.timer.start(100, self)
        self.show()


    def timerEvent(self, e):

        if self.step >= 100:
            self.timer.stop()
            self.pbar.setValue(100)
            self.hide()
            return

        self.step = self.step + 1
        self.pbar.setValue(self.step)


    def doAction(self):
        """确认执行定单"""
        if self.timer.isActive():
            self.timer.stop()
            self.callback()
            self.hide()

    # def closeEvent(self, evnt):
    #     print("close Event")
    #     self.tradingWidget.unregister()
    #     super(OrderConfirmProgess, self).closeEvent(evnt)
