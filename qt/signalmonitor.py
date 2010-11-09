#!/usr/bin/env python

"""
   Copyright 2010 Nissim Karpenstein

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

"""
   signalmonitor.py: This is the signal monitor client application that displays
   the signal strength amnd data transmission state icons in the statuas bar on
   a tethered computer.
"""

# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtCore, QtGui, QtNetwork
import os
import time
import subprocess
import simplejson as js

DATA_DISCONNECTED = 0
DATA_CONNECTING = 1
DATA_CONNECTED = 2
DATA_SUSPENDED = 3

DATA_ACTIVITY_NONE = 0
DATA_ACTIVITY_IN = 1
DATA_ACTIVITY_OUT = 2
DATA_ACTIVITY_INOUT = 3
DATA_ACTIVITY_DORMANT = 4

Timeout = 5000

def get_default_gateway_lnx():
  p = subprocess.Popen('route -n', shell=True, stdout=subprocess.PIPE)
  s = p.communicate()[0]
  for l in s.splitlines():
    try:
      i = l.index('UG')
      return l.split()[1]
    except ValueError:
      pass
  return ''

class ClientThread(QtCore.QThread):
  stateChanged = QtCore.pyqtSignal(str)
  error = QtCore.pyqtSignal(int, str)

  def __init__(self, dialog, parent=None):
    super(ClientThread, self).__init__(parent)
    self.dialog = dialog
    self.getParametersFromDialog()
    self.mutex = QtCore.QMutex()
    self.reset = False
    self.abort = False
    
  def __del__(self):
    self.mutex.lock()
    self.abort = True
    self.mutex.unlock()
    self.wait()

  def getParametersFromDialog(self):
    self.serverAddress = self.dialog.serverAddress
    self.manualServerAddress = self.dialog.manualServerAddress
    
  def connectToServer(self):
    if self.serverAddress == 'Automatic':
      server = self.getServerAddress()
    else:
      server = self.manualServerAddress()
    if server.find(':') == -1:
      port = 6236
    else:
      fields = server.split(':')
      server = fields[0]
      port = int(fields[1])
    print 'About to attempt connection to ' + server + ':' + str(port)
    self.socket = QtNetwork.QTcpSocket()
    self.socket.connectToHost(server, port)
    if not self.socket.waitForConnected(Timeout):
      self.error.emit(self.socket.error(), self.socket.errorString())
      return 
    print 'Successfully connected.'
  
  def disconnectServer(self):
    self.socket.writeData('S\n')
    self.socket.disconnectFromHost()
    if not self.socket.waitForDisconnected(Timeout):
      self.error.emit(self.socket.error(), self.socket.errorString())
      return 

  def getServerAddress(self):
    if os.uname()[0] == 'Linux':
      return get_default_gateway_lnx()
    return ''

  def restart(self):
    if self.isRunning():
      self.mutex.lock()
      self.reset = True
      self.mutex.unlock()
    else:
      self.start(QtCore.QThread.LowPriority)

  def stop(self):
    if self.isRunning():
      self.mutex.lock()
      self.abort = True
      self.mutex.unlock()

  def run(self):
    self.connectToServer()
    print 'About to write to socket'
    self.socket.writeData('G\n')
    print 'Done'
    if not self.socket.waitForReadyRead(Timeout):
      self.error.emit(self.socket.error(), self.socket.errorString())
      return
    print 'Checking for canReadLine'
    while True: #self.socket.canReadLine():
      print 'in loop'
      line = str(self.socket.readLineData(2000)).strip()
      print 'read a line: ' + line 
      if line != '{}' and line != '':
        self.stateChanged.emit(line)
      time.sleep(.2)
      if self.abort:
        self.disconnectServer()
        self.mutex.lock()
        self.abort = False
        self.mutex.unlock()
        return
      if self.reset:
        self.mutex.lock()
        self.reset = False
        self.mutex.unlock()
        self.disconnectServer()
        self.getParametersFromDialog()
        self.connectToServer()
      print 'writing to socket'
      self.socket.writeData('G\n')
      if not self.socket.waitForReadyRead(Timeout):
        self.error.emit(self.socket.error(), self.socket.errorString())
        return

class Window(QtGui.QDialog):
  def __init__(self):
    super(Window, self).__init__()

    self.loadConfig()
    print 'config loaded, showConfigOnStartup = ' + str(self.showConfigOnStartup)

    self.createOptionsGroupBox()

    self.svrAddressCombo.currentIndexChanged.connect(self.toggleManualAddress)
    self.okButton.clicked.connect(self.okAction)
    self.cancelButton.clicked.connect(self.cancelAction)
    if self.serverAddress == 'Automatic':
      self.svrAddressCombo.setCurrentIndex(0)
    else:
      self.svrAddressCombo.setCurrentIndex(1)

    self.createIconDict()
    self.createActions()
    self.createTrayIcons()

    mainLayout = QtGui.QVBoxLayout()
    mainLayout.addWidget(self.optionsGroupBox)
    self.setLayout(mainLayout)
    self.client = ClientThread(self)
    self.client.stateChanged.connect(self.processMessage)
    self.client.error.connect(self.clientError)

    self.setWindowTitle("Signal Monitor")
    self.resize(400, 175)

  def toggleManualAddress(self, index):
    if index == 0:
      self.svrAddressText.setEnabled(False)
      self.serverAddress = 'Automatic'
    else:
      self.serverAddress = 'Manual'
      self.svrAddressText.setEnabled(True)
      self.svrAddressText.setFocus()

  def okAction(self):
    self.serverAddress = str(self.svrAddressCombo.currentText())
    self.manualServerAddress = str(self.svrAddressText.text())
    self.showConfigOnStartup = (self.showConfigCheck.checkState() == QtCore.Qt.Checked)
    self.saveConfig()
    self.client.restart()
    self.done(0)

  def cancelAction(self):
    self.done(0)

  def iconActivated(self, reason):
    if reason in (QtGui.QSystemTrayIcon.Trigger, QtGui.QSystemTrayIcon.DoubleClick):
      self.iconComboBox.setCurrentIndex(
            (self.iconComboBox.currentIndex() + 1)
            % self.iconComboBox.count())
    elif reason == QtGui.QSystemTrayIcon.MiddleClick:
      self.showMessage()

  def showMessage(self):
    icon = QtGui.QSystemTrayIcon.MessageIcon(
          self.typeComboBox.itemData(self.typeComboBox.currentIndex()))
    self.trayIcon.showMessage(self.titleEdit.text(),
          self.bodyEdit.toPlainText(), icon,
          self.durationSpinBox.value() * 1000)

  def messageClicked(self):
    QtGui.QMessageBox.information(None, "Systray",
            "Sorry, I already gave what help I could.\nMaybe you should "
            "try asking a human?")

  def createOptionsGroupBox(self):
    self.optionsGroupBox = QtGui.QGroupBox("Options")
    self.svrAddressLabel = QtGui.QLabel("Server Address:")
    self.svrAddressCombo = QtGui.QComboBox()
    self.svrAddressCombo.addItem("Automatic")
    self.svrAddressCombo.addItem("Manual")
    self.svrManualLabel = QtGui.QLabel("Manual Address:")
    self.svrAddressText = QtGui.QLineEdit(self.manualServerAddress)
    self.svrAddressText.setEnabled(False)
    self.showConfigCheck = QtGui.QCheckBox("Show this window on startup:")
    self.showConfigCheck.setChecked(self.showConfigOnStartup)
    self.okButton = QtGui.QPushButton("OK")
    self.okButton.setDefault(True)
    self.cancelButton = QtGui.QPushButton("Cancel")
    self.cancelButton.setDefault(True)
    self.optionsLayout = QtGui.QGridLayout()
    self.optionsLayout.addWidget(self.svrAddressLabel, 0, 0)
    self.optionsLayout.addWidget(self.svrAddressCombo, 0, 1, 1, 3)
    self.optionsLayout.addWidget(self.svrManualLabel, 1, 0)
    self.optionsLayout.addWidget(self.svrAddressText, 1, 1, 1, 3)
    self.optionsLayout.addWidget(self.showConfigCheck, 2, 0, 1, 4)
    self.optionsLayout.addWidget(self.cancelButton, 3, 2)
    self.optionsLayout.addWidget(self.okButton, 3, 3)
    self.optionsGroupBox.setLayout(self.optionsLayout)

  def disconnect(self):
    self.client.stop()

  def createActions(self):
    self.optionsAction = QtGui.QAction("&Options", self,
          triggered=self.showNormal)
    self.disconnectAction = QtGui.QAction("&Disconnect", self,
          triggered=self.disconnect)
    self.quitAction = QtGui.QAction("&Quit", self,
          triggered=QtGui.qApp.quit)

  def createTrayIcons(self):
     self.trayIconMenu = QtGui.QMenu(self)
     self.trayIconMenu.addAction(self.optionsAction)
     self.trayIconMenu.addAction(self.disconnectAction)
     self.trayIconMenu.addAction(self.quitAction)

     self.trayIconSignal = QtGui.QSystemTrayIcon(self)
     self.trayIconSignal.setContextMenu(self.trayIconMenu)
     self.trayIconSignal.setIcon(self.iconDict['zeroBars'])
     self.trayIconSignal.show()
     self.trayIconData = QtGui.QSystemTrayIcon(self)
     self.trayIconData.setContextMenu(self.trayIconMenu)
     self.trayIconData.setIcon(self.iconDict['3gNoData'])
     self.trayIconData.show()

  def createIconDict(self):
    self.iconDict = {}
    self.iconDict['zeroBars'] = QtGui.QIcon('../images/zeroBars.png')
    self.iconDict['oneBars'] = QtGui.QIcon('../images/oneBars.png')
    self.iconDict['twoBars'] = QtGui.QIcon('../images/twoBars.png')
    self.iconDict['threeBars'] = QtGui.QIcon('../images/threeBars.png')
    self.iconDict['fourBars'] = QtGui.QIcon('../images/fourBars.png')
    self.iconDict['3gNoData'] = QtGui.QIcon('../images/3gNoData.png')
    self.iconDict['3gDataIn'] = QtGui.QIcon('../images/3gDataIn.png')
    self.iconDict['3gDataOut'] = QtGui.QIcon('../images/3gDataOut.png')
    self.iconDict['3gDataInOut'] = QtGui.QIcon('../images/3gDataInOut.png')
    self.iconDict['1xNoData'] = QtGui.QIcon('../images/1xNoData.png')
    self.iconDict['1xDataIn'] = QtGui.QIcon('../images/1xDataIn.png')
    self.iconDict['1xDataOut'] = QtGui.QIcon('../images/1xDataOut.png')
    self.iconDict['1xDataInOut'] = QtGui.QIcon('../images/1xDataInOut.png')

  """
    The format of the config file is name: value\n
  """
  def saveConfig(self):
    f = open(os.getenv('HOME') + '/.signalmon', 'w')
    f.write("ServerAddress: " + self.serverAddress + '\n')
    if self.serverAddress == 'Manual':
      f.write("ManualServerAddress: " + self.manualServerAddress + '\n')
      #f.write("ManualServerPort: " + self.manualServerPort + '\n')
    f.write("ShowConfigOnStartup: " + str(self.showConfigOnStartup) + '\n')
    f.close()

  def loadConfig(self):
    self.serverAddress = 'Automatic'
    self.manualServerAddress = ''
    self.manualServerPort = ''
    self.showConfigOnStartup = True
    try: 
      f = open(os.getenv('HOME') + '/.signalmon', 'r')
      lines = f.readlines()
      f.close()
      for l in lines:
        (k, v) = [x.strip() for x in l.split(': ')]
        print 'k, v: %s, %s' % (k, v)
        if k == 'ServerAddress':
          self.serverAddress = v
        elif k == 'ManualServerAddress':
          self.manualServerAddress = v
        elif k == 'ManualServerPort':
          self.manualServerPort = v
        elif k == 'ShowConfigOnStartup':
          self.showConfigOnStartup = (v == 'True')
    except IOError:
      pass

  def clientError(self, i, s):
    QtGui.QMessageBox.critical(self, 'Error in network connection to phone', 'Error # ' + str(i) + ': ' + s)

  def processMessage(self, s):
    print 'in processMessage slot'
    m = js.loads(str(s))
    if m['connState'] == DATA_CONNECTED:
      self.trayIconData.show()
    else:
      self.trayIconData.hide()
    if m['evdoSnr'] >= 0:
      numbars = round(m['evdoSnr'] / 2.0)
      mode = '3g'
    else:
      mode = '1x'
      if m['cdmaDbm'] < -100:
        numbars = 0
      elif m['cdmaDbm'] < -96:
        numbars = 1
      elif m['cdmaDbm'] < -86:
        numbars = 2
      elif m['cdmaDbm'] < -76:
        numbars = 3
      else:
        numbars = 4

    if numbars == 0:
      self.trayIconSignal.setIcon(self.iconDict['zeroBars'])
    elif numbars == 1:
      self.trayIconSignal.setIcon(self.iconDict['oneBars'])
    elif numbars == 2:
      self.trayIconSignal.setIcon(self.iconDict['twoBars'])
    elif numbars == 3:
      self.trayIconSignal.setIcon(self.iconDict['threeBars'])
    elif numbars == 4:
      self.trayIconSignal.setIcon(self.iconDict['fourBars'])
      
    if m['dataActivity'] in (DATA_ACTIVITY_NONE, DATA_ACTIVITY_DORMANT):
      self.trayIconData.setIcon(self.iconDict[mode + 'NoData'])
    elif m['dataActivity'] == DATA_ACTIVITY_IN:
      self.trayIconData.setIcon(self.iconDict[mode + 'DataIn'])
    elif m['dataActivity'] == DATA_ACTIVITY_OUT:
      self.trayIconData.setIcon(self.iconDict[mode + 'DataOut'])
    elif m['dataActivity'] == DATA_ACTIVITY_INOUT:
      self.trayIconData.setIcon(self.iconDict[mode + 'DataInOut'])
      


if __name__ == '__main__':

  import sys

  app = QtGui.QApplication(sys.argv)

  if not QtGui.QSystemTrayIcon.isSystemTrayAvailable():
    QtGui.QMessageBox.critical(None, "Systray",
                "I couldn't detect any system tray on this system.")
    sys.exit(1)

  QtGui.QApplication.setQuitOnLastWindowClosed(False)

  window = Window()
  print 'window.showConfigOnStartup: ' + str(window.showConfigOnStartup)
  if window.showConfigOnStartup:
    window.show()
  else:
    window.client.start(QtCore.QThread.LowPriority)
  sys.exit(app.exec_())


