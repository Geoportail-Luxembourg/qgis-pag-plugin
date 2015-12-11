'''
Created on 08 dec. 2015

@author: arxit
'''

from qgis.gui import QgsEditorWidgetWrapper, QgsEditorConfigWidget, QgsEditorWidgetFactory, QgsEditorWidgetRegistry, QgsFilterLineEdit
from qgis.core import NULL
from PyQt4.QtGui import QDoubleSpinBox, QHBoxLayout, QLabel
from PyQt4.QtCore import QCoreApplication, QFileInfo, QSettings

import os.path
 
class PreciseRangeWidgetWrapper(QgsEditorWidgetWrapper):
    def value(self):
        if self.spinbox is not None:
            value = self.spinbox.value()
            if value == self.spinbox.minimum() and self.config('AllowNull'):
                return NULL
            else:
                return value
 
    def setValue(self, value):
        if self.spinbox is not None:
            if value is None or value == NULL:
                self.spinbox.setValue(self.spinbox.minimum())
            else:
                self.spinbox.setValue(value)
 
    def createWidget(self, parent):
        return QDoubleSpinBox(parent)
    
    def initWidget(self, editor):
        self.spinbox = editor if type(editor) is QDoubleSpinBox else editor.findChild(QDoubleSpinBox)
    
        if self.spinbox is not None:
            minvalue = self.config('Min')
            maxvalue = self.config('Max')
            step = self.config('Step')
            nullable = self.config('AllowNull')
            self.spinbox.setMinimum(minvalue)
            self.spinbox.setMaximum(maxvalue)            
            self.spinbox.setSingleStep(step)
            self.spinbox.setDecimals(len(str(step).split('.')[1]) if len(str(step).split('.'))==2 else 0)
            if nullable:
                self.spinbox.setMinimum(minvalue - step)
                self.spinbox.setValue(self.spinbox.minimum())
                self.spinbox.setSpecialValueText(str(QSettings().value('qgis/nullValue', 'NULL' )))
            self.spinbox.valueChanged.connect(self.onValueChanged)
            
    def onValueChanged(self, value):
        self.valueChanged.emit(value)

    def valid(self):
        return self.spinbox is not None

class PreciseRangeWidgetWrapperConfig(QgsEditorConfigWidget):
    def __init__(self, layer, idx, parent):
        QgsEditorConfigWidget.__init__(self, layer, idx, parent)
        
        self.setLayout(QHBoxLayout())
        self.ruleEdit = QLabel(self)
        self.ruleEdit.setText(QCoreApplication.translate('PreciseRangeWidgetWrapperConfig','A precise range editor.'))
        self.layout().addWidget(self.ruleEdit)
 
    def config(self):
        return self.conf
 
    def setConfig(self, config):
        self.conf = config
                     
class PreciseRangeWidgetWrapperFactory(QgsEditorWidgetFactory):
    def __init__(self):
        QgsEditorWidgetFactory.__init__(self, QCoreApplication.translate('PreciseRangeWidgetWrapperFactory','Precise Range'))
 
    def create(self, layer, fieldIdx, editor, parent):
        return PreciseRangeWidgetWrapper(layer, fieldIdx, editor, parent)
 
    def configWidget(self, layer, idx, parent):
        return PreciseRangeWidgetWrapperConfig(layer, idx, parent)
    
    def writeConfig( self, config, elem, doc, layer, idx ):
        elem.setAttribute('Min', config['Min'])
        elem.setAttribute('Max', config['Max'])
        elem.setAttribute('Step', config['Step'])
        elem.setAttribute('AllowNull', config['AllowNull'])
 
    def readConfig(self, elem, layer, idx):
        config = dict()
        config['Min'] = elem.attribute('Min')
        config['Max'] = elem.attribute('Max')
        config['Step'] = elem.attribute('Step')
        config['AllowNull'] = elem.attribute('AllowNull')
        return config
 
myFactory = PreciseRangeWidgetWrapperFactory()
QgsEditorWidgetRegistry.instance().registerWidget('PreciseRange', myFactory)
