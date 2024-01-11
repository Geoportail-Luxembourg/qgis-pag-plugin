# -*- coding: utf-8 -*-
'''
Created on 08 dec. 2015

@author: arxit
'''

from builtins import str
from qgis.gui import QgsGui, QgsEditorWidgetWrapper, QgsEditorConfigWidget, QgsEditorWidgetFactory, QgsEditorWidgetRegistry, QgsFilterLineEdit
from qgis.core import NULL
from qgis.PyQt.QtWidgets import QWidget, QPushButton, QGridLayout, QLineEdit, QFileDialog, QLabel, QHBoxLayout
from qgis.PyQt.QtGui import QPalette
from qgis.PyQt.QtCore import QCoreApplication, QFileInfo, QSettings

import os.path

class SimpleFilenameWidgetWrapper(QgsEditorWidgetWrapper):
    def value(self):
        if self.mLineEdit is not None:
            if self.mLineEdit.text() == str(QSettings().value('qgis/nullValue', 'NULL' )) or self.mLineEdit.text() == '':
                value = NULL
            else:
                value = self.mLineEdit.text()

        if self.mLabel is not None:
            value = self.mLabel.text()

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
        layout.addWidget(le, 0, 0)
        layout.addWidget(pbn, 0, 1)

        container.setLayout(layout)

        return container

    def initWidget(self, editor):
        self.mLineEdit = editor if type(editor) is QLineEdit else editor.findChild(QLineEdit)

        self.mPushButton = editor.findChild(QPushButton)

        if self.mPushButton is not None:
            self.mPushButton.clicked.connect(self.selectFileName)

        self.mLabel = editor if type(editor) is QLabel else None

        if self.mLineEdit is not None:
            fle = editor
            if type(fle) is QgsFilterLineEdit:
                fle.setNullValue(str(QSettings().value('qgis/nullValue', 'NULL')))

            self.mLineEdit.textChanged.connect(self.onTextChanged)

    def onTextChanged(self, newText):
        self.valueChanged.emit(newText)

    def valid(self):
        return self.mLineEdit is not None or self.mLabel is not None

    def selectFileName(self):
        if self.mLineEdit is not None:
            text = self.mLineEdit.text()

        if self.mLabel is not None:
            text = self.mLabel.text()

        fileName, __ = QFileDialog.getOpenFileName(self.mLineEdit,
                                               QCoreApplication.translate('SimpleFilenameWidgetWrapper', 'Select a file'),
                                               QFileInfo(text).absolutePath())

        if fileName.strip() == u'':
            return

        fileName = os.path.splitext(os.path.basename(fileName.strip()))[0]

        if self.mLineEdit is not None:
            self.mLineEdit.setText(fileName)

        if self.mLabel is not None:
            self.mLineEdit.setText(fileName)

class SimpleFilenameWidgetWrapperConfig(QgsEditorConfigWidget):
    def __init__(self, layer, idx, parent):
        QgsEditorConfigWidget.__init__(self, layer, idx, parent)

        self.setLayout(QHBoxLayout())
        self.ruleEdit = QLabel(self)
        self.ruleEdit.setText(QCoreApplication.translate('SimpleFilenameWidgetWrapperConfig','A filename without extension editor widget.'))
        self.layout().addWidget(self.ruleEdit)

    def config(self):
        return {}

    def setConfig(self, config):
        pass

class SimpleFilenameWidgetWrapperFactory(QgsEditorWidgetFactory):
    def __init__(self):
        QgsEditorWidgetFactory.__init__(self, QCoreApplication.translate('SimpleFilenameWidgetWrapperFactory','Simple Filename'))

    def create(self, layer, fieldIdx, editor, parent):
        return SimpleFilenameWidgetWrapper(layer, fieldIdx, editor, parent)

    def configWidget(self, layer, idx, parent):
        return SimpleFilenameWidgetWrapperConfig(layer, idx, parent)

myFactory = SimpleFilenameWidgetWrapperFactory()
QgsGui.editorWidgetRegistry().registerWidget('SimpleFilename', myFactory)