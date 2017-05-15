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
sys.path.append('../')
sys.path.append('../../')

from ctaBase import *
from ctaTemplate import CtaTemplate

import talib
import numpy as np
from datetime import datetime
import json

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


########################################################################
class KkStrategy(CtaTemplate):
    """基于King Keltner通道的交易策略"""
    className = 'KkStrategy'
    author = u'renxg'

    # 策略参数
    kkLength = 20           # 计算通道中值的窗口数
    kkDev = 1.0            # 计算通道宽度的偏差
    initDays = 10            # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    trailingPercent = 0.8   # 百分比移动止损
    stopLossPercent = 1.2     # ATR 止损比例

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

    bufferSize = 21                   # 需要缓存的数据的大小
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

    holdTime = 0                       #持仓时间
    holidayTime = 0                     #休息时间
    longStop = 0
    shortStop = 0
    tradeIndex = 0                     #交易编号

    openPrice = 0                   #开仓价
    pnl = 0                         #profit and loss
    

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fixedSize',
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
        
        #self.putEvent()

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

        #打印价差过大信息
        if self.lastBar and abs(bar.open - self.lastBar.close) > 10:
            print(u'价差过大 %s，请检查数据 %s -- %s  %s -- %s' %(bar.open - self.lastBar.close,self.lastBar.datetime,self.lastBar.close , bar.datetime , bar.open))

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

        #重新设置止损点位
        # 持有多头仓位
        if self.pos > 0:
            longStop = self.intraTradeHigh - max(self.atrValue*self.stopLossPercent,abs(self.intraTradeHigh - self.intraTradeLow)*0.2)
            #longStop = self.intraTradeHigh * (1-self.trailingPercent/100)
            # 发出本地止损委托，并且把委托号记录下来，用于后续撤单
            orderID = self.sell(longStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)
            self.longStop = longStop

        # 持有空头仓位
        elif self.pos < 0:
            # 计算空头移动止损
            shortStop = self.intraTradeLow + max(self.atrValue*self.stopLossPercent,abs(self.intraTradeHigh - self.intraTradeLow)*0.2)
            #shortStop = self.intraTradeLow * (1+self.trailingPercent/100)
            orderID = self.cover(shortStop, abs(self.pos), stop=True)
            self.orderList.append(orderID)
            self.shortStop = shortStop

        '''
        如每日平仓，收益曲线还比较好的话，策略就牛了。
        每日平仓在回测时能避免隔夜随机收入，以及换月无效收入。
        '''
        #第日平仓
        # if bar.datetime.time() > datetime.strptime("14:55:00", "%H:%M:%S").time():
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
        if  bar.datetime.time() <= datetime.strptime("10:00:00", "%H:%M:%S").time():
            self.kCircle = 12
        else:
            self.kCircle = 20
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
    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        self.writeCtaLog(u'处理Bar %s' %bar.datetime)

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

        '''
        行情向上时：放低上限，便于开仓； 放低下限，避免做空，
        行情向下时：提高上限，避免开仓； 提高下限，便于开仓
        '''
        real = talib.LINEARREG_SLOPE(self.closeArray, self.kkLength)[-1]
        self.kkMid = talib.MA(self.closeArray, self.kkLength)[-1]
        self.kkUp = self.kkMid + self.atrValue * self.kkDev - real
        self.kkDown = self.kkMid - self.atrValue * self.kkDev - real

        # self.kkMid = talib.MA(self.closeArray,self.kkLength)[-1]
        # self.kkUp = talib.MA(self.highArray,self.kkLength)[-1] - real
        # self.kkDown = talib.MA(self.lowArray,self.kkLength)[-1] - real


        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        """
        Bug fix: 修复刚进场就无亏离场的Bug
        Bar回测结果表明：总的pnl没太大变化；在Tick环境中，可能会有明显的过滤效果，使得Tick运行结果与Bar运行结果相近
        """
        #如果持仓小于5分钟，且盈亏三个点以内，则继续持仓
        if abs(self.pos) > 0 and self.holdTime <= 5 and abs(self.pnl/self.fixedSize/10) <= 3:
            self.putEvent()   
            return

        """
        Bug fix: 第一脚没踏进，第二脚踏不上节奏的问题
        场景：在20分钟间隔的Bar_A，Bar_B两点，价格形态如这样^_^ Bar_A后突破的买点被遗漏，程序到Bar_B后又找到了买点。
             A点后入场比B点后入场多了自动上移止损点位的优势。这时需要对B点后入场进行止损优化
        优化目标1：B点入场，如果发生止损，与A点止损价格相同
        优化目标2：如A点后入已经止损，则B点也不再进入
        """
        #如果空仓且当前价位已在通道外，证明错过了上次开仓时机
        #估出A-B间的高点到当前价的gap
        #将Gap优化到止损点中去
        
        if self.pos == 0 :
            gap = 0
            if bar.close > self.kkUp:
                gap = max(self.highArray[-2:-1]) - bar.close
            elif bar.close < self.kkDown:
                gap = bar.close - min(self.lowArray[-2:-1])

            #Gap > 止损价， 不再开仓。宁愿错过
            if gap > self.atrValue*self.stopLossPercent:
                self.putEvent()
                return
        

        # 当前无仓位，发送OCO开仓委托
        if self.pos == 0 and self.holidayTime <= 0:
            self.sendOcoOrder(self.kkUp, self.kkDown, self.fixedSize)
        # 持有多头仓位
        elif self.pos > 0 and bar.close < self.kkMid:
            orderID = self.sell(bar.close-self.tickAdd, abs(self.pos))
            self.orderList.append(orderID)
        # 持有空头仓位
        elif self.pos < 0 and bar.close > self.kkMid:
            orderID = self.cover(bar.close+self.tickAdd, abs(self.pos))
            self.orderList.append(orderID)   
    
        # 发出状态更新事件
        self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        
        content = json.dumps(trade.__dict__,cls=DateTimeEncoder,indent=4,ensure_ascii=False)
        self.writeCtaLog(u'%s 交易: %s' %(self.tradeIndex, content))

        if abs(self.pos) == 0:
            self.writeCtaLog(u'%s 交易: PNL = %s  HoldTime = %s' %(self.tradeIndex, self.pnl, self.holdTime))

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
        
        #重置 intraTradeHigh intraTradeLow
        if abs(self.pos) > 0:
            '''
            场景：开盘高开后，一路向下，止损。
            问题：止损点位没有因为开盘时的冲高而跟踪向上
            '''
            #bug fix: 实盘下Tick触发交易，最高值值最低值由当前Bar来定。回测时由 lastBar来定
            if self.bar:
                self.intraTradeHigh = self.bar.high
                self.intraTradeLow = self.bar.low
            else:
                self.intraTradeHigh = self.lastBar.high
                self.intraTradeLow = self.lastBar.low

        #Bug fix: 注意,一个单子分次成交后，会回调Ontrader多次
        #完全成交后，重新计数
        if abs(self.pos) == self.fixedSize:
            #重新计数
            self.holdTime = 0
            self.holidayTime = 0
            self.openPrice = trade.price

        #完全平仓后
        elif self.pos == 0:
            self.tradeIndex += 1 #设置下次交易编号
            #设置空仓时间
            self.holidayTime = int(self.holdTime/3)

        # if self.pnl < 10:
        #     print( talib.HT_DCPHASE(self.closeArray)[-1])

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
    engine.setStartDate('20170401',1)
    
    # 设置产品相关参数
    #engine.setSlippage(0.2)     # 股指1跳
    #engine.setRate(0.3/10000)   # 万0.3
    #engine.setSize(300)         # 股指合约大小        
    engine.setSlippage(0.1)
    engine.setRate(1/10000)
    engine.setSize(10) 
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'rb1710')
    
    if True:
        # 在引擎中创建策略对象
        d = {}
        engine.initStrategy(KkStrategy, d)
        
        # 开始跑回测
        engine.runBacktesting()
        
        # 显示回测结果
        engine.showBacktestingResult()

        for log in engine.logList:print(log)

    else:
        # 跑优化
        setting = OptimizationSetting()                 # 新建一个优化任务设置对象
        setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
        #setting.addParameter('kkDev', 0.5, 2.0, 0.10)    # 增加第一个优化参数kkDev，起始0.5，结束1.5，步进1
        #setting.addParameter('stopLossPercent', 2, 3, 0.5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
        #setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数
        #setting.addParameter('kkLength',18,23,1)
        
        # 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
        # 测试时还跑着一堆其他的程序，性能仅供参考
        import time    
        start = time.time()
        
        # 运行单进程优化函数，自动输出结果，耗时：359秒
        #engine.runOptimization(KkStrategy, setting)            
        
        # 多进程优化，耗时：89秒
        engine.runParallelOptimization(KkStrategy, setting)     
        
        print (u'耗时：%s' %(time.time()-start))