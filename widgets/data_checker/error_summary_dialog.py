# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ErrorSummaryDialog
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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QColor
from PyQt4.QtCore import QCoreApplication

import PagLuxembourg.main

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'error_summary_dialog.ui'))


class ErrorSummaryDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, schema_errors, data_errors, parent=None):
        '''
        Constructor.
        '''
        
        self.schema_errors = schema_errors
        self.data_errors = list()
        for layer, errors in data_errors:
            for feature, field, message in errors:
                self.data_errors.append((layer, feature, field, message))
        
        super(ErrorSummaryDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.tabSchemaErrors.setHorizontalHeaderLabels([
                                                      QCoreApplication.translate('ErrorSummaryDialog','Layer'),
                                                      QCoreApplication.translate('ErrorSummaryDialog','Field name'),
                                                      QCoreApplication.translate('ErrorSummaryDialog','Error')])
        self.tabSchemaErrors.horizontalHeader().setResizeMode(QHeaderView.Stretch);
        
        self.tabDataErrors.setHorizontalHeaderLabels([
                                                      QCoreApplication.translate('ErrorSummaryDialog','Layer'),
                                                      QCoreApplication.translate('ErrorSummaryDialog','Feature ID'),
                                                      QCoreApplication.translate('ErrorSummaryDialog','Field name'),
                                                      QCoreApplication.translate('ErrorSummaryDialog','Error')])
        self.tabDataErrors.horizontalHeader().setResizeMode(QHeaderView.Stretch);
        self.tabDataErrors.currentCellChanged.connect(self._tabDataErrorsCellChanged)
        
        self._loadSchemaErrors()
        self._loadDataErrors()

    def _loadSchemaErrors(self):
        self.tabSchemaErrors.setRowCount(len(self.schema_errors))
        
        rowindex = 0
        
        for layer, field, message in self.schema_errors:
            self.tabSchemaErrors.setItem(rowindex,0,QTableWidgetItem(layer.name())) # Layer name
            self.tabSchemaErrors.setItem(rowindex,1,QTableWidgetItem(field.name if field is not None else '')) # Field name
            self.tabSchemaErrors.setItem(rowindex,2,QTableWidgetItem(message)) # Message
            
            rowindex +=  1
    
    def _loadDataErrors(self):
        self.tabDataErrors.setRowCount(len(self.data_errors))
        
        rowindex = 0
        
        for layer, feature, field, message in self.data_errors:
            self.tabDataErrors.setItem(rowindex,0,QTableWidgetItem(layer.name())) # Layer name
            self.tabDataErrors.setItem(rowindex,1,QTableWidgetItem(str(feature.id()))) # Feature id
            self.tabDataErrors.setItem(rowindex,2,QTableWidgetItem(field.name if field is not None else '')) # Field name
            self.tabDataErrors.setItem(rowindex,3,QTableWidgetItem(message)) # Message
            
            rowindex +=  1
    
    def _tabDataErrorsCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        # Deselect
        layer, feature, field, message = self.data_errors[previousRow]
        layer.setSelectedFeatures([])
        
        layer, feature, field, message = self.data_errors[currentRow]
        layer.setSelectedFeatures([feature.id()])
        PagLuxembourg.main.qgis_interface.mapCanvas().zoomToSelected(layer)