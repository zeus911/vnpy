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
from datetime import datetime

########################################################################
class KkStrategy(CtaTemplate):
    """基于King Keltner通道的交易策略"""
    className = 'KkStrategy'
    author = u'renxg'

    # 策略参数
    # 策略参数
    atrLength = 22          # 计算ATR指标的窗口数   
    atrMaLength = 10        # 计算ATR均线的窗口数
    rsiLength = 5           # 计算RSI的窗口数
    rsiEntry = 16           # RSI的开仓信号
    trailingPercent = 0.8   # 百分比移动止损
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟

    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrCount = 0                        # 目前已经缓存了的ATR的计数
    atrArray = np.zeros(bufferSize)     # ATR指标的数组
    atrValue = 0                        # 最新的ATR指标数值
    atrMa = 0                           # ATR移动平均的数值

    rsiValue = 0                        # RSI指标的数值
    rsiBuy = 0                          # RSI买开阈值
    rsiSell = 0                         # RSI卖开阈值
    intraTradeHigh = 0                  # 移动止损用的持仓期内最高价
    intraTradeLow = 0                   # 移动止损用的持仓期内最低价
    

    # 策略变量
    tickAdd = 1             # 委托时相对基准价格的超价
    lastTick = None         # 最新tick数据
    lastBar = None          # 最新bar数据
    lastBarClose = 0
    lastPrice = 0
    intraTradeHigh = 0
    intraTradeLow = 0

    bar = None                  # 1分钟K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟
    fiveBar = None              # 1分钟K线对象

    # bufferSize = 21                   # 需要缓存的数据的大小
    # bufferCount = 0                     # 目前已经缓存了的数据的计数
    # highArray = np.zeros(bufferSize)    # K线最高价的数组
    # lowArray = np.zeros(bufferSize)     # K线最低价的数组
    # closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    atrValue = 0                        # 最新的ATR指标数值
    kkMid = 0                           # KK通道中轨
    kkUp = 0                            # KK通道上轨
    kkDown = 0                          # KK通道下轨

    buyOrderID = None              # OCO委托买入开仓的委托号
    shortOrderID = None            # OCO委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    holdTime = 0                       #持仓时间
    holidayTime = 0                     #休息时间
    longStop = 0
    shortStop = 0
    tradeIndex = 0                     #交易编号

    openPrice = 0                   #开仓价
    pnl = 0                         #profit and loss

    kCount = 0
    

    """
    "infoArray" 字典是用来储存辅助品种信息的, 可以是同品种的不同分钟k线, 也可以是不同品种的价格。

    调用的方法:
    self.infoArray["数据库名 + 空格 + collection名"]["close"]
    self.infoArray["数据库名 + 空格 + collection名"]["high"]
    self.infoArray["数据库名 + 空格 + collection名"]["low"]
    """
    infoArray = {}
    initInfobar = {}

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'kkLength',
                 'kkDev']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue',

               'kkUp',
               'kkMid',
               'kkDown',

               'lastPrice',
               'pnl',
               
               'longStop',
               'shortStop',
                'holdTime',
               'holidayTime'
               ]  

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
        #sys.stdout.write(".")
        #sys.stdout.flush()  
        self.lastTick = tick
        self.lastPrice = tick.lastPrice

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
        
        self.putEvent()

    #-------------------------------------------------------------------------------------------------------
    def isTradingTime(self,time,timeRanges=[
        (datetime.strptime("09:00:00", "%H:%M:%S").time(), datetime.strptime("10:15:00", "%H:%M:%S").time()),
        (datetime.strptime("10:30:00", "%H:%M:%S").time(), datetime.strptime("11:30:00", "%H:%M:%S").time()),
        (datetime.strptime("13:30:00", "%H:%M:%S").time(), datetime.strptime("15:00:00", "%H:%M:%S").time()),
        (datetime.strptime("21:00:00", "%H:%M:%S").time(), datetime.strptime("23:00:00", "%H:%M:%S").time())
         ]):

        for tr in timeRanges:
            if tr[0] <= time <= tr[1]:
                return True
        return False
        pass

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        #date check
        if not self.isTradingTime(bar.datetime.time()):
            return

        #更新last Bar
        self.lastBar = bar
        self.lastBarClose = bar.close

        #计算持仓时间、休息时间
        if self.trading:
            if abs(self.pos)>0 :
                self.pnl = (self.lastBarClose - self.openPrice)*self.pos*10
                self.holdTime += 1
            else:
                self.holidayTime -= 1

        if abs(self.pos) > 0:
            # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
            for orderID in self.orderList:
                self.cancelOrder(orderID)
            self.orderList = []

            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

        # if self.pos > 0 and bar.close < self.kkMid:
        #     orderID = self.sell(bar.close-self.tickAdd, abs(self.pos))
        #     self.orderList.append(orderID)
        # # 持有空头仓位
        # elif self.pos < 0 and bar.close > self.kkMid:
        #     orderID = self.cover(bar.close+self.tickAdd, abs(self.pos))
        #     self.orderList.append(orderID)  

        #重新设置止损点位
        # 持有多头仓位
        # if self.pos > 0:
        #     longStop = self.intraTradeHigh - max(self.atrValue*self.stopLossPercent,abs(self.intraTradeHigh - self.intraTradeLow)*0.2)
        #     # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
        #     orderID = self.sell(longStop, abs(self.pos), stop=True)
        #     self.orderList.append(orderID)
        #     self.longStop = longStop

        # # 持有空头仓位
        # elif self.pos < 0:
        #     # 计算空头移动止损
        #     shortStop = self.intraTradeLow + max(self.atrValue*self.stopLossPercent,abs(self.intraTradeHigh - self.intraTradeLow)*0.2)
        #     orderID = self.cover(shortStop, abs(self.pos), stop=True)
        #     self.orderList.append(orderID)
        #     self.shortStop = shortStop

        # if bar.datetime.time() > datetime.strptime("22:55:00", "%H:%M:%S").time():
        #     #平仓
        #     for orderID in self.orderList:
        #         self.cancelOrder(orderID)
        #         self.orderList = []

        #     if self.pos > 0:
        #         orderID = self.sell(bar.close -5, abs(self.pos))
        #         self.orderList.append(orderID)
        #     if self.pos < 0:
        #         orderID = self.cover(bar.close + 5, abs(self.pos))
        #         self.orderList.append(orderID)


       # 加大开盘时的重要度
       # 加大开盘时的重要度
        if  bar.datetime.time() <= datetime.strptime("10:00:00", "%H:%M:%S").time():
            self.kCircle = 20
        else:
            self.kCircle = 30
        if bar.datetime.minute % self.kCircle == 0:
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


        # 保存K线数据
        self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize - 1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize - 1] = self.lowArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low

        # 若读取的缓存数据不足, 不考虑交易
        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return

        if len(self.infoArray["TestData @GC_30M"]["close"]) < self.rsiLength:
            return

        # 计算指标数值

        # 计算不同时间下的ATR数值

        # Only trading when information bar changes
        # 只有在30min或者1d K线更新后才可以交易
        TradeOn = False
        if any([i is not None for i in self.infoArray["TestData @GC_30M"].values()]):

            TradeOn = True
            self.scaledAtrValue1M = talib.ATR(self.highArray,
                                       self.lowArray,
                                       self.closeArray,
                                       self.atrLength)[-1] * (25) ** (0.5)
            self.atrValue30M = talib.abstract.ATR(self.infoArray["TestData @GC_30M"])[-1]
            self.rsiValue = talib.abstract.RSI(self.infoArray["TestData @GC_30M"], self.rsiLength)[-1]

            #print(self.scaledAtrValue1M, self.atrValue30M, self.rsiValue)

        self.atrCount += 1
        if self.atrCount < self.bufferSize:
            return

        # 判断是否要进行交易

        # 当前无仓位
        if (self.pos == 0 and TradeOn == True):
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low

            # 1Min调整后ATR大于30MinATR
            # 即处于趋势的概率较大，适合CTA开仓
            if self.atrValue30M < self.scaledAtrValue1M:
                # 使用RSI指标的趋势行情时，会在超买超卖区钝化特征，作为开仓信号
                if self.rsiValue > self.rsiBuy:
                    # 这里为了保证成交，选择超价5个整指数点下单
                    self.buy(bar.close+5, 1)

                elif self.rsiValue < self.rsiSell:
                    self.short(bar.close-5, 1)

                # 下单后, 在下一个30Min K线之前不交易
                TradeOn = False

        # 持有多头仓位
        elif self.pos > 0:
            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            # 计算多头移动止损
            longStop = self.intraTradeHigh * (1 - self.trailingPercent / 100)
            # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
            orderID = self.sell(longStop, 1, stop=True)
            self.orderList.append(orderID)

        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.intraTradeHigh = bar.high

            shortStop = self.intraTradeLow * (1 + self.trailingPercent / 100)
            orderID = self.cover(shortStop, 1, stop=True)
            self.orderList.append(orderID)

    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        self.writeCtaLog(u'处理Bar %s' %bar.datetime)

        infobar = {}
        infobar["TestData @GC_30M"] = bar

        for name in infobar:
    
            data = infobar[name]

            # Construct empty array
            if len(self.infoArray) < len(infobar) :
                self.infoArray[name] = {
                    "close": np.zeros(self.bufferSize),
                    "high": np.zeros(self.bufferSize),
                    "low": np.zeros(self.bufferSize)
                }

            if data is None:
                pass

            else:
                self.infoArray[name]["close"][0:self.bufferSize - 1] = \
                    self.infoArray[name]["close"][1:self.bufferSize]
                self.infoArray[name]["high"][0:self.bufferSize - 1] = \
                    self.infoArray[name]["high"][1:self.bufferSize]
                self.infoArray[name]["low"][0:self.bufferSize - 1] = \
                    self.infoArray[name]["low"][1:self.bufferSize]

                self.infoArray[name]["close"][-1] = data.close
                self.infoArray[name]["high"][-1] = data.high
                self.infoArray[name]["low"][-1] = data.low

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 多头开仓成交后，撤消空头委托
        if self.pos > 0:
            self.cancelOrder(self.shortOrderID)
            if self.buyOrderID in self.orderList:
                self.orderList.remove(self.buyOrderID)
            if self.shortOrderID in self.orderList:
                self.orderList.remove(self.shortOrderID)

        # 反之同样
        elif self.pos < 0:
            self.cancelOrder(self.buyOrderID)
            if self.buyOrderID in self.orderList:
                self.orderList.remove(self.buyOrderID)
            if self.shortOrderID in self.orderList:
                self.orderList.remove(self.shortOrderID)
        
        #重置
        if abs(self.pos) > 0:
            self.intraTradeHigh = trade.price
            self.intraTradeLow = trade.price

        
        if abs(self.pos) > 0:
            print("--------------",self.tradeIndex,"-----------------------")
            print(trade.__dict__)
            print(trade.direction,trade.offset,trade.price,trade.tradeTime)

            #重新计数
            self.holdTime = 0
            self.holidayTime = 0
            self.openPrice = trade.price
        else:
            print(trade.direction,trade.offset,trade.price,trade.tradeTime)
            print('pnl =', self.pnl, "    Hold minutes: ", self.holdTime,"    ATR ", self.atrValue)

            self.holidayTime = int(self.holdTime/3)
            # 30 minute punishment for short time holding
            if self.holdTime < 60:
                self.holidayTime += 30
            if self.pnl < 0:
                self.holidayTime += 30

            self.tradeIndex += 1
            
        
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
        


        

    #----------------------------------------------------------------------
    def onManualTrade(self, orderType):
        """手动交易（必须由用户继承实现）
        手动交易注意事项：
        开仓：开仓方式应与本策略规则相同，否则开出的仓位可能会很快被策略平掉（通道内开仓后，策略会将通道内的仓位平掉）
             可用于加仓
        平仓：相当于止盈      
        """
        if not self.trading:
            self.writeCtaLog(u'非交易状态')
            return

        if self.bar == None and self.lastTick == None:
            self.writeCtaLog(u'策略没有当前价格信息')
            return

        # 先撤销之前的委托
        for vtOrderID in self.orderList:
            self.cancelOrder(vtOrderID)
        self.orderList = []
        
        # 如果目标仓位和实际仓位一致，则不进行任何操作
        posChange = 0
        if orderType == CTAORDER_BUY or orderType == CTAORDER_COVER:
            posChange = self.fixedSize
        else:
            posChange = -self.fixedSize

        if not posChange:
            return
        
        # 确定委托基准价格，有tick数据时优先使用，否则使用bar
        longPrice = 0
        shortPrice = 0
        
        if self.lastTick:
            if posChange > 0:
                longPrice = self.lastTick.askPrice1 + self.tickAdd
            else:
                shortPrice = self.lastTick.bidPrice1 - self.tickAdd
        else:
            if posChange > 0:
                longPrice = self.lastBar.close + self.tickAdd
            else:
                shortPrice = self.lastBar.close - self.tickAdd
        
        # 回测模式下，采用合并平仓和反向开仓委托的方式
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            if posChange > 0:
                vtOrderID = self.buy(longPrice, abs(posChange))
            else:
                vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)
        
        # 实盘模式下，首先确保之前的委托都已经结束（全成、撤销）
        # 然后先发平仓委托，等待成交后，再发送新的开仓委托
        else:
            # 检查之前委托都已结束
            if self.orderList:
                return
            
            # 买入
            if posChange > 0:
                if self.pos < 0:
                    vtOrderID = self.cover(longPrice, abs(self.pos))
                else:
                    vtOrderID = self.buy(longPrice, abs(posChange))
            # 卖出
            else:
                if self.pos > 0:
                    vtOrderID = self.sell(shortPrice, abs(self.pos))
                else:
                    vtOrderID = self.short(shortPrice, abs(posChange))
            self.orderList.append(vtOrderID)


        # 发出状态更新事件
        self.putEvent()



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
    engine.setStartDate('20160402',1)
    
    # 设置产品相关参数
    #engine.setSlippage(0.2)     # 股指1跳
    #engine.setRate(0.3/10000)   # 万0.3
    #engine.setSize(300)         # 股指合约大小        
    engine.setSlippage(0.1)
    engine.setRate(1/10000)
    engine.setSize(10) 
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'rb0000')
    
    if True:
        # 在引擎中创建策略对象
        d = {}
        engine.initStrategy(KkStrategy, d)
        
        # 开始跑回测
        engine.runBacktesting()
        
        # 显示回测结果
        engine.showBacktestingResult()
    else:
        # 跑优化
        setting = OptimizationSetting()                 # 新建一个优化任务设置对象
        setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
        #setting.addParameter('kkDev', 0.5, 2.0, 0.10)    # 增加第一个优化参数kkDev，起始0.5，结束1.5，步进1
        #setting.addParameter('stopLossPercent', 2, 3, 0.5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
        #setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数
        setting.addParameter('kkLength',18,23,1)
        
        # 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
        # 测试时还跑着一堆其他的程序，性能仅供参考
        import time    
        start = time.time()
        
        # 运行单进程优化函数，自动输出结果，耗时：359秒
        #engine.runOptimization(KkStrategy, setting)            
        
        # 多进程优化，耗时：89秒
        engine.runParallelOptimization(KkStrategy, setting)     
        
        print (u'耗时：%s' %(time.time()-start))