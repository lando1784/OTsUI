from GUIs.OTsUI_MainGUI import *
from pyqtgraph import setConfigOption
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QSlider, QDial, QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit, QComboBox, QPushButton
from PyQt5.QtCore import QThread
import configparser as cfg
import numpy as np
from scipy.signal import welch
from os import sep
from os.path import splitext
from GUIs.OTsUI_configUI_Engine import configDial

try:
    import epz as tempEpz
    import inspect
    _,_,keys,_ = inspect.getargspec(tempEpz.CMD.__init__())
    print(keys)
    if 'tag' not in keys:
        import libs.epz as tempEpz
    epz = tempEpz
except:
    import libs.epz as epz

from libs.epzInterpreter import Interpreter
from libs.usefulVar import pens
from time import sleep

setConfigOption('background', 'w')
setConfigOption('foreground', (100,100,100))

INCR = 0.01
DEC = 1
CHUNK = 512
NOTLEN = 1000


class OTsUI(QMainWindow,Ui_OTsUI_main):

    def __init__(self, parent=None):

        super(OTsUI, self).__init__(parent)
        self.setupUi(self)
        self.cfgFile = QFileDialog.getOpenFileName(self,'Select a configuration file',filter='Ini (*.ini)')[0]
        if self.cfgFile == '':
            self.cfgFile = 'config/defaultCfg.ini'
        self.kx = 1
        self.ky = 1
        self.kz = 1
        self.sx = 1
        self.sy = 1
        self.sz = 1
        self.logDir = ''
        self.dataDir = ''
        self.parDir = ''
        self.xData = None

        self.powSpecConnected = False
        self.signalConnected = False

        self.trapHomePos = [0.0,0.0,0.0]

        # epz objects

        self.otsuiEnv = epz.Environment()

        self.padBtnFuncDict = {self.yPlusTrapBtn: [self.incrementTrapY,0],
                               self.xPlusTrapBtn: [self.incrementTrapX,0],
                               self.zPlusTrapBtn: [self.incrementTrapZ,0],
                               self.yMinusTrapBtn: [self.decrementTrapY,1],
                               self.xMinusTrapBtn: [self.decrementTrapX,1],
                               self.zMinusTrapBtn: [self.decrementTrapZ,1]}

        #######################################################################

        # Plot items
        
        self.trapPadPlot.plotItem.showAxis('top', show=True)
        self.trapPadPlot.plotItem.showAxis('right', show=True)
        self.trapPadPlot.plotItem.showGrid(True, True, 1)
        self.trapPadPlot.setMaximumSize(QtCore.QSize(180, 180))
        
        self.trapPosXYPlot.plotItem.showAxis('top', show=True)
        self.trapPosXYPlot.plotItem.showAxis('right', show=True)
        self.trapPosXYPlot.plotItem.showGrid(True, True, 1)
        self.trapPosXYPlot.setEnabled(True)
        
        #######################################################################
        
        # Set num controls

        self.parDict = self.getParamsDict()
        self.applyConfig()
            
        #################################################################################

        self.numConnections()
        self.cmbBoxConnections()
        self.pathConnections()
        self.actionConnections()
        self.buttonConnections()
        self.genericConnections()


    def createConfigDict(self,parser):
        paramsDict = {}
        secs = parser.sections()
        for s in secs:
            paramsDict[s] = {}
            options = parser.options(s)
            for o in options:
                paramsDict[s][o] = parser.get(s,o)

        return paramsDict


    def applyConfig(self):

        parser = cfg.ConfigParser()
        parser.read(self.cfgFile)
        configDict = self.createConfigDict(parser)

        xvM = float(configDict['XAXIS']['vgalvmax'])
        xvm = float(configDict['XAXIS']['vgalvmin'])
        xM = float(configDict['XAXIS']['nmgalvmax'])
        xm = float(configDict['XAXIS']['nmgalvmin'])
        yvM = float(configDict['YAXIS']['vgalvmax'])
        yvm = float(configDict['YAXIS']['vgalvmin'])
        yM = float(configDict['YAXIS']['nmgalvmax'])
        ym = float(configDict['YAXIS']['nmgalvmin'])
        zvM = float(configDict['ZAXIS']['vgalvmax'])
        zvm = float(configDict['ZAXIS']['vgalvmin'])
        zM = float(configDict['ZAXIS']['nmgalvmax'])
        zm = float(configDict['ZAXIS']['nmgalvmin'])

        self.xVToNm = lambda x: ((x-xvm)/(xvM-xvm))*(xM-xm)+xm
        self.xNmToV = lambda x: ((x-xm)/(xM-xm))*(xvM-xvm)+xvm
        self.yVToNm = lambda x: ((x-yvm)/(yvM-yvm))*(yM-ym)+ym
        self.yNmToV = lambda x: ((x-ym)/(yM-ym))*(yvM-yvm)+yvm
        self.zVToNm = lambda x: ((x-zvm)/(zvM-zvm))*(zM-zm)+zm
        self.zNmToV = lambda x: ((x-zm)/(zM-zm))*(zvM-zvm)+zvm


        self.xVToNmRel = lambda x: (x/(configDict['XAXIS']['vgalvmax']-configDict['XAXIS']['vgalvmin']))*(configDict['XAXIS']['nmgalvmax']-configDict['XAXIS']['nmgalvmin'])
        self.xNmToVRel = lambda x: (x/(configDict['XAXIS']['nmgalvmax']-configDict['XAXIS']['nmgalvmin']))*(configDict['XAXIS']['vgalvmax']-configDict['XAXIS']['vgalvmin'])
        self.yVToNmRel = lambda x: (x/(configDict['YAXIS']['vgalvmax']-configDict['YAXIS']['vgalvmin']))*(configDict['YAXIS']['nmgalvmax']-configDict['YAXIS']['nmgalvmin'])
        self.yNmToVRel = lambda x: (x/(configDict['YAXIS']['nmgalvmax']-configDict['YAXIS']['nmgalvmin']))*(configDict['YAXIS']['vgalvmax']-configDict['YAXIS']['vgalvmin'])
        self.zVToNmRel = lambda x: (x/(configDict['ZAXIS']['vgalvmax']-configDict['ZAXIS']['vgalvmin']))*(configDict['ZAXIS']['nmgalvmax']-configDict['ZAXIS']['nmgalvmin'])
        self.zNmToVRel = lambda x: (x/(configDict['ZAXIS']['nmgalvmax']-configDict['ZAXIS']['nmgalvmin']))*(configDict['ZAXIS']['vgalvmax']-configDict['ZAXIS']['vgalvmin'])


        configGroupDictX = {'nmgalvmax': [[self.activeCalXAmplNumDbl], ['nmgalvmin']],
                            'qpdmax': [[self.stdExpXSetPntNumDbl,
                                        self.customExpXAmplNumDbl], ['qpdmin']],
                            'pmax': [[self.xyPNumDbl, self.xyPDial], ['0']],
                            'imax': [[self.xyINumDbl, self.xyIDial], ['0']],
                            'speedmax': [[self.xSpeedTrapPadNumDbl,
                                          self.xSpeedTrapPadSlider], ['INCR']]}
        configGroupDictY = {'nmgalvmax': [[self.activeCalYAmplNumDbl], ['nmgalvmin']],
                            'qpdmax': [[self.stdExpYSetPntNumDbl,
                                        self.customExpYAmplNumDbl], ['qpdmin']],
                            'pmax': [[self.xyPNumDbl, self.xyPDial], ['0']],
                            'imax': [[self.xyINumDbl, self.xyIDial], ['0']],
                            'speedmax': [[self.ySpeedTrapPadNumDbl,
                                          self.ySpeedTrapPadSlider], ['INCR']]}
        configGroupDictZ = {'nmgalvmax': [[self.activeCalZAmplNumDbl], ['nmgalvmin']],
                            'qpdmax': [[self.stdExpZSetPntNumDbl,
                                        self.customExpZAmplNumDbl], ['qpdmin']],
                            'pmax': [[self.zPNumDbl, self.zPDial], ['0']],
                            'imax': [[self.zINumDbl, self.zIDial], ['0']], }
        otherGroupDict = {'stimmaxfreq': [[self.activeCalXFreqNumDbl,self.activeCalYFreqNumDbl,
                                           self.activeCalZFreqNumDbl],['0']]}
        configNumDict = {'XAXIS':configGroupDictX, 'YAXIS':configGroupDictY,
                         'ZAXIS':configGroupDictZ, 'OTHER':otherGroupDict}

        self.ipAddLine.setText(configDict['CONN']['ipaddr'])
        self.subPortLine.setText(configDict['CONN']['subport'])
        self.pubPortLine.setText(configDict['CONN']['pubport'])
        self.xDevName = configDict['XAXIS']['devname']
        self.yDevName = configDict['YAXIS']['devname']
        self.zDevName = configDict['ZAXIS']['devname']
        self.otsuiEnv.epserver = self.ipAddLine.text()
        self.otsuiEnv.pubport = self.pubPortLine.text()
        self.otsuiEnv.subport = self.subPortLine.text()
        self.otsuiEnv.device = self.xDevName

        for s in configNumDict.keys():
            for o in configNumDict[s].keys():
                for el in configNumDict[s][o][0]:
                    scale = (1/INCR) if (type(el) == QDial or type(el) == QSlider) else 1
                    max = float(configDict[s][o])
                    minKey = configNumDict[s][o][1][0]
                    min = float(configDict[s][minKey]) if (minKey != '0' and minKey != 'INCR') else eval(minKey)
                    el.setMaximum(max*scale)
                    el.setMinimum(min*scale)
                    el.setSingleStep(INCR*scale)


    def epzConnect(self):

        self.xInterpreter = Interpreter(self.otsuiEnv,self.xDevName)
        self.yInterpreter = Interpreter(self.otsuiEnv,self.yDevName)
        self.zInterpreter = Interpreter(self.otsuiEnv,self.zDevName)

        self.xData = epz.QtDATA(self.otsuiEnv,self.xDevName)
        self.xData.decimate = DEC
        self.xData.chunk = CHUNK
        self.xData.notifyLength = NOTLEN
        self.xData.notify = True
        self.xData.yDataReceived.connect(self.trapTrack)
        self.xData.zDataReceived.connect(self.qpdTrack)
        self.yData = epz.QtDATA(self.otsuiEnv,self.yDevName)
        self.yData.decimate = DEC
        self.yData.chunk = CHUNK
        self.yData.notifyLength = NOTLEN
        self.yData.notify = True
        self.yData.yDataReceived.connect(self.trapTrack)
        self.yData.zDataReceived.connect(self.qpdTrack)
        self.zData = epz.QtDATA(self.otsuiEnv,self.zDevName)
        self.zData.decimate = DEC
        self.zData.chunk = CHUNK
        self.zData.notifyLength = NOTLEN
        self.zData.notify = True
        self.zData.yDataReceived.connect(self.trapTrack)
        self.zData.zDataReceived.connect(self.qpdTrack)

        sleep(0.2)

        self.xInterpreter.circulaBufferOn()
        self.yInterpreter.circulaBufferOn()
        self.zInterpreter.circulaBufferOn()
        self.xInterpreter.startDev()
        self.yInterpreter.startDev()
        self.zInterpreter.startDev()

        self.xData.start()
        self.yData.start()
        self.zData.start()

        self.linkPlotToData(self.plotTabs.currentIndex()==0)


    def changePlotTab(self):
        if self.xData != None:
            self.linkPlotToData(self.plotTabs.currentIndex()==0)


    def linkPlotToData(self, goSignal):

        signals = [self.xData,self.yData,self.zData,self.xData,self.yData,self.zData]

        if goSignal:
            self.sig1Plot.plotItem.clear()
            self.sig2Plot.plotItem.clear()
            self.sig3Plot.plotItem.clear()
            if self.powSpecConnected or self.signalConnected:
                for s in signals[:3]:
                    s.chunkReceived.disconnect()
            signals[self.sig1selCmb.currentIndex()].chunkReceived.connect(self.sig1Update)
            signals[self.sig2selCmb.currentIndex()].chunkReceived.connect(self.sig2Update)
            signals[self.sig3selCmb.currentIndex()].chunkReceived.connect(self.sig3Update)
            self.signalConnected = True
        else:
            self.powSpec1Plot.plotItem.clear()
            self.powSpec2Plot.plotItem.clear()
            self.powSpec3Plot.plotItem.clear()
            if self.powSpecConnected or self.signalConnected:
                for s in signals[:3]:
                    s.chunkReceived.disconnect()
            signals[self.ps1selCmb.currentIndex()].chunkReceived.connect(self.ps1Update)
            signals[self.ps2selCmb.currentIndex()].chunkReceived.connect(self.ps2Update)
            signals[self.ps3selCmb.currentIndex()].chunkReceived.connect(self.ps3Update)
            self.powSpecConnected = True


    def trapTrack(self):

        pass


    def qpdTrack(self):

        pass


    def sig1Update(self,v):

        self.sig1Plot.plotItem.clear()
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.sig1selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.sig1selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig1selCmb.currentIndex()]
        if S != 0:
            plottableY = np.array(v[2])*S*k
        else:
            plottableY = vToNm(np.array(v[1]))
        plottableX = np.arange(plottableY.shape[0])
        #plottableX = np.array(v[0])-v[0][0]
        self.sig1Plot.plotItem.plot(plottableX,plottableY,pen=pens[0])


    def sig2Update(self,v):

        self.sig2Plot.plotItem.clear()
        print(self.sig2selCmb.currentIndex())
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.sig2selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.sig2selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig2selCmb.currentIndex()]
        print(vToNm)
        if S != 0:
            plottableY = np.array(v[2])*S*k
        else:
            plottableY = vToNm(np.array(v[1]))
        plottableX = np.arange(plottableY.shape[0])
        #plottableX = np.array(v[0])-v[0][0]
        self.sig2Plot.plotItem.plot(plottableX,plottableY,pen=pens[1])


    def sig3Update(self,v):

        self.sig3Plot.plotItem.clear()
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.sig3selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.sig3selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig1se3Cmb.currentIndex()]
        if S != 0:
            plottableY = np.array(v[2])*S*k
        else:
            plottableY = vToNm(np.array(v[1]))
        plottableX = np.arange(plottableY.shape[0])
        #plottableX = np.array(v[0])-v[0][0]
        self.sig3Plot.plotItem.plot(plottableX,plottableY,pen=pens[2])


    def ps1Update(self,v):

        self.powSpec1Plot.plotItem.clear()
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.ps1selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.ps1selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig1selCmb.currentIndex()]
        if S != 0:
            tempY = np.array(v[2])*S*k
        else:
            tempY = vToNm(np.array(v[1]))
        sampF = 1.0/np.mean(np.array(v[0])[1:]-np.array(v[0])[:-1])
        plottableX,plottableY = welch(tempY,sampF)
        self.powSpec1Plot.plotItem.plot(plottableX,plottableY,pen=pens[0])


    def ps2Update(self,v):

        self.powSpec2Plot.plotItem.clear()
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.ps2selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.ps2selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig1selCmb.currentIndex()]
        if S != 0:
            tempY = np.array(v[2])*S*k
        else:
            tempY = vToNm(np.array(v[1]))
        sampF = 1.0/np.mean(np.array(v[0])[1:]-np.array(v[0])[:-1])
        plottableX,plottableY = welch(tempY,sampF)
        self.powSpec2Plot.plotItem.plot(plottableX,plottableY,pen=pens[1])


    def ps3Update(self,v):

        self.powSpec3Plot.plotItem.clear()
        S = list([self.sx,self.sy,self.sz,0,0,0])[self.ps3selCmb.currentIndex()]
        k = list([self.kx,self.ky,self.kz,0,0,0])[self.ps3selCmb.currentIndex()]
        vToNm = list([0,0,0,self.xVToNm,self.yVToNm,self.zVToNm])[self.sig1selCmb.currentIndex()]
        if S != 0:
            tempY = np.array(v[2])*S*k
        else:
            tempY = vToNm(np.array(v[1]))
        sampF = 1.0/np.mean(np.array(v[0])[1:]-np.array(v[0])[:-1])
        plottableX,plottableY = welch(tempY,sampF)
        self.powSpec3Plot.plotItem.plot(plottableX,plottableY,pen=pens[0])


    def getParamsDict(self):

        baseDict = {QSpinBox:['NUM','.value()','.setValue(',[]],QDoubleSpinBox:['DBL','.value()','.setValue(',[]],
                    QLineEdit:['LINE','.text()','.setText(',[]],QCheckBox:['CKBOX','.isChecked()','.setChecked(',[]],
                    QComboBox:['CMBBOX','.currentIndex()','.setCurrentIndex(',[]]}

        for d in dir(self):
            dObj = getattr(self, d)
            try:
                if dObj.isReadOnly():
                    continue
            except:
                pass
            if type(dObj) in baseDict.keys():
                baseDict[type(dObj)][3].append(d)
            else:
                pass

        return baseDict


    def saveParams(self):

        parFileName = str(QFileDialog.getSaveFileName(self,'Choose a name for you parameters file',filter='Parameters Files (*.par)')[0])
        if parFileName == '':
            return None
        splitName = splitext(parFileName)
        if splitName[1] != '.par':
            parFileName = splitName[0]+'.par'

        sDict = self.getParamsDict()
        paramsFile = open(parFileName,'w')
        paramsParser = cfg.ConfigParser()

        paramsParser.add_section('MISC')
        paramsParser.set('MISC','ot',self.cfgFile)
        for k in sDict.keys():
            paramsParser.add_section(sDict[k][0])
            for i in range(len(sDict[k][3])):
                paramsParser.set(sDict[k][0], sDict[k][3][i], str(eval('self.'+sDict[k][3][i]+sDict[k][1])))

        paramsParser.write(paramsFile)
        paramsFile.close()


    def loadParams(self):

        self.cmbBoxDisconnect()
        parFileName = str(QFileDialog.getOpenFileName(self,'Choose a parameters file',filter='Parameters Files (*.par)')[0])
        if parFileName == '':
            return None
        lDict = self.getParamsDict()
        #paramsFile = open(parFileName,'r')
        paramsParser = cfg.ConfigParser()
        paramsParser.read(parFileName)
        print(paramsParser.sections())
        if paramsParser.get('MISC', 'ot') != self.cfgFile:
            warning = QMessageBox(self)
            warning.setText('You tried to load parameters that have been saved for another OT\n'+
                            'Please choose a parameter file for you current OT')
            warning.exec_()
            self.loadParams()
        attrList = dir(self)
        for a in attrList:
            for k in lDict.keys():
                if a in lDict[k][3]:
                    value = paramsParser.get(lDict[k][0],a.lower())
                    try:
                        value = str(eval(value))
                    except:
                        value = '\'' + value + '\''
                    eval('self.' + a + lDict[k][2] + value + ')')
        self.cmbBoxConnections()


    def configNum(self,numName,cfgName,cfgKey):
        
        culprit = getattr(self, numName)
        scale = (1/INCR) if (type(culprit) == QDial or type(culprit) == QSlider) else 1
        getattr(self, numName).setMaximum(float(self.cfgParse[cfgKey][cfgName+'MAX'])*scale)
        getattr(self, numName).setMinimum(float(self.cfgParse[cfgKey][cfgName+'MIN'])*scale)
        getattr(self, numName).setSingleStep(INCR*scale)
        getattr(self, numName).setValue(float(self.cfgParse[cfgKey][cfgName])*scale)
        
    
    def changeCmbGrMem(self):
        sendCmb = self.sender()
        fatherCmb = sendCmb.parentWidget()
        listCmbChild = [c for c in fatherCmb.children() if (type(c)==QComboBox and c is not sendCmb)]
        equalValCmbList = [l for l in listCmbChild if l.currentIndex()==sendCmb.currentIndex()]
        if equalValCmbList != []:
            equalValCmb = equalValCmbList[0]
            elements = list(range(sendCmb.count()))
            elements.remove(sendCmb.currentIndex())
            listOtherChild = [c for c in listCmbChild if c is not equalValCmb]
            for c in listOtherChild:
                elements.remove(c.currentIndex())
            equalValCmb.blockSignals(True)
            equalValCmb.setCurrentIndex(elements[0])
            equalValCmb.blockSignals(False)

        if self.xData != None:
            print(sendCmb.objectName())
            self.linkPlotToData((sendCmb is self.sig1selCmb or sendCmb is self.sig2selCmb or sendCmb is self.sig3selCmb))
        
    
    def setScaledValue(self,rec):
        culprit = self.sender()
        scale = rec.singleStep() if (type(culprit) == QDial or type(culprit) == QSlider) else 1/culprit.singleStep()
        rec.blockSignals(True)
        rec.setValue(culprit.value()*scale)
        rec.blockSignals(False)
        
        
    def selectDir(self,displayLine):
        
        displayLine.setText(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        
    
    def updateDirObj(self):
        
        culprit = self.sender()
        folder = culprit.text()
        folder=folder.replace('/',sep)
        if culprit == self.logDirLine:
            self.logDir = folder
        else:
            self.dataDir = folder



    def showDial(self):

        culprit = self.sender()

        if culprit is self.action_Config_File:
            self.cfgDial = configDial(self.cfgFile,self)
            self.cfgDial.exec_()


    def closeEvent(self, event):
        print('logdir: '+self.logDir)
        reply = QMessageBox.question(self, 'Message',
            "Do you really want to close OTsUI?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.xData is None:
                event.accept()
                return None
            self.xInterpreter.circulaBufferOff()
            self.yInterpreter.circulaBufferOff()
            self.zInterpreter.circulaBufferOff()
            self.xInterpreter.stopDev()
            self.yInterpreter.stopDev()
            self.zInterpreter.stopDev()

            reply = QMessageBox.question(self, 'Message',
                                               "Do you want to kill the devices (If you say yes, you'll have to turn the towers off and then on before using CoMPlEx again)?",
                                               QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.xInterpreter.killDev()
                self.yInterpreter.killDev()
                self.zInterpreter.killDev()

            event.accept()
        else:
            event.ignore()


    def trapPadControl(self):

        culprit = self.sender()
        print(culprit.objectName())
        if culprit is self.xPlusTrapBtn:
            lemma = self.incrementTrapX
        elif culprit is self.yPlusTrapBtn:
            lemma = self.incrementTrapY
        elif culprit is self.zPlusTrapBtn:
            lemma = self.incrementTrapZ
        elif culprit is self.xMinusTrapBtn:
            lemma = self.decrementTrapX
        elif culprit is self.yMinusTrapBtn:
            lemma = self.decrementTrapY
        elif culprit is self.zMinusTrapBtn:
            lemma = self.decrementTrapZ
        print('lemma down')
        self.buttonChecker = ButtonThread(lemma)
        self.buttonChecker.start()
        print('thread started')


    def stopTrap(self):

        self.buttonChecker.go = False


    def incrementTrapY(self):

        if self.yTrapPosNumDbl.value() >= self.yTrapPadStepNumDbl.maximum():
            return None
        self.yInterpreter.setDacHard(self.yTrapPosNumDbl.value()+self.yTrapPadStepNumDbl.value())


    def decrementTrapY(self):

        if self.yTrapPosNumDbl.value() <= self.yTrapPadStepNumDbl.minimum():
            return None
        self.yInterpreter.setDacHard(self.yTrapPosNumDbl.value()-self.yTrapPadStepNumDbl.value())


    def incrementTrapX(self):

        if self.xTrapPosNumDbl.value() >= self.xTrapPadStepNumDbl.maximum():
            return None
        self.xInterpreter.setDAC(self.xTrapPosNumDbl.value()+self.xTrapPadStepNumDbl.value())


    def decrementTrapX(self):

        if self.xTrapPosNumDbl.value() <= self.xTrapPadStepNumDbl.minimum():
            return None
        self.xInterpreter.setDacHard(self.yTrapPosNumDbl.value()-self.yTrapPadStepNumDbl.value())


    def incrementTrapZ(self):

        if self.zTrapPosNumDbl.value() >= self.zTrapPadStepNumDbl.maximum():
            return None
        self.zInterpreter.setDacHard(self.zTrapPosNumDbl.value()+self.zTrapPadStepNumDbl.value())


    def decrementTrapZ(self):

        if self.zTrapPosNumDbl.value() <= self.zTrapPadStepNumDbl.maximum():
            return None
        self.zInterpreter.setDacHard(self.zTrapPosNumDbl.value()+self.zTrapPadStepNumDbl.value())


    def numConnections(self):

        # Setting up the interconnection between UI numeric controls

        self.zPNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.zPDial))
        self.zPDial.valueChanged.connect(lambda: self.setScaledValue(self.zPNumDbl))

        self.zINumDbl.valueChanged.connect(lambda: self.setScaledValue(self.zIDial))
        self.zIDial.valueChanged.connect(lambda: self.setScaledValue(self.zINumDbl))

        self.xyPNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.xyPDial))
        self.xyPDial.valueChanged.connect(lambda: self.setScaledValue(self.xyPNumDbl))

        self.xyINumDbl.valueChanged.connect(lambda: self.setScaledValue(self.xyIDial))
        self.xyIDial.valueChanged.connect(lambda: self.setScaledValue(self.xyINumDbl))

        self.zOffSetNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.zOffSetDial))
        self.zOffSetDial.valueChanged.connect(lambda: self.setScaledValue(self.zOffSetNumDbl))

        self.xOffSetNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.xOffSetDial))
        self.xOffSetDial.valueChanged.connect(lambda: self.setScaledValue(self.xOffSetNumDbl))

        self.yOffSetNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.yOffSetDial))
        self.yOffSetDial.valueChanged.connect(lambda: self.setScaledValue(self.yOffSetNumDbl))

        self.xSpeedTrapPadSlider.valueChanged.connect(lambda: self.setScaledValue(self.xSpeedTrapPadNumDbl))
        self.xSpeedTrapPadNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.xSpeedTrapPadSlider))

        self.ySpeedTrapPadSlider.valueChanged.connect(lambda: self.setScaledValue(self.ySpeedTrapPadNumDbl))
        self.ySpeedTrapPadNumDbl.valueChanged.connect(lambda: self.setScaledValue(self.ySpeedTrapPadSlider))

        ######################################


    def cmbBoxConnections(self):

        # Setting Plot combo boxes

        self.sig1selCmb.currentIndexChanged.connect(self.changeCmbGrMem)
        self.sig2selCmb.currentIndexChanged.connect(self.changeCmbGrMem)
        self.sig3selCmb.currentIndexChanged.connect(self.changeCmbGrMem)

        self.ps1selCmb.currentIndexChanged.connect(self.changeCmbGrMem)
        self.ps2selCmb.currentIndexChanged.connect(self.changeCmbGrMem)
        self.ps3selCmb.currentIndexChanged.connect(self.changeCmbGrMem)


    def cmbBoxDisconnect(self):

        # Setting Plot combo boxes

        self.sig1selCmb.currentIndexChanged.disconnect()
        self.sig2selCmb.currentIndexChanged.disconnect()
        self.sig3selCmb.currentIndexChanged.disconnect()

        self.ps1selCmb.currentIndexChanged.disconnect()
        self.ps2selCmb.currentIndexChanged.disconnect()
        self.ps3selCmb.currentIndexChanged.disconnect()

        #################################################################################


    def pathConnections(self):

        # Set directories selection

        self.logDirBtn.clicked.connect(lambda: self.selectDir(self.logDirLine))
        self.dataDirBtn.clicked.connect(lambda: self.selectDir(self.dataDirLine))
        self.logDirLine.textChanged.connect(self.updateDirObj)
        self.dataDirLine.textChanged.connect(self.updateDirObj)

        #################################################################################


    def actionConnections(self):

        self.action_Config_File.triggered.connect(self.showDial)
        self.action_Save_Parameters.triggered.connect(self.saveParams)
        self.action_Load_Parameters.triggered.connect(self.loadParams)
        self.action_Exit.triggered.connect(self.close)


    def buttonConnections(self):

        self.xPlusTrapBtn.pressed.connect(self.trapPadControl)
        self.yPlusTrapBtn.pressed.connect(self.trapPadControl)
        self.zPlusTrapBtn.pressed.connect(self.trapPadControl)
        self.xMinusTrapBtn.pressed.connect(self.trapPadControl)
        self.yMinusTrapBtn.pressed.connect(self.trapPadControl)
        self.zMinusTrapBtn.pressed.connect(self.trapPadControl)
        self.xPlusTrapBtn.released.connect(self.stopTrap)
        self.yPlusTrapBtn.released.connect(self.stopTrap)
        self.zPlusTrapBtn.released.connect(self.stopTrap)
        self.xMinusTrapBtn.released.connect(self.stopTrap)
        self.yMinusTrapBtn.released.connect(self.stopTrap)
        self.zMinusTrapBtn.released.connect(self.stopTrap)
        self.connectBtn.clicked.connect(self.epzConnect)


    def genericConnections(self):

        self.plotTabs.currentChanged.connect(self.changePlotTab)

        

class ButtonThread(QThread):

    def __init__(self,func):

        super(ButtonThread,self).__init__()
        self.lemma = func
        self.go = True


    def run(self):

        while self.go:
            sleep(0.2)
            self.lemma()