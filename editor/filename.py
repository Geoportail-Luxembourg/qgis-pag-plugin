'''
Created on 08 dec. 2015

@author: arxit
'''

from qgis.gui import QgsEditorWidgetWrapper, QgsEditorConfigWidget, QgsEditorWidgetFactory, QgsEditorWidgetRegistry, QgsFilterLineEdit
from qgis.core import NULL
from PyQt4.QtGui import QWidget, QPalette, QPushButton, QGridLayout, QLineEdit, QFileDialog, QLabel, QHBoxLayout
from PyQt4.QtCore import QCoreApplication, QFileInfo, QSettings

import os.path
 
class FilenameWidgetWrapper(QgsEditorWidgetWrapper):
    def value(self):
        if self.mLineEdit is not None:
            if self.mLineEdit.text() == str(QSettings().value('qgis/nullValue', 'NULL' )) or self.mLineEdit.text() == '':
                value = NULL
            else:
                value = self.mLineEdit.text()

        if self.mLabel is not None:
            value = self.mLabel.text();

        return value
 
    def setValue(self, value):
        if self.mLineEdit is not None:
            if value == NULL or value is None:
                self.mLineEdit.setText(str(QSettings().value('qgis/nullValue', 'NULL')))
            else:
                self.mLineEdit.setText(value)
    
        if self.mLabel is not None:
            self.mLabel.setText(value)
 
    def createWidget(self, parent):
        '''
        #Create a new empty widget
        '''
        
        container = QWidget(parent)
        container.setBackgroundRole(QPalette.Window)
        container.setAutoFillBackground(True)
        
        le = QgsFilterLineEdit(container)
        pbn = QPushButton('...', container)
        layout = QGridLayout()
    
        layout.setMargin(0)
        layout.addWidget(le, 0, 0);
        layout.addWidget(pbn, 0, 1);
    
        container.setLayout(layout);
    
        return container
    
    def initWidget(self, editor):
        self.mLineEdit = editor if editor is QLineEdit else editor.findChild(QLineEdit)
    
        self.mPushButton = editor.findChild(QPushButton)
    
        if self.mPushButton is not None:
            self.mPushButton.clicked.connect(self.selectFileName)
    
        self.mLabel = editor if editor is QLabel else None
    
        if self.mLineEdit is QLineEdit:
            fle = editor
            if fle is QgsFilterLineEdit:
                fle.setNullValue(str(QSettings().value('qgis/nullValue', 'NULL')))
    
            self.mLineEdit.textChanged.connect(self.valueChanged)

    def valid(self):
        return self.mLineEdit is not None or self.mLabel is not None
    
    def selectFileName(self):
        if self.mLineEdit is not None:
            text = self.mLineEdit.text()

        if self.mLabel is not None:
            text = self.mLabel.text()

        fileName = QFileDialog.getOpenFileName(self.mLineEdit,
                                               QCoreApplication.translate('FilenameWidgetWrapper','Select a file'),
                                               QFileInfo(text).absolutePath())

        if fileName.strip() == u'':
            return
        
        fileName = os.path.splitext(os.path.basename(fileName.strip()))[0]
        
        if self.mLineEdit is not None:
            self.mLineEdit.setText(fileName)

        if self.mLabel is not None:
            self.mLineEdit.setText(fileName)

class FilenameWidgetWrapperConfig(QgsEditorConfigWidget):
    def __init__(self, layer, idx, parent):
        QgsEditorConfigWidget.__init__(self, layer, idx, parent)
        
        self.setLayout(QHBoxLayout())
        self.ruleEdit = QLabel(self)
        self.ruleEdit.setText(QCoreApplication.translate('FilenameWidgetWrapperConfig','A filename without extension editor widget.'))
        self.layout().addWidget(self.ruleEdit)
 
    def config(self):
        return {}
 
    def setConfig(self, config):
        pass
                     
class FilenameWidgetWrapperFactory(QgsEditorWidgetFactory):
    def __init__(self):
        QgsEditorWidgetFactory.__init__(self, QCoreApplication.translate('QgsEditorWidgetFactory','Simple Filename'))
 
    def create(self, layer, fieldIdx, editor, parent):
        return FilenameWidgetWrapper(layer, fieldIdx, editor, parent)
 
    def configWidget(self, layer, idx, parent):
        return FilenameWidgetWrapperConfig(layer, idx, parent)
 
myFactory = FilenameWidgetWrapperFactory()
QgsEditorWidgetRegistry.instance().registerWidget('SimpleFilename', myFactory)
