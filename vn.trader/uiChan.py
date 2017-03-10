# encoding: UTF-8

"""
该文件中包含的是交易平台的上层UI部分，
Widget主要用于调用主动功能，有部分包含数据监控。
"""

from __future__ import division

import time
import sys
import os
import json
import numpy as np
import math
import shelve
from collections import OrderedDict

import sip
from PyQt5 import QtCore, QtGui,QtWidgets

import pyqtgraph as pg
import numpy as np
from eventEngine import *
from pymongo import MongoClient
from pymongo.errors import *
from datetime import datetime, timedelta
from PyQt5.QtCore import *
from dataRecorder.drBase import *
from chan import Chan


from eventEngine import *
from vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData
from vtConstant import *

# Local Configure
CONF_SYMBOL = 'rb1705'
SETTING_FILENAME = 'VT_setting.json'
path = os.path.abspath(os.path.dirname(__file__))   
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME)     

########################################################################
class UIChan(QObject):
    """用于显示价格走势图"""
    signal = QtCore.pyqtSignal(type(Event()))

    # tick图的相关参数、变量
    listlastPrice = np.empty(1000)

    fastMA = 0
    midMA = 0
    slowMA = 0
    listfastMA = np.empty(1000)
    listmidMA = np.empty(1000)
    listslowMA = np.empty(1000)
    tickFastAlpha = 0.0333    # 快速均线的参数,30
    tickMidAlpha = 0.0167     # 中速均线的参数,60
    tickSlowAlpha = 0.0083    # 慢速均线的参数,120

    ptr = 0
    ticktime = None  # tick数据时间

    # K线图EMA均线的参数、变量
    EMAFastAlpha = 0.0167    # 快速EMA的参数,60
    EMASlowAlpha = 0.0083  # 慢速EMA的参数,120
    fastEMA = 0        # 快速EMA的数值
    slowEMA = 0        # 慢速EMA的数值
    listfastEMA = []
    listslowEMA = []

    # K线缓存对象
    barOpen = 0
    barHigh = 0
    barLow = 0
    barClose = 0
    barTime = None
    barOpenInterest = 0
    num = 0

    # 保存K线数据的列表对象
    listBar = []
    listClose = []
    listHigh = []
    listLow = []
    listOpen = []
    listOpenInterest = []
    listTimes = [] #暂时以序列号代替

    chan = None

    # 是否完成了历史数据的读取
    initCompleted = False
    # 初始化时读取的历史数据的起始日期(可以选择外部设置)
    startDate = None
    symbol = CONF_SYMBOL #'rb1705'

        
    # Create a subclass of GraphicsObject.
    # The only required methods are paint() and boundingRect()
    # (see QGraphicsItem documentation)

    class CandlestickItem(pg.GraphicsObject):
        def __init__(self):
            pg.GraphicsObject.__init__(self)
            self.flagHasData = False

        def set_data(self, data):
            self.data = data  # data must have fields: time, open, close, min, max
            self.flagHasData = True
            self.generatePicture()
            self.informViewBoundsChanged()

        def generatePicture(self):
            # pre-computing a QPicture object allows paint() to run much more quickly,
            # rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen('w'))
            #w = (self.data[1][0] - self.data[0][0]) / 3.
            w = 1/3.
            for (t, open, close, min, max) in self.data:
                p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
                if open > close:
                    p.setBrush(pg.mkBrush('g'))
                else:
                    p.setBrush(pg.mkBrush('r'))
                p.drawRect(QtCore.QRectF(t - w, open, w * 2, close - open))
            p.end()

        def paint(self, p, *args):
            if self.flagHasData:
                p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            # boundingRect _must_ indicate the entire area that will be drawn on
            # or else we will get artifacts and possibly crashing.
            # (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())


    class BisItem(pg.GraphicsObject):
        def __init__(self):
            pg.GraphicsObject.__init__(self)
            self.flagHasData = False

        def set_data(self, data):
            self.data = data  # data must have fields: time, open, close, min, max
            self.flagHasData = True
            self.generatePicture()
            self.informViewBoundsChanged()

        def generatePicture(self):
            # pre-computing a QPicture object allows paint() to run much more quickly,
            # rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)

            for bi in self.data:
                if bi.biType == 'up':
                    p.setPen(pg.mkPen('r'))
                    p.drawLine(QtCore.QPointF(chan.chanBars[bi.barIndex1].closeIndex, chan.lowBar[chan.chanBars[bi.barIndex1].closeIndex]), QtCore.QPointF(
                        chan.chanBars[bi.barIndex2].closeIndex, chan.highBar[chan.chanBars[bi.barIndex2].closeIndex]))
                else:
                    p.setPen(pg.mkPen('g'))
                    p.drawLine(QtCore.QPointF(chan.chanBars[bi.barIndex1].closeIndex, chan.highBar[chan.chanBars[bi.barIndex1].closeIndex]), QtCore.QPointF(
                        chan.chanBars[bi.barIndex2].closeIndex, chan.lowBar[chan.chanBars[bi.barIndex2].closeIndex]))
            p.end()

        def paint(self, p, *args):
            if self.flagHasData:
                p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            # boundingRect _must_ indicate the entire area that will be drawn on
            # or else we will get artifacts and possibly crashing.
            # (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())


    class LinesItem(pg.GraphicsObject):
        def __init__(self):
            pg.GraphicsObject.__init__(self)
            self.flagHasData = False

        def set_data(self, data):
            self.data = data  # data must have fields: time, open, close, min, max
            self.flagHasData = True
            self.generatePicture()
            self.informViewBoundsChanged()

        def generatePicture(self):
            # pre-computing a QPicture object allows paint() to run much more quickly,
            # rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)

            for line in self.data:
                if line.lineType == 'up':
                    p.setPen(pg.mkPen('r'))
                    p.drawLine(QtCore.QPointF(chan.chanBars[line.barIndex1].closeIndex, chan.lowBar[chan.chanBars[line.barIndex1].closeIndex]), QtCore.QPointF(
                        chan.chanBars[line.barIndex2].closeIndex, chan.highBar[chan.chanBars[line.barIndex2].closeIndex]))
                else:
                    p.setPen(pg.mkPen('g'))
                    p.drawLine(QtCore.QPointF(chan.chanBars[line.barIndex1].closeIndex, chan.highBar[chan.chanBars[line.barIndex1].closeIndex]), QtCore.QPointF(
                        chan.chanBars[line.barIndex2].closeIndex, chan.lowBar[chan.chanBars[line.barIndex2].closeIndex]))
            p.end()

        def paint(self, p, *args):
            if self.flagHasData:
                p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            # boundingRect _must_ indicate the entire area that will be drawn on
            # or else we will get artifacts and possibly crashing.
            # (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())


    class ZhongshusItem(pg.GraphicsObject):
        def __init__(self):
            pg.GraphicsObject.__init__(self)
            self.flagHasData = False

        def set_data(self, data):
            self.data = data  # data must have fields: time, open, close, min, max
            self.flagHasData = True
            self.generatePicture()
            self.informViewBoundsChanged()

        def generatePicture(self):
            # pre-computing a QPicture object allows paint() to run much more quickly,
            # rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen('w'))
            p.setBrush(pg.mkBrush(None))
            for zhongshu in self.data:
                p.drawRect(QtCore.QRectF(chan.chanBars[zhongshu.barIndex1].closeIndex,
                                        zhongshu.low, chan.chanBars[
                                            zhongshu.barIndex2].closeIndex - chan.chanBars[zhongshu.barIndex1].closeIndex,
                                        zhongshu.high - zhongshu.low))
            p.end()

        def paint(self, p, *args):
            if self.flagHasData:
                p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            # boundingRect _must_ indicate the entire area that will be drawn on
            # or else we will get artifacts and possibly crashing.
            # (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())


    class BeiChiItem(pg.GraphicsObject):
        def __init__(self):
            pg.GraphicsObject.__init__(self)
            self.flagHasData = False

        def set_data(self, data):
            self.data = data  # data must have fields: time, open, close, min, max
            self.flagHasData = True
            self.generatePicture()
            self.informViewBoundsChanged()

        def generatePicture(self):
            # pre-computing a QPicture object allows paint() to run much more quickly,
            # rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen('w',width=15))
            p.setPen(pg.mkColor("#FF0000"))
            p.setBrush(pg.mkBrush(None))
            for i in self.data:
                p.drawPoint(i, chan.closeBar[i])
            p.end()

        def paint(self, p, *args):
            if self.flagHasData:
                p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            # boundingRect _must_ indicate the entire area that will be drawn on
            # or else we will get artifacts and possibly crashing.
            # (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())


    class DateAxis(pg.AxisItem):
        def __init__(self, dates, *args, **kwargs):
            pg.AxisItem.__init__(self, *args, **kwargs)
            self.x_values = list(range(len(dates)))
    #        self.x_strings = []
    #        for i in dates:
    #            self.x_strings.append(i.strftime('%Y%m%d'))
            self.x_strings = dates
            
        def tickStrings(self, values, scale, spacing):
            strings = []
            if(len(values)==0):
                return strings
            rng = max(values)-min(values)
            for v in values:
                vs = v* scale
                if vs in self.x_values:
                    if rng >= 100:
                        
                        #vstr = self.x_strings[np.abs(self.x_values-vs).argmin()].strftime('%Y%m%d')
                        vstr = ""
                    else:
                        #vstr = self.x_strings[np.abs(self.x_values-vs).argmin()].strftime('%Y%m%d,%H:%M')
                        vstr = ""
                else:
                    vstr = ""
                strings.append(vstr)         
            return strings

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(UIChan, self).__init__(parent)
        
        self.__eventEngine = eventEngine
        self.__mainEngine = mainEngine
        # MongoDB数据库相关
        self.__mongoConnected = False
        self.__mongoConnection = None
        self.__mongoTickDB = None

        # 调用函数
        self.__connectMongo()
        self.initUi(startDate=None)
        self.registerEvent()

    #----------------------------------------------------------------------
    def initUi(self, startDate=None):
        """初始化界面"""
        self.initplotTick()  # plotTick初始化
        self.initHistoricalData()  # 下载历史数据

    #----------------------------------------------------------------------
    def initplotTick(self):
        """"""
        global chan
        chan = Chan([],[],[],[],[],[])

        for index in range(0,len(self.listBar)):
            chan.append(self.listOpen[index],self.listHigh[index],self.listLow[index],self.listClose[index],self.listOpenInterest[index], self.listTimes[index])

        if(chan.length>26):
            chan.barsMerge()
            chan.findFenxing()
            chan.findBi()
            chan.findLines()
            chan.findZhongshus()
            chan.calculate_ta()
            chan.findBiZhongshus()
            chan.macdSeparate()
            chan.findTrendLines()
            chan.decisionBi()

        win = pg.GraphicsWindow()
        win.setWindowTitle('行情+缠论')
        label = pg.LabelItem(justify = "center")
        win.addItem(label)
        axis = self.DateAxis(self.listTimes,orientation='bottom')
        p1 = win.addPlot(row=1, col=0,axisItems = {'bottom':axis})
        p2 = win.addPlot(row=2, col=0,axisItems = {'bottom':axis})
        p2.setXLink(p1)
        p2.plot(x = list(range(len(self.listBar))),y = chan.diff,pen = 'w')
        p2.plot(x = list(range(len(self.listBar))),y = chan.dea,pen = 'y')
        hLine = pg.InfiniteLine(angle=0, movable=False)
        hLine.setPos(0)
        p2.addItem(hLine, ignoreBounds=True)
        macdPositive = []
        macdNegetive = []
        for i in chan.macd:
            if i>=0:
                macdPositive.append(i)
                macdNegetive.append(0)
            else:
                macdPositive.append(0)
                macdNegetive.append(i)
                
        self.curve0 = p2.plot(x = list(range(len(self.listBar))),y = np.zeros(len(self.listBar)))
        self.curve1 = p2.plot(x = list(range(len(self.listBar))),y = macdPositive, pen = 'w')
        self.curve2 = p2.plot(x = list(range(len(self.listBar))),y = macdNegetive, pen = 'w')
        self.itemFill1 = pg.FillBetweenItem(self.curve0,self.curve1,pg.mkBrush('r'))
        self.itemFill2 = pg.FillBetweenItem(self.curve0,self.curve2,pg.mkBrush('g'))
        p2.addItem(self.itemFill1)
        p2.addItem(self.itemFill2)


        self.itemK = self.CandlestickItem()
        self.itemK.set_data(self.listBar)
        self.itemBi = self.BisItem()
        self.itemBi.set_data(chan.bis)
        self.itemLine = self.LinesItem()
        self.itemLine.set_data(chan.lines)
        self.itemZhongshu = self.ZhongshusItem()
        #itemZhongshu.set_data(chan.zhongshus)
        self.itemZhongshu.set_data(chan.biZhongshus)

        # self.itemDiBeiChi = self.BeiChiItem()
        # self.itemDiBeiChi.set_data(chan.dibeichi)
        # self.itemDingBeiChi = self.BeiChiItem()
        # self.itemDingBeiChi.set_data(chan.dingbeichiLine)
        # self.itemTrendDiBeiChi = self.BeiChiItem()
        # self.itemTrendDiBeiChi.set_data(chan.trendDibeichi)
        # self.itemTrendDingBeiChi = self.BeiChiItem()
        # self.itemTrendDingBeiChi.set_data(chan.trendDingbeichi)


        p1.plot()
        p1.addItem(self.itemK)
        p1.addItem(self.itemBi)
        p1.addItem(self.itemLine)
        p1.addItem(self.itemZhongshu)
        # p1.addItem(self.itemDiBeiChi)
        # p1.addItem(self.itemDingBeiChi)
        # p1.addItem(self.itemTrendDiBeiChi)
        # p1.addItem(self.itemTrendDingBeiChi)
        p1.showGrid(x=True,y=True)

        #p1.setWindowTitle('pyqtgraph example: customGraphicsItem')

        # cross hair
        vLine = pg.InfiniteLine(angle=90, movable=False)
        hLine = pg.InfiniteLine(angle=0, movable=False)
        p1.addItem(vLine, ignoreBounds=True)
        p1.addItem(hLine, ignoreBounds=True)


        vb1 = p1.vb
        vb2 = p2.vb

        def mouseMoved(evt):
            pos = evt[0]  # using signal proxy turns original arguments into a tuple
            if p1.sceneBoundingRect().contains(pos):
                mousePoint = vb1.mapSceneToView(pos)
                index = int(mousePoint.x())
                if index > 0 and index < len(self.listBar):
                    label.setText("<span style='font-size: 12pt'>date=%d,   <span style='color: red'>open=%0.01f</span>,   <span style='color: green'>close=%0.01f\n, high = %0.01f, low = %0.01f</span>" %
                                (self.listTimes[index], self.listBar[index][1], self.listBar[index][2], self.listBar[index][3], self.listBar[index][4]))
                vLine.setPos(mousePoint.x())
                hLine.setPos(mousePoint.y())
            setYRange()
            
            
        def setYRange():
            r = vb1.viewRange()
            xmin = math.floor(r[0][0])
            xmax = math.ceil(r[0][1])

            #fix index <0 bug
            xmax = max(0,xmax-xmin)
            xmin = max(0,xmin)

            xmin = min(xmin,len(self.listBar))
            xmax = min(xmax,len(self.listBar))
            xmax = max(xmin,xmax)
            if(xmin==xmax):
                return

            if(len(self.listBar)):
                highBound1 = max(self.listHigh[xmin:xmax])
                lowBound1 = min(self.listLow[xmin:xmax])
                p1.setRange(yRange=(lowBound1,highBound1))
            if(len(self.chan.diff)):
                highBound2 = max(self.chan.diff[xmin:xmax])
                lowBound2 = min(self.chan.diff[xmin:xmax])
                p2.setRange(yRange=(lowBound2,highBound2))
        
        self.proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
        self.win = win
        self.p1 = p1
        self.p2 = p2
        self.chan = chan
        self.axis = axis

    #----------------------------------------------------------------------
    def initHistoricalData(self,startDate=None):
        """初始历史数据"""

        td = timedelta(days=20)     # 读取3天的历史TICK数据

        if startDate:
            cx = self.loadTick(self.symbol, startDate-td)
        else:
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            cx = self.loadTick(self.symbol, today-td)

        if cx:
            for data in cx:
                tick = DrTickData()
                tick.__dict__ = data
                self.onTick(tick)

        self.initCompleted = True    # 读取历史数据完成
        # pprint('load historic data completed')

    #----------------------------------------------------------------------
    def updateMarketData(self, event):
        """更新行情"""
        tick = event.dict_['data']
        self.onTick(tick)  # tick数据更新

        # # 将数据插入MongoDB数据库，实盘建议另开程序记录TICK数据
        # self.__recordTick(data)

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """tick数据更新"""
        from datetime import time

        # 首先生成datetime.time格式的时间（便于比较）,从字符串时间转化为time格式的时间
        hh, mm, ss = tick.time.split(':')
        ss,ms = ss.split('.')
        self.ticktime = time(int(hh), int(mm), int(ss), microsecond=int(ms))

        # 计算tick图的相关参数
        if self.ptr == 0:
            self.fastMA = tick.lastPrice
            self.midMA = tick.lastPrice
            self.slowMA = tick.lastPrice
        else:
            self.fastMA = (1-self.tickFastAlpha) * self.fastMA + self.tickFastAlpha * tick.lastPrice
            self.midMA = (1-self.tickMidAlpha) * self.midMA + self.tickMidAlpha * tick.lastPrice
            self.slowMA = (1-self.tickSlowAlpha) * self.slowMA + self.tickSlowAlpha * tick.lastPrice
        self.listlastPrice[self.ptr] = tick.lastPrice
        self.listfastMA[self.ptr] = self.fastMA
        self.listmidMA[self.ptr] = self.midMA
        self.listslowMA[self.ptr] = self.slowMA

        self.ptr += 1
        # pprint("----------")
        # pprint(self.ptr)
        if self.ptr >= self.listlastPrice.shape[0]:
            tmp = self.listlastPrice
            self.listlastPrice = np.empty(self.listlastPrice.shape[0] * 2)
            self.listlastPrice[:tmp.shape[0]] = tmp

            tmp = self.listfastMA
            self.listfastMA = np.empty(self.listfastMA.shape[0] * 2)
            self.listfastMA[:tmp.shape[0]] = tmp

            tmp = self.listmidMA
            self.listmidMA = np.empty(self.listmidMA.shape[0] * 2)
            self.listmidMA[:tmp.shape[0]] = tmp

            tmp = self.listslowMA
            self.listslowMA = np.empty(self.listslowMA.shape[0] * 2)
            self.listslowMA[:tmp.shape[0]] = tmp

        # K线数据
        # 假设是收到的第一个TICK
        if self.barOpen == 0:
            # 初始化新的K线数据
            self.barOpen = tick.lastPrice
            self.barHigh = tick.lastPrice
            self.barLow = tick.lastPrice
            self.barClose = tick.lastPrice
            self.barTime = self.ticktime
            self.barOpenInterest = tick.openInterest
            self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
        else:
            # 如果是当前一分钟内的数据
            if self.ticktime.minute == self.barTime.minute:
                # 汇总TICK生成K线
                self.barHigh = max(self.barHigh, tick.lastPrice)
                self.barLow = min(self.barLow, tick.lastPrice)
                self.barClose = tick.lastPrice
                self.barTime = self.ticktime
            # 如果是新一分钟的数据
            else:
                # 先保存K线收盘价
                self.num += 1
                self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
                # 初始化新的K线数据
                self.barOpen = tick.lastPrice
                self.barHigh = tick.lastPrice
                self.barLow = tick.lastPrice
                self.barClose = tick.lastPrice
                self.barTime = self.ticktime
                self.barOpenInterest = tick.openInterest

    #----------------------------------------------------------------------
    def onBar(self, n, o, c, l, h, oi):
        self.listBar.append((n, o, c, l, h))
        self.listTimes.append(n)
        self.listOpen.append(o)
        self.listClose.append(c)
        self.listHigh.append(h)
        self.listLow.append(l)
        self.listOpenInterest.append(oi)
        
        #计算K线图EMA均线
        if self.fastEMA:
            self.fastEMA = c*self.EMAFastAlpha + self.fastEMA*(1-self.EMAFastAlpha)
            self.slowEMA = c*self.EMASlowAlpha + self.slowEMA*(1-self.EMASlowAlpha)
        else:
            self.fastEMA = c
            self.slowEMA = c
        self.listfastEMA.append(self.fastEMA)
        self.listslowEMA.append(self.slowEMA)

        # 调用画图函数
        #self.plotTick()      # tick图
        self.plotKline()     # K线图
        self.plotMACD()     #macd
        #self.plotTendency()  # K线副图，持仓量
    #----------------------------------------------------------------------
    def plotKline(self):
        """K线图"""
        #if self.initCompleted:
        self.chan.append(self.barOpen,self.barHigh,self.barLow,self.barClose,self.barOpenInterest, self.barTime)
        if(self.chan.length>26):
            self.chan.barsMerge()
            self.chan.findFenxing()
            self.chan.findBi()
            self.chan.findLines()
            self.chan.findZhongshus()
            self.chan.calculate_ta()
            self.chan.findBiZhongshus()
            self.chan.macdSeparate()
            self.chan.findTrendLines()
            self.chan.decisionBi()

            self.itemK.set_data(self.listBar)
            self.itemBi.set_data(self.chan.bis)
            self.itemLine.set_data(self.chan.lines)
            self.itemZhongshu.set_data(self.chan.biZhongshus)

            app = QtGui.QApplication.instance()
            app.processEvents()  ## force complete redraw for every plot

    def plotMACD(self):
        """K线图"""
        #if self.initCompleted:
        if(self.chan.length>26):
            self.p2.clear()
            self.p2.plot(x = list(range(len(self.listBar))),y = chan.diff,pen = 'w')
            self.p2.plot(x = list(range(len(self.listBar))),y = chan.dea,pen = 'y')
            hLine = pg.InfiniteLine(angle=0, movable=False)
            hLine.setPos(0)
            self.p2.addItem(hLine, ignoreBounds=True)
            macdPositive = []
            macdNegetive = []
            for i in self.chan.macd:
                if i>=0:
                    macdPositive.append(i)
                    macdNegetive.append(0)
                else:
                    macdPositive.append(0)
                    macdNegetive.append(i)
                    
            self.curve0 = self.p2.plot(x = list(range(len(self.listBar))),y = np.zeros(len(self.listBar)))
            self.curve1 = self.p2.plot(x = list(range(len(self.listBar))),y = macdPositive, pen = 'w')
            self.curve2 = self.p2.plot(x = list(range(len(self.listBar))),y = macdNegetive, pen = 'w')
            self.itemFill1 = pg.FillBetweenItem(self.curve0,self.curve1,pg.mkBrush('r'))
            self.itemFill2 = pg.FillBetweenItem(self.curve0,self.curve2,pg.mkBrush('g'))
            self.p2.addItem(self.itemFill1)
            self.p2.addItem(self.itemFill2)

    #----------------------------------------------------------------------
    def __connectMongo(self):
        """连接MongoDB数据库"""
        try:
            f = open(SETTING_FILENAME)
            setting = json.load(f)
            self.__mongoConnection = MongoClient(setting['mongoHost'])
            self.__mongoConnected = True
            self.__mongoTickDB = self.__mongoConnection['VnTrader_Tick_Db']
        except ConnectionFailure:
            pass

    #----------------------------------------------------------------------
    def __recordTick(self, data):
        """将Tick数据插入到MongoDB中"""
        if self.__mongoConnected:
            symbol = data['InstrumentID']
            data['date'] = self.today
            self.__mongoTickDB[symbol].insert(data)

    #----------------------------------------------------------------------
    def loadTick(self, symbol, startDate, endDate=None):
        """从MongoDB中读取Tick数据"""
        if self.__mongoConnected:
            collection = self.__mongoTickDB[symbol]
            # 如果输入了读取TICK的最后日期
            if endDate:
                cx = collection.find({'datetime': {'$gte': startDate, '$lte': endDate}})
            else:
                cx = collection.find({'datetime': {'$gte': startDate}})
            return cx
        else:
            return None

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateMarketData)
        self.__eventEngine.register(EVENT_TICK, self.signal.emit)

    #----------------------------------------------------------------------
    def updateSymbol(self):
        """合约变化"""
        # 读取组件数据
        symbol = self.symbol
        exchange = None
        vtSymbol = None
        # 查询合约
        if exchange:
            vtSymbol = '.'.join([symbol, exchange])
            contract = self.__mainEngine.getContract(vtSymbol)
        else:
            vtSymbol = symbol
            contract = self.__mainEngine.getContract(symbol)   
        
        if contract:
            vtSymbol = contract.vtSymbol
            gatewayName = contract.gatewayName
            print(contract.name)
            exchange = contract.exchange    # 保证有交易所代码

        # 重新注册事件监听
        self.__eventEngine.unregister(EVENT_TICK + symbol, self.signal.emit)
        self.__eventEngine.register(EVENT_TICK + vtSymbol, self.signal.emit)

        # 订阅合约
        req = VtSubscribeReq()
        req.symbol = symbol
        req.exchange = exchange
        #req.currency = currency
        req.productClass = PRODUCT_FUTURES

        self.__mainEngine.subscribe(req, gatewayName)

        # 更新组件当前交易的合约
        self.symbol = vtSymbol


import sys
import os
import ctypes
import platform
import importlib

import vtPath
from uiChanMainWindow import *

from eventEngine import *
from vnrpc import RpcClient


# 文件路径名
path = os.path.abspath(os.path.dirname(__file__))    
ICON_FILENAME = 'vnpy.ico'
ICON_FILENAME = os.path.join(path, ICON_FILENAME)  

SETTING_FILENAME = 'VT_setting.json'
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME)     


########################################################################
class VtClient(RpcClient):
    """vn.trader客户端"""

    #----------------------------------------------------------------------
    def __init__(self, reqAddress, subAddress, eventEngine):
        """Constructor"""
        super(VtClient, self).__init__(reqAddress, subAddress)
        
        self.eventEngine = eventEngine
        
        self.usePickle()
        
    #----------------------------------------------------------------------
    def callback(self, topic, data):
        """回调函数"""
        self.eventEngine.put(data)


########################################################################
class ClientEngine(object):
    """客户端引擎，提供和MainEngine完全相同的API接口"""

    #----------------------------------------------------------------------
    def __init__(self, client, eventEngine):
        """Constructor"""
        self.client = client
        self.eventEngine = eventEngine
    
    #----------------------------------------------------------------------  
    def connect(self, gatewayName):
        """连接特定名称的接口"""
        self.client.connect(gatewayName)
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq, gatewayName):
        """订阅特定接口的行情"""
        self.client.subscribe(subscribeReq, gatewayName)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq, gatewayName):
        """对特定接口发单"""
        self.client.sendOrder(orderReq, gatewayName)    
    
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq, gatewayName):
        """对特定接口撤单"""
        self.client.cancelOrder(cancelOrderReq, gatewayName)
        
    #----------------------------------------------------------------------
    def qryAccont(self, gatewayName):
        """查询特定接口的账户"""
        self.client.qryAccount(gatewayName)
        
    #----------------------------------------------------------------------
    def qryPosition(self, gatewayName):
        """查询特定接口的持仓"""
        self.client.qryPosition(gatewayName)
        
    #----------------------------------------------------------------------
    def exit(self):
        """退出程序前调用，保证正常退出"""  
        # 停止事件引擎
        self.eventEngine.stop()      
        
        # 关闭客户端的推送数据接收
        self.client.stop()        
    
    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速发出日志事件"""
        self.client.writeLog(content)      
    
    #----------------------------------------------------------------------
    def dbConnect(self):
        """连接MongoDB数据库"""
        self.client.dbConnect()
    
    #----------------------------------------------------------------------
    def dbInsert(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        self.client.dbInsert(dbName, collectionName, d)
    
    #----------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的数据列表"""
        self.client.dbQuery(dbName, collectionName, d)
        
    #----------------------------------------------------------------------
    def dbUpdate(self, dbName, collectionName, d, flt, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        self.client.dbUpdate(dbName, collectionName, d, flt, upsert)
    
    #----------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约"""
        return self.client.getContract(vtSymbol)
    
    #----------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约（返回列表）"""
        return self.client.getAllContracts()
    
    #----------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        return self.client.getOrder(vtOrderID)
    
    #----------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有的活跃的委托（返回列表）"""
        return self.client.getAllWorkingOrders()
    
    #----------------------------------------------------------------------
    def getAllGatewayNames(self):
        """查询所有的接口名称"""
        return self.client.getAllGatewayNames()


#----------------------------------------------------------------------
def main():
    """客户端主程序入口"""
    # 重载sys模块，设置默认字符串编码方式为utf8
    #reload(sys)
    #sys.setdefaultencoding('utf8')    
    importlib.reload(sys)
    
    # 设置Windows底部任务栏图标
    if 'Windows' in platform.uname() :
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('vn.trader')    
    
    # 创建事件引擎
    eventEngine = EventEngine()
    eventEngine.start(timer=False)

    # 创建客户端
    f = open(SETTING_FILENAME)
    setting = json.load(f)
    reqAddress = 'tcp://' + setting['mongoHost'] + ':2014'
    subAddress = 'tcp://' + setting['mongoHost'] + ':0602'
    #reqAddress = 'tcp://192.168.31.45:2014'
    #subAddress = 'tcp://192.168.31.45:0602'
    client = VtClient(reqAddress, subAddress, eventEngine)

    client.subscribeTopic('')
    client.start()
    
    # 初始化主引擎和主窗口对象
    mainEngine = ClientEngine(client, eventEngine)

    try:
        app = QtGui.QApplication([])
    except RuntimeError:
        app = QtGui.QApplication.instance()


    """增加连接功能"""
    gatewayName = "CTP"
    mainEngine.connect(gatewayName)

    """subscribe symbol"""

    chan = UIChan(mainEngine,mainEngine.eventEngine)
    chan.updateSymbol()
    mw = chan.win
    mw.show()
        
    app.exec_()


if __name__ == '__main__':
    main()    