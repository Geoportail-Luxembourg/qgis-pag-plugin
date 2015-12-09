'''
Created on 08 dec. 2015

@author: arxit
'''

from qgis.gui import QgsEditorWidgetWrapper, QgsEditorConfigWidget, QgsEditorWidgetFactory, QgsEditorWidgetRegistry, QgsFilterLineEdit
from qgis.core import NULL
from PyQt4.QtGui import QWidget, QPalette, QPushButton, QGridLayout, QLineEdit, QFileDialog, QLabel, QHBoxLayout
from PyQt4.QtCore import QCoreApplication, QFileInfo, QSettings

import os.path
 
class SimpleFilenamePicker(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        
        self.setAutoFillBackground(True)
        
        self.le = QgsFilterLineEdit(self)
        self.le.setNullValue(str(QSettings().value('qgis/nullValue', 'NULL')))
        pbn = QPushButton('...', self)
        pbn.clicked.connect(self.selectFileName)
        layout = QGridLayout()
    
        layout.setMargin(0)
        layout.addWidget(self.le, 0, 0)
        layout.addWidget(pbn, 0, 1)
    
        self.setLayout(layout)
        
        self.setValue(NULL)
    
    def value(self):
        if self.le.text() == str(QSettings().value('qgis/nullValue', 'NULL' )) or self.le.text() == '':
            return None
        else:
            return self.le.text()
 
    def setValue(self, value):
        if value == NULL or value is None:
            self.le.setText(str(QSettings().value('qgis/nullValue', 'NULL')))
        else:
            self.le.setText(value)
    
    def selectFileName(self):
        text = self.le.text()

        fileName = QFileDialog.getOpenFileName(self.le,
                                               QCoreApplication.translate('Filename','Select a file'),
                                               QFileInfo(text).absolutePath())

        if fileName.strip() == u'':
            return
        
        fileName = os.path.splitext(os.path.basename(fileName.strip()))[0]
        
        self.setValue(fileName)
