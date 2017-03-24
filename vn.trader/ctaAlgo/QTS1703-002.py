# encoding: UTF-8

"""
基于King Keltner通道的交易策略，适合用在股指上，
展示了OCO委托和5分钟K线聚合的方法。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
3. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略
"""

from __future__ import division

import sys
sys.path.append('/Users/renxg/vnpy/vnpy/vn.trader')

from ctaBase import *
from ctaTemplate import *

import talib
import numpy as np


########################################################################
class KkStrategy(CtaTemplate):
    """基于通道外 Mean value reversal的交易策略"""
    className = 'KkStrategy'
    author = u'rxg'

    # 策略参数
    kkLength = 32           # 计算通道中值的窗口数
    kkDev = 0.7             # 计算通道宽度的偏差
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    trailingPercent = 0.8   # 百分比移动止损
    stopLossPercent = 0.2   # ATR 止损比例

    # 策略变量
    bar = None                  # 1分钟K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟
    fiveBar = None              # 1分钟K线对象

    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrValue = 0                        # 最新的ATR指标数值
    kkMid = 0                           # KK通道中轨
    kkUp = 0                            # KK通道上轨
    kkDown = 0                          # KK通道下轨

    buyOrderID = None              # OCO委托买入开仓的委托号
    shortOrderID = None            # OCO委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'kkLength',
                 'kkDev',
                 'stopLossPercent']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue',
               'kkMid',
               'kkUp',
               'kkDown']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(KkStrategy, self).__init__(ctaEngine, setting)
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 聚合为1分钟K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:  
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间

            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 如果当前是一个5分钟走完
        if bar.datetime.minute % 15 == 0:
            # 如果已经有聚合5分钟K线
            if self.fiveBar:
                # 将最新分钟的数据更新到目前5分钟线中
                fiveBar = self.fiveBar
                fiveBar.high = max(fiveBar.high, bar.high)
                fiveBar.low = min(fiveBar.low, bar.low)
                fiveBar.close = bar.close
                
                # 推送5分钟线数据
                self.onFiveBar(fiveBar)
                
                # 清空5分钟线数据缓存
                self.fiveBar = None
        else:
            # 如果没有缓存则新建
            if not self.fiveBar:
                fiveBar = CtaBarData()
                
                fiveBar.vtSymbol = bar.vtSymbol
                fiveBar.symbol = bar.symbol
                fiveBar.exchange = bar.exchange
            
                fiveBar.open = bar.open
                fiveBar.high = bar.high
                fiveBar.low = bar.low
                fiveBar.close = bar.close
            
                fiveBar.date = bar.date
                fiveBar.time = bar.time
                fiveBar.datetime = bar.datetime 
                
                self.fiveBar = fiveBar
            else:
                fiveBar = self.fiveBar
                fiveBar.high = max(fiveBar.high, bar.high)
                fiveBar.low = min(fiveBar.low, bar.low)
                fiveBar.close = bar.close
    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []
    
        # 保存K线数据
        self.closeArray[0:self.bufferSize-1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize-1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize-1] = self.lowArray[1:self.bufferSize]
    
        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
    
        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return
    
        # 计算指标数值
        self.atrValue = talib.ATR(self.highArray, 
                                  self.lowArray, 
                                  self.closeArray,
                                  self.kkLength)[-1]

        self.kkMidLast = self.kkMid
        self.kkMid = talib.MA(self.closeArray, self.kkLength)[-1]
        self.kkUp = self.kkMid + self.atrValue * self.kkDev
        self.kkDown = self.kkMid - self.atrValue * self.kkDev
    
        # 判断是否要进行交易
    
        # # 当前无仓位，发送OCO开仓委托
        # if self.pos == 0:
        #     self.sendOcoOrder(self.kkUp, self.kkDown, self.fixedSize)
    
        # # 持有多头仓位
        # elif self.pos > 0 and bar.close < self.kkUp:
        #     orderID = self.sell(bar.close*0.97, abs(self.pos))
        #     self.orderList.append(orderID)
    
        # # 持有空头仓位
        # elif self.pos < 0 and bar.close > self.kkDown:
        #     orderID = self.buy(bar.close*1.03, abs(self.pos))
        #     self.orderList.append(orderID)

        # 最后半小时不再持仓
        timeA = datetime.strptime(bar.time, "%H:%M:%S")
        timeBegin = datetime.strptime("09:30:00", "%H:%M:%S")
        timeStop = datetime.strptime("14:30:00", "%H:%M:%S")

        if timeA < timeBegin or timeA > timeStop:
            #平仓
            if self.pos == 0:
                return
            elif self.pos > 0:
                orderID = self.short(bar.close -5, abs(self.pos), stop=True)
                self.orderList.append(orderID)
            elif self.pos < 0:
                orderID = self.buy(bar.close + 5, abs(self.pos), stop=True)
                self.orderList.append(orderID)
                


        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            if bar.close > self.kkUp and self.kkMidLast>self.kkMid:
                #print("short", bar.close)
                orderID = self.short(bar.close-5, self.fixedSize)
                self.orderList.append(orderID)

            elif bar.close < self.kkDown and self.kkMidLast<self.kkMid:
                #print("buy", bar.close)
                orderID = self.buy(bar.close+5, self.fixedSize)
                self.orderList.append(orderID)

                # 持有多头仓位
        elif self.pos > 0:
            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            # 计算多头移动止损
            #longStop = self.intraTradeHigh * (1-self.trailingPercent/100)
            longStop = self.intraTradeHigh - max(self.atrValue*self.stopLossPercent,(self.intraTradeHigh - self.intraTradeLow)*0.3)
            # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
            #print("current:cover", bar.close," ", longStop)
            orderID = self.short(longStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)

        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)

            #shortStop = self.intraTradeLow * (1+self.trailingPercent/100)
            #print("current:sell", bar.close," ", shortStop)
            shortStop = self.intraTradeLow + max(self.atrValue*self.stopLossPercent,abs(self.intraTradeHigh - self.intraTradeLow)*0.3)
            orderID = self.buy(shortStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)
                
    
        # 发出状态更新事件
        self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 多头开仓成交后，撤消空头委托
        #print(trade.__dict__)
        if self.pos > 0:
            self.cancelOrder(self.shortOrderID)
            if self.buyOrderID in self.orderList:
                self.orderList.remove(self.buyOrderID)
            if self.shortOrderID in self.orderList:
                self.orderList.remove(self.shortOrderID)
            #添加止损设置
            #orderID = self.short(trade.price - self.atrValue*0.5, abs(self.pos), stop=True)
            #self.orderList.append(orderID)

        # 反之同样
        elif self.pos < 0:
            self.cancelOrder(self.buyOrderID)
            if self.buyOrderID in self.orderList:
                self.orderList.remove(self.buyOrderID)
            if self.shortOrderID in self.orderList:
                self.orderList.remove(self.shortOrderID)
            #添加止损设置
            #orderID = self.buy(trade.price + self.atrValue*0.5, abs(self.pos), stop=True)
            #self.orderList.append(orderID)
        
        # 发出状态更新事件
        self.putEvent()
        
    #----------------------------------------------------------------------
    def sendOcoOrder(self, buyPrice, shortPrice, volume):
        """
        发送OCO委托
        
        OCO(One Cancel Other)委托：
        1. 主要用于实现区间突破入场
        2. 包含两个方向相反的停止单
        3. 一个方向的停止单成交后会立即撤消另一个方向的
        """
        # 发送双边的停止单委托，并记录委托号
        self.buyOrderID = self.buy(buyPrice, volume, True)
        self.shortOrderID = self.short(shortPrice, volume, True)
        
        # 将委托号记录到列表中
        self.orderList.append(self.buyOrderID)
        self.orderList.append(self.shortOrderID)


if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from ctaBacktesting import *
    
    #from PyQt4 import QtCore, QtGui
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')
    
    # 设置产品相关参数
    #engine.setSlippage(0.2)     # 股指1跳
    #engine.setRate(0.3/10000)   # 万0.3
    #engine.setSize(300)         # 股指合约大小        
    engine.setSlippage(0.1)
    engine.setRate(5/10000)
    engine.setSize(10) 
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'RB0000')
    
    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(KkStrategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    engine.showBacktestingResult()

    # 跑优化
    setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
    setting.addParameter('kkDev', 0.5, 1., 0.10)    # 增加第一个优化参数kkDev，起始0.5，结束1.5，步进1
    #setting.addParameter('stopLossPercent', 0.1, 1, 0.1)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
    #setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数
    
    # 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    # 测试时还跑着一堆其他的程序，性能仅供参考
    import time    
    start = time.time()
    
    # 运行单进程优化函数，自动输出结果，耗时：359秒
    engine.runOptimization(KkStrategy, setting)            
    
    # 多进程优化，耗时：89秒
    #engine.runParallelOptimization(AtrRsiStrategy, setting)     
    
    print (u'耗时：%s' %(time.time()-start))