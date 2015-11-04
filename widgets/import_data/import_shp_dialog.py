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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QColor, QCheckBox, QWidget, QHBoxLayout, QComboBox
from PyQt4.QtCore import QCoreApplication, Qt, QVariant

from qgis.core import *

import PagLuxembourg.main
import PagLuxembourg.project

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_shp_dialog.ui'))


class ImportShpDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, filename, parent=None):
        '''
        Constructor.
        '''
        
        super(ImportShpDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        # Indicates the shapefile loading is valid 
        self.valid = True
        
        self.lblFilename.setText(filename)
        
        self.tabMapping.setHorizontalHeaderLabels([
                                                      QCoreApplication.translate('ImportShpDialog','SHP Field'),
                                                      QCoreApplication.translate('ImportShpDialog','QGIS Field'),
                                                      QCoreApplication.translate('ImportShpDialog','Enabled'),
                                                      QCoreApplication.translate('ImportShpDialog','Error')])
        self.tabMapping.horizontalHeader().setResizeMode(QHeaderView.Stretch);
        
        self.shplayer = QgsVectorLayer(filename, filename, "ogr")
        
        if not self.shplayer.isValid():
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('ImportShpDialog','Error'),
                                                                        QCoreApplication.translate('ImportShpDialog','Shapefile is not valid'))
            self.valid = False
            return
            
        self._loadShpFields()
        self._loadQgisLayers()
        
    def _loadShpFields(self):
        '''
        Loads the SHP layer fields available to import
        '''
        
        self.shpfields = self.shplayer.dataProvider().fields()
        
    def _loadQgisLayers(self):
        '''
        Loads the QGIS layers into the combobox
        '''
        
        self.qgislayers = list()
        
        # Adds the map layers with same geometry type to the combobox
        for layer in PagLuxembourg.main.qgis_interface.legendInterface().layers():
            if layer.geometryType() == self.shplayer.geometryType():
                self.qgislayers.append(layer)
                self.cbbLayers.addItem(layer.name(), layer.id())
    
    def _selectedLayerIndexChanged(self, index):
        '''
        Event on QGIS layer selection changed
        
        :param index: The selected layer index
        :type index: int
        '''
        
        qgislayer = self.qgislayers[index]
        qgislayer_fields = qgislayer.dataProvider().fields()
        
        self.tabMapping.clearContents()
        self.tabMapping.setRowCount(len(self.shpfields))
        
        rowindex = 0
        
        # Fill mapping
        for shpfield in self.shpfields:
            self.tabMapping.setItem(rowindex, 0, QTableWidgetItem(shpfield.name())) # SHP field name
            self.tabMapping.setCellWidget(rowindex, 1, self._getQgisFieldsCombobox(shpfield)) # QGIS fields
            self.tabMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox()) # Enabled checkbox
            
            rowindex +=  1
    
    def _getCenteredCheckbox(self, checked=True):
        '''
        Get a centered checkbox to insert in a table widget
        
        :returns: A widget with a centered checkbox
        :rtype: QWidget
        '''
        
        widget = QWidget()
        checkBox = QCheckBox()
        checkBox.setChecked(checked)
        layout = QHBoxLayout(widget)
        layout.addWidget(checkBox);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(0,0,0,0);
        widget.setLayout(layout);
        
        return widget
    
    def _getMappingRowEnabled(self, rowindex):
        '''
        Get the checked state of the checkbox at the given row
        
        :param rowindex: The row index
        :type rowindex: Int
        
        :returns: True if checked
        :rtype: Boolean
        '''
        
        for child in self.tabMapping.cellWidget(rowindex, 2).children():
            if type(child) is QCheckBox:
                return child.isChecked()
        
        raise TypeError('No checkbox found')
    
    def _getQgisFieldsCombobox(self, shpfield):
        '''
        Get a combobox filled with the QGIS layer fields to insert in a table widget
        
        :param shpfield: The SHP field
        :type shpfield: QgsField
        
        :returns: A combobox with the QGIS layer fields
        :rtype: QWidget
        '''
        # Datatype mapping allowed while checking. For a given SHP type, several QGIS type may be allowed or compatible
        SHP_QGIS_ALLOWED_DATATYPE_MAP = [(QVariant.String, QVariant.String),
                                         (QVariant.LongLong, QVariant.LongLong),
                                         (QVariant.LongLong, QVariant.Double),
                                         (QVariant.LongLong, QVariant.String),
                                         (QVariant.Int, QVariant.Int),
                                         (QVariant.Int, QVariant.LongLong),
                                         (QVariant.Int, QVariant.Double),
                                         (QVariant.Int, QVariant.String),
                                         (QVariant.Double, QVariant.Double),
                                         (QVariant.Double, QVariant.String)]
        
        widget = QWidget()
        combobox = QComboBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(combobox, 1);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(5,0,5,0);
        widget.setLayout(layout);
        
        qgislayer = self.qgislayers[self.cbbLayers.currentIndex()]
        qgislayer_fields = qgislayer.dataProvider().fields()
        
        current_item_index = 0
        selected_index = -1
        
        for field in qgislayer_fields:
            # Skip PK field
            if field.name() == PagLuxembourg.project.PK:
                continue
            
            # Include only fields with compatible data type
            for shp_type, qgis_type in SHP_QGIS_ALLOWED_DATATYPE_MAP:
                if shpfield.type() == shp_type and field.type() == qgis_type:
                    combobox.addItem(field.name())
                    # Select field if same name
                    if field.name() == shpfield.name():
                        selected_index = current_item_index
                    current_item_index += 1
                    break;
        
        combobox.setCurrentIndex(selected_index)
        
        return widget
    
    def _getSelectedQgisField(self, rowindex):
        '''
        Get the selected QGIS field name at the given row
        
        :param rowindex: The row index
        :type rowindex: Int
        
        :returns: The selected QGIS field name
        :rtype: QString, str
        '''
        
        for child in self.tabMapping.cellWidget(rowindex, 1).children():
            if type(child) is QComboBox:
                return child.currentText()
        
        raise TypeError('No combobox found')
    
    def _getActiveMapping(self):
        '''
        Get the active mapping, without disabled rows
        
        :returns: A list of tuples, shp field name, qgis field name
        :rtype: List of tuples
        '''
        
        mapping = list()
        
        for rowindex in range(self.tabMapping.rowCount()):
            if self._getMappingRowEnabled(rowindex):
                mapping.append((self.tabMapping.item(rowindex, 0).text(), self._getSelectedQgisField(rowindex)))
        
        return mapping
    
    def _validateMapping(self):
        '''
        Validate the mapping
        
        :returns: True if the mapping is valid
        :rtype: Boolean
        '''
        
        mapping = self._getActiveMapping()
        unique_qgisfields = list()
        
        for shpfield, qgis_field in mapping:
            # Check whether QGIS field is empty
            if qgis_field == '':
                QMessageBox.critical(self, 
                                 QCoreApplication.translate('ImportShpDialog','Error'),
                                 QCoreApplication.translate('ImportShpDialog','No QGIS field for SHP field {}.').format(shpfield))
                return False
            # Check whether QGIS field is unique
            if qgis_field in unique_qgisfields:
                QMessageBox.critical(self, 
                                 QCoreApplication.translate('ImportShpDialog','Error'),
                                 QCoreApplication.translate('ImportShpDialog','QGIS field {} is used more than one time.').format(qgis_field))
                return False
            
            unique_qgisfields.append(qgis_field)
        
        return True
    
    def _launchImport(self):
        '''
        Launch the import
        '''
        
        if not self._validateMapping():
            return
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]        
        shp_dp = self.shplayer.dataProvider()
        qgis_dp = qgis_layer.dataProvider()
        qgis_layer_fields = qgis_dp.fields()
        shp_qgis_fieldindexmap = self._getFieldIndexMap()
        newfeatures = list()
        
        # Iterate shp features
        for shpfeature in shp_dp.getFeatures():
            feature = QgsFeature(qgis_layer_fields)
            for shpindex, qgisindex in shp_qgis_fieldindexmap.iteritems():
                # Check if numeric value needs to be casted
                if shpfeature[shpindex] == NULL:
                    feature.setAttribute(qgisindex, NULL)
                elif feature.fields()[qgisindex].type() == QVariant.String and not isinstance(shpfeature[shpindex], basestring):
                    feature.setAttribute(qgisindex, str(shpfeature[shpindex]))
                else:
                    feature.setAttribute(qgisindex, shpfeature[shpindex])
            
            if qgis_layer.hasGeometryType():
                feature.setGeometry(shpfeature.geometry())
            
            newfeatures.append(feature)
        
        # Start editing session
        if not qgis_layer.isEditable():
            qgis_layer.startEditing()
        
        # Add features    
        qgis_layer.addFeatures(newfeatures, True)
        
        # Commit    
        if not qgis_layer.commitChanges():
            qgis_layer.rollBack()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('ImportShpDialog','Error'), 
                                                                        QCoreApplication.translate('ImportShpDialog','Commit error on layer {}').format(qgis_layer.name()))
        
        # Reload layer
        qgis_layer.reload()
        
        # Zoom to selected
        PagLuxembourg.main.qgis_interface.mapCanvas().zoomToSelected(qgis_layer)
        
        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ImportShpDialog','Success'), 
                                                                   QCoreApplication.translate('ImportShpDialog','Importation was successful'))
        
        self.close()
    
    def _getFieldIndexMap(self):
        '''
        Get the field index map between the source layer and destination layer
        
        :returns: A dictionnary of the source fields as key and destination fields as values
        :rtype: Dict
        '''
        
        indexmap = dict()
        
        mapping = self._getActiveMapping()
        
        source_fields = self.shpfields
        destination_fields = self.qgislayers[self.cbbLayers.currentIndex()].dataProvider().fields()
        
        for shpfield, qgisfield in mapping:
            indexmap[source_fields.fieldNameIndex(shpfield)]=destination_fields.fieldNameIndex(qgisfield)
            
        return indexmap