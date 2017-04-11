# encoding: UTF-8

'''
CTA模块相关的GUI控制组件
'''


from uiBasicWidget import QtGui, QtCore, BasicCell,QtWidgets
from eventEngine import *
from ctaAlgo.ctaBase import *
from PyQt5 import QtGui
import os,json,time
from language import text

########################################################################################
class ParamWindow2(QtGui.QDialog):

    def __init__(self,name=None, direction=None, vtSymbol=None, CtaEngineManager=None):
        super(ParamWindow2,self).__init__()
        self.resize(350, 480)
        self.ce = CtaEngineManager
        self.saveButton = QtGui.QPushButton(u"保存",self)
        self.cancelButton = QtGui.QPushButton(u"取消",self)
        self.setWindowTitle(u"参数")
        self.vtSymbol = vtSymbol
        self.setting = {}
        self.paramters = {}
        self.strategyName = ""
        self.name = name
        self.firstSave = True
        self.fileName = ""
        if name != "":
            self.fileName = "parameter_" + name + ".json"
        path = os.path.abspath(os.path.dirname(__file__))
        self.fileName = os.path.join(path, self.fileName)     

        self.center()
        self.onInit()
    def onInit(self):
        self.saveButton.resize(50, 27)
        self.cancelButton.resize(50, 27)
        self.saveButton.move(220,450)
        self.cancelButton.move(280,450)
        self.saveButton.clicked.connect(self.saveParameter)
        self.cancelButton.clicked.connect(self.cancel) 
        self.initLabel()
        self.paramters = self.loadParameter()
        if self.fileName != "":
            self.showParam()
    def initLabel(self):
        if self.name == "":
            strategyname_label = QtGui.QLabel(u"策略名",self)
            strategyname_label.setGeometry(QtCore.QRect(25,25,70,22))
            self.strategyname_label = QtGui.QLineEdit(self)
            self.strategyname_label.setGeometry(QtCore.QRect(120,25,70,22))

        self.closeFirst = QtGui.QCheckBox(u'平仓优先',self)
        self.closeFirst.setGeometry(QtCore.QRect(210,25,90,22))

        label_symbol = QtGui.QLabel(u"合约",self)
        label_symbol.setGeometry(QtCore.QRect(25,50,70,22))
        self.lineEdit_label_symbol = QtGui.QLineEdit(self)
        self.lineEdit_label_symbol.setGeometry(QtCore.QRect(120,50,70,22))

        symbolDirection = QtGui.QLabel(u"方向",self)
        symbolDirection.setGeometry(QtCore.QRect(210,50,70,22))
        self.directionCombo = QtGui.QComboBox(self)
        self.directionCombo.addItem("")
        self.directionCombo.addItem("long")
        self.directionCombo.addItem('short')
        self.directionCombo.setGeometry(QtCore.QRect(245,50,50,22))

        label_longBuyUnit = QtGui.QLabel(u"每笔数量",self)
        label_longBuyUnit.setGeometry(QtCore.QRect(25,75,50,22))
        self.lineEdit_label_longBuyUnit = QtGui.QLineEdit(self)
        self.lineEdit_label_longBuyUnit.setGeometry(QtCore.QRect(120,75,70,22))

        maxStpLos = QtGui.QLabel(u'止损', self)
        maxStpLos.setGeometry(QtCore.QRect(210,75,70,22))
        self.lineEdit_label_maxStpLos = QtGui.QLineEdit(self)
        self.lineEdit_label_maxStpLos.setGeometry(QtCore.QRect(245,75,60,22))

        label_longPriceCoe = QtGui.QLabel(u"价格系数",self)
        label_longPriceCoe.setGeometry(QtCore.QRect(25,100,50,22))
        self.lineEdit_label_longPriceCoe = QtGui.QLineEdit(self)
        self.lineEdit_label_longPriceCoe.setGeometry(QtCore.QRect(120,100,70,22))

        label_longPosition = QtGui.QLabel(u"当前持仓量", self)
        label_longPosition.setGeometry(QtCore.QRect(25,125,50,22))
        self.lineEdit_label_longPosition = QtGui.QLineEdit(self)
        self.lineEdit_label_longPosition.setGeometry(QtCore.QRect(120,125,70,22))


        label_stpProfit = QtGui.QLabel(u"止赢", self)
        label_stpProfit.setGeometry(QtCore.QRect(25,150,50,22))
        self.lineEdit_label_stpProfit = QtGui.QLineEdit(self)
        self.lineEdit_label_stpProfit.setGeometry(QtCore.QRect(120,150,70,22))

        label_slippage = QtGui.QLabel(u"滑点", self)
        label_slippage.setGeometry(QtCore.QRect(25,175,50,22))
        self.lineEdit_label_slippage = QtGui.QLineEdit(self)
        self.lineEdit_label_slippage.setGeometry(QtCore.QRect(120,175,70,22))

        label_mail = QtGui.QLabel(u"邮箱", self)
        label_mail.setGeometry(QtCore.QRect(25,200,50,22))
        self.lineEdit_label_mail = QtGui.QLineEdit(self)
        self.lineEdit_label_mail.setGeometry(QtCore.QRect(120,200,200,22))

        label_buyPrice = QtGui.QLabel(u"开仓价差", self)
        label_buyPrice.setGeometry(QtCore.QRect(25,225,50,22))
        self.lineEdit_label_buyPrice = QtGui.QLineEdit(self)
        self.lineEdit_label_buyPrice.setGeometry(QtCore.QRect(120,225,200,22))

        label_stoptime = QtGui.QLabel(u"停止时间", self)
        label_stoptime.setGeometry(QtCore.QRect(25,250,50,22))
        self.lineEdit_label_stoptime = QtGui.QLineEdit(self)
        self.lineEdit_label_stoptime.setGeometry(QtCore.QRect(120,250,200,22))

        self.isFilter = QtGui.QCheckBox(u'当波动大于', self)
        self.isFilter.setGeometry(QtCore.QRect(25,275,150,22))
        self.lineEdit_label_var = QtGui.QLineEdit(self)
        self.lineEdit_label_var.setGeometry(QtCore.QRect(120,275,20,22))
        label_pct = QtGui.QLabel(u'% 时忽略',self)
        label_pct.setGeometry(QtCore.QRect(141,275,80,22))

    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width())/2, (screen.height() - size.height())/2)

    def showParam(self):
        self.lineEdit_label_symbol.setText(self.vtSymbol)
        self.lineEdit_label_longBuyUnit.setText(str(self.paramters["openUnit"]))
        self.lineEdit_label_longPriceCoe.setText(str(self.paramters["PriceCoe"]))
        #self.lineEdit_label_longPosition.setText(str(self.paramters["postoday"][self.vtSymbol]))
        self.lineEdit_label_stpProfit.setText(str(self.paramters["stpProfit"]))
        self.lineEdit_label_slippage.setText(str(self.paramters["slippage"]))
        self.lineEdit_label_stoptime.setText(str(self.paramters["stoptime"]))
        self.lineEdit_label_maxStpLos.setText(str(self.paramters["maxStpLos"]))
        if self.paramters['direction'] =='long':
            self.directionCombo.setCurrentIndex(1)
        else :
            self.directionCombo.setCurrentIndex(2)

        if self.paramters['closeFirst'] == True:
            self.closeFirst.setChecked(True)
        else :
            self.closeFirst.setChecked(False)

        if self.paramters['isFilter'] == True:
            self.isFilter.setChecked(True)
        else :
            self.isFilter.setChecked(False)

        rec = ""
        for x in self.paramters["receivers"]:
            rec += x
            rec += ","
        rec = rec[:-1]
        self.lineEdit_label_mail.setText(rec)
        bp = ""
        for x in self.paramters["buyPrice"]:
            bp += str(x)
            bp += ','
        bp = bp[:-1]
        self.lineEdit_label_buyPrice.setText(bp)
        

    def cancel(self):

        self.showParam()

    def loadParameter(self) :
        param = {}
        if self.fileName == "":
            return param
        with open(self.fileName, 'r') as f:
            param = json.load(f)
        return param

    def saveParameter(self) :
        
        param = {}

        try :
            param["stpProfit"] = int(self.lineEdit_label_stpProfit.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'止赢应该是一个数字！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
            return

        try:    
            param["slippage"] = int(self.lineEdit_label_slippage.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'滑点应该是一个数字！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
            return
        bp = []
        m = ""

        try:
            for x in self.lineEdit_label_buyPrice.text():
                if x == ',':
                    bp.append(int(m))
                    m = ''
                    continue
                m += str(x)
            bp.append(int(m))
        except Exception as e:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'开仓价应是用英文逗号分隔的一组数字！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
            return
        param["buyPrice"] = bp
        pos = {}

        self.vtSymbol = str(self.lineEdit_label_symbol.text())
        if self.lineEdit_label_symbol.text() == '':
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'请正确填写longsymbol！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes) 
            return
        else :
            self.vtSymbol = str(self.lineEdit_label_symbol.text())

        try:
            pos[self.vtSymbol] = int(self.lineEdit_label_longPosition.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'请正确填写symbol的持仓！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes) 
            return

        self.paramters = self.loadParameter()
        param["postoday"] = pos
        if self.closeFirst.isChecked():
            param['closeFirst'] = True
        else :
            param['closeFirst'] = False
        
        if self.isFilter.isChecked():
            param['isFilter'] = True
        else :
            param['isFilter'] = False

        if self.isFilter.isChecked():
            try :
                param["var"] = int(self.lineEdit_label_var.text())
            except ValueError:
                reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'波动率应该是一个数字！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
                return

        try:
            param['maxStpLos'] = int(self.lineEdit_label_maxStpLos.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'止损应该是一个数字！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes) 
            return

        try:
            param['openUnit'] = int(self.lineEdit_label_longBuyUnit.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'请正确填写symbol开仓手数！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes) 
            return


        try:
            param['PriceCoe'] = int(self.lineEdit_label_longPriceCoe.text())
        except ValueError:
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'请正确填写symbol的系数！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes) 
            return
        stpTime = str(self.lineEdit_label_stoptime.text())
        if stpTime == "":
            param['stoptime'] = '9999'
        else :
            param['stoptime'] = stpTime
        rec = []
        m = ""
        for x in str(self.lineEdit_label_mail.text()):
            if x == ',':
                rec.append(m)
                m = ""
                continue
            m += x
        if m != '':
            rec.append(m)
        if str(self.directionCombo.currentText()) == '':
            reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'请选择交易方向！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
            return
        else :
            param['direction'] = str(self.directionCombo.currentText())

        param['receivers'] = rec
        if self.name == "" and self.firstSave:
            if self.strategyname_label.text() == '':
                reply = QtGui.QMessageBox.question(self, u'ERROR!',
                                           u'策略名不能为空！', QtGui.QMessageBox.Yes, QtGui.QMessageBox.Yes)
                return
            else :
                self.strategyName = self.strategyname_label.text()
            self.fileName = "parameter_" + self.strategyName + ".json"
            param['isStop'] = False
            with open(self.fileName, 'a') as f:
                f.write("{}")
                f.close()
        param['isStop'] = False
        self.paramters = param
        d1 = json.dumps(param,sort_keys=True,indent=4)
        with open(self.fileName, "w") as f:
            f.write(d1)
            f.close()
        self.setting['name'] = str(self.strategyName)
        self.setting['className'] = 'theGirdTrading'
        self.setting['vtSymbol'] = self.vtSymbol

        if self.name == "" and self.firstSave :
            self.ce.ctaEngine.addStrategy(self.setting,self.strategyName)
            self.firstSave = False

########################################################################
class CtaValueMonitor(QtWidgets.QTableWidget):
    """参数监控"""

    #----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(CtaValueMonitor, self).__init__(parent)
        
        self.keyCellDict = {}
        self.data = None
        self.inited = False
        
        self.initUi()
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setRowCount(1)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)
        
        self.setMaximumHeight(self.sizeHint().height())
        
    #----------------------------------------------------------------------
    def updateData(self, data):
        """更新数据"""
        if not self.inited:
            self.setColumnCount(len(data))
            self.setHorizontalHeaderLabels(data.keys())
            
            col = 0
            for k, v in data.items():
                cell = QtWidgets.QTableWidgetItem(str(v))
                self.keyCellDict[k] = cell
                self.setItem(0, col, cell)
                col += 1
            
            self.inited = True
        else:
            for k, v in data.items():
                cell = self.keyCellDict[k]
                cell.setText(str(v))


########################################################################
class CtaStrategyManager(QtWidgets.QGroupBox):
    """策略管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, eventEngine, name, parent=None):
        """Constructor"""
        super(CtaStrategyManager, self).__init__(parent)
        
        self.ctaEngine = ctaEngine
        self.eventEngine = eventEngine
        self.name = name
        
        self.initUi()
        self.updateMonitor()
        self.registerEvent()
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setTitle(self.name)
        
        self.paramMonitor = CtaValueMonitor(self)
        self.varMonitor = CtaValueMonitor(self)
        
        height = 60
        self.paramMonitor.setFixedHeight(height)
        self.varMonitor.setFixedHeight(height)
        
        buttonInit = QtWidgets.QPushButton(u'初始化')
        buttonStart = QtWidgets.QPushButton(u'启动')
        buttonStop = QtWidgets.QPushButton(u'停止')
        buttonBuy = QtWidgets.QPushButton(u'开多')
        buttonSell = QtWidgets.QPushButton(u'平多')
        buttonShort = QtWidgets.QPushButton(u'开空')
        buttonCover= QtWidgets.QPushButton(u'平空')

        buttonParam = QtWidgets.QPushButton(u'参数')

        buttonInit.clicked.connect(self.init)
        buttonStart.clicked.connect(self.start)
        buttonStop.clicked.connect(self.stop)
        buttonBuy.clicked.connect(self.buy)
        buttonSell.clicked.connect(self.sell)

        buttonShort.clicked.connect(self.short)
        buttonCover.clicked.connect(self.cover)

        buttonParam.clicked.connect(self.paramSetting)

        
        hbox1 = QtWidgets.QHBoxLayout()     
        hbox1.addWidget(buttonInit)
        hbox1.addWidget(buttonStart)
        hbox1.addWidget(buttonStop)
        hbox1.addWidget(buttonBuy)
        hbox1.addWidget(buttonSell)
    
        hbox1.addWidget(buttonShort)
        hbox1.addWidget(buttonCover)

        hbox1.addWidget(buttonParam)
        hbox1.addStretch()
        
        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(self.paramMonitor)
        
        hbox3 = QtWidgets.QHBoxLayout()
        hbox3.addWidget(self.varMonitor)
        
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)

        self.setLayout(vbox)
        
    #----------------------------------------------------------------------
    def updateMonitor(self, event=None):
        """显示策略最新状态"""
        paramDict = self.ctaEngine.getStrategyParam(self.name)
        if paramDict:
            self.paramMonitor.updateData(paramDict)
            
        varDict = self.ctaEngine.getStrategyVar(self.name)
        if varDict:
            self.varMonitor.updateData(varDict)        
            
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateMonitor)
        self.eventEngine.register(EVENT_CTA_STRATEGY+self.name, self.signal.emit)
    
    #----------------------------------------------------------------------
    def init(self):
        """初始化策略"""
        self.ctaEngine.initStrategy(self.name)
    
    #----------------------------------------------------------------------
    def start(self):
        """启动策略"""
        self.ctaEngine.startStrategy(self.name)
        
    #----------------------------------------------------------------------
    def stop(self):
        """停止策略"""
        self.ctaEngine.stopStrategy(self.name)

    #----------------------------------------------------------------------
    def buy(self):
        """手动开多"""
        self.ctaEngine.tradeStrategy(self.name,CTAORDER_BUY)
        self.ctaEngine.writeCtaLog( u'手动开多' + self.name) 

    #----------------------------------------------------------------------
    def sell(self):
        """手动平多"""
        self.ctaEngine.tradeStrategy(self.name,CTAORDER_SELL)
        self.ctaEngine.writeCtaLog( u'手动平多' + self.name) 

    #----------------------------------------------------------------------
    def short(self):
        """手动开空"""
        self.ctaEngine.tradeStrategy(self.name,CTAORDER_SHORT)
        self.ctaEngine.writeCtaLog( u'手动开空' + self.name) 

    def cover(self):
        """手动平空"""
        self.ctaEngine.tradeStrategy(self.name,CTAORDER_COVER)
        self.ctaEngine.writeCtaLog( u'手动平空' + self.name) 

    def paramSetting(self):
        """设置参数窗口"""
        self.paramWindow = ParamWindow2(self.name)
        self.paramWindow.paramters = self.paramWindow.loadParameter()
        self.paramWindow.showParam()
        self.paramWindow.show()

###################################################˝#####################
class CtaEngineManager(QtWidgets.QWidget):
    """CTA引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, eventEngine, parent=None):
        """Constructor"""
        super(CtaEngineManager, self).__init__(parent)
        
        self.ctaEngine = ctaEngine
        self.eventEngine = eventEngine
        
        self.strategyLoaded = False
        
        self.initUi()
        self.registerEvent()
        
        # 记录日志
        self.ctaEngine.writeCtaLog(u'CTA引擎启动成功')        
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'CTA策略')
        
        # 按钮
        loadButton = QtWidgets.QPushButton(u'加载策略')
        initAllButton = QtWidgets.QPushButton(u'全部初始化')
        startAllButton = QtWidgets.QPushButton(u'全部启动')
        stopAllButton = QtWidgets.QPushButton(u'全部停止')
        savePositionButton = QtWidgets.QPushButton(u'保存持仓')
        
        loadButton.clicked.connect(self.load)
        initAllButton.clicked.connect(self.initAll)
        startAllButton.clicked.connect(self.startAll)
        stopAllButton.clicked.connect(self.stopAll)
        savePositionButton.clicked.connect(self.ctaEngine.savePosition)
        
        # 滚动区域，放置所有的CtaStrategyManager
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        
        # CTA组件的日志监控
        self.ctaLogMonitor = QtWidgets.QTextEdit()
        self.ctaLogMonitor.setReadOnly(True)
        self.ctaLogMonitor.setMaximumHeight(200)
        
        # 设置布局
        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(loadButton)
        hbox2.addWidget(initAllButton)
        hbox2.addWidget(startAllButton)
        hbox2.addWidget(stopAllButton)
        hbox2.addWidget(savePositionButton)
        hbox2.addStretch()
        
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox2)
        vbox.addWidget(self.scrollArea)
        vbox.addWidget(self.ctaLogMonitor)
        self.setLayout(vbox)
        
    #----------------------------------------------------------------------
    def initStrategyManager(self):
        """初始化策略管理组件界面"""        
        w = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout()
        
        for name in self.ctaEngine.strategyDict.keys():
            strategyManager = CtaStrategyManager(self.ctaEngine, self.eventEngine, name)
            vbox.addWidget(strategyManager)
        
        vbox.addStretch()
        
        w.setLayout(vbox)
        self.scrollArea.setWidget(w)   
        
    #----------------------------------------------------------------------
    def initAll(self):
        """全部初始化"""
        for name in self.ctaEngine.strategyDict.keys():
            self.ctaEngine.initStrategy(name)    
            
    #----------------------------------------------------------------------
    def startAll(self):
        """全部启动"""
        for name in self.ctaEngine.strategyDict.keys():
            self.ctaEngine.startStrategy(name)
            
    #----------------------------------------------------------------------
    def stopAll(self):
        """全部停止"""
        for name in self.ctaEngine.strategyDict.keys():
            self.ctaEngine.stopStrategy(name)
            
    #----------------------------------------------------------------------
    def load(self):
        """加载策略"""
        if not self.strategyLoaded:
            self.ctaEngine.loadSetting()
            self.initStrategyManager()
            self.strategyLoaded = True
            self.ctaEngine.writeCtaLog(u'策略加载成功')
        
    #----------------------------------------------------------------------
    def updateCtaLog(self, event):
        """更新CTA相关日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.ctaLogMonitor.append(content)
    
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateCtaLog)
        self.eventEngine.register(EVENT_CTA_LOG, self.signal.emit)
        
    #----------------------------------------------------------------------
    def closeEvent(self, event):
        """关闭窗口时的事件"""
        reply = QtGui.QMessageBox.question(self, text.SAVE_POSITION_DATA,
                                           text.SAVE_POSITION_QUESTION, QtGui.QMessageBox.Yes | 
                                           QtGui.QMessageBox.No, QtGui.QMessageBox.No)
    
        if reply == QtGui.QMessageBox.Yes: 
            self.ctaEngine.savePosition()
            
        event.accept()
    
    
    



    
    