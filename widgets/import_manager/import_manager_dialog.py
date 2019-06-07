# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImportShpDialog
                                 A QGIS plugin
 Gestion de Plans d'Aménagement Général du Grand-Duché de Luxembourg
                             -------------------
        begin                : 2015-10-23
        git sha              : $Format:%H$
        copyright            : (C) 2015 by arx iT
        email                : mba@arxit.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import absolute_import

import os

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QCheckBox, QWidget, QHBoxLayout, QComboBox
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QCoreApplication, Qt, QVariant

from qgis.core import *

import PagLuxembourg.main

from . import import_manager

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_manager_dialog.ui'))


class ImportManagerDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        '''
        Constructor.
        '''

        super(ImportManagerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # Setup table
        self.tabImports.setHorizontalHeaderLabels([
                                                   QCoreApplication.translate('ImportManagerDialog','Import Id'),
                                                   QCoreApplication.translate('ImportManagerDialog','Date'),
                                                   QCoreApplication.translate('ImportManagerDialog','Filename'),
                                                   QCoreApplication.translate('ImportManagerDialog','Imported layers')])
        self.tabImports.setColumnWidth(0, 230)
        self.tabImports.setColumnWidth(1, 80)
        self.tabImports.setColumnWidth(2, 200)

        self.tabImports.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Load imports
        layer = PagLuxembourg.main.current_project.getImportLogLayer()

        if layer is None:
            return

        self.tabImports.setRowCount(layer.featureCount())

        rowindex = 0

        for feature in layer.getFeatures():
            self.tabImports.setItem(rowindex, 0, self._getCenteredTableWidgetItem(feature[1]))
            self.tabImports.setItem(rowindex, 1, self._getCenteredTableWidgetItem(feature[2]))
            self.tabImports.setItem(rowindex, 2, self._getCenteredTableWidgetItem(feature[3]))
            self.tabImports.setItem(rowindex, 3, self._getCenteredTableWidgetItem(feature[4].replace('|','\n')))

            rowindex +=1

    def _getCenteredTableWidgetItem(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        return item

    def _rollbackBtnClicked(self):
        row = self.tabImports.currentRow()

        if row == -1:
            return

        importid = self.tabImports.item(row, 0).text()

        manager = import_manager.ImportManager()
        manager.rollbackImport(importid)

        self.close()