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

from importer import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_shp_dialog.ui'))


class ImportShpDialog(QtGui.QDialog, FORM_CLASS, Importer):
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
        
        # Don't trigger combobox index changed if loading from config file
        self.is_loading_mapping = False
        
        # Filename
        self.lblFilename.setText(filename)
        
        # Setup table
        self.tabMapping.setHorizontalHeaderLabels([
                                                      QCoreApplication.translate('ImportShpDialog','QGIS Field'),
                                                      QCoreApplication.translate('ImportShpDialog','SHP Field'),
                                                      QCoreApplication.translate('ImportShpDialog','Value'),
                                                      QCoreApplication.translate('ImportShpDialog','Enabled')])
        self.tabMapping.setColumnWidth(0, 200)
        self.tabMapping.setColumnWidth(1, 200)
        self.tabMapping.setColumnWidth(2, 270)
        
        self.tabValueMap.setHorizontalHeaderLabels([
                                                      QCoreApplication.translate('ImportShpDialog','SHP Value'),
                                                      QCoreApplication.translate('ImportShpDialog','QGIS Value')
                                                      ])
        self.tabValueMap.setColumnWidth(0, 200)
        
        # Load shp layer
        self.shplayer = QgsVectorLayer(filename, filename, "ogr")
        
        # If not valid, don't show the dialog
        if not self.shplayer.isValid():
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('ImportShpDialog','Error'),
                                                                        QCoreApplication.translate('ImportShpDialog','Shapefile is not valid'))
            self.valid = False
            return
            
        # Load the default mapping
        self.mapping = LayerMapping()
        
        self._loadShpFields()
        self._loadQgisLayers()
        
    def _toggleFieldsMappingCheckboxes(self):
        self._setTableCheckboxChecked(self.tabMapping, 2, self.chkEnableAllFieldsMapping.isChecked())
        
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
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == self.shplayer.geometryType() and PagLuxembourg.main.current_project.isPagLayer(layer):
                self.qgislayers.append(layer)
                self.cbbLayers.addItem(layer.name(), layer.id())
    
    def _selectedLayerIndexChanged(self, index):
        '''
        Event on QGIS layer selection changed
        
        :param index: The selected layer index
        :type index: int
        '''
        
        if not self.is_loading_mapping:
            self.mapping = LayerMapping()
            self._loadMapping()
    
    def _loadMapping(self):
        '''
        Loads a mapping using an existing one or a default one
        
        :param mapping: An existing Mapping
        :type mapping: LayerMapping
        '''
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]
        
        # Gets the mapping destination layer
        for layer in self.qgislayers:
            if PagLuxembourg.main.current_project.getLayerTableName(layer) == self.mapping.destinationLayerName():
                qgis_layer = layer
        
        if self.mapping.destinationLayerName() is not None and qgis_layer is None:
            QMessageBox.critical(self, 
                                 QCoreApplication.translate('ImportShpDialog','Error'),
                                 QCoreApplication.translate('ImportShpDialog','Destination layer {} not found.').format(self.mapping.destinationLayerName()))
            return
        
        # Loads a config file mapping
        self.is_loading_mapping = True
        self.cbbLayers.setCurrentIndex(self.qgislayers.index(qgis_layer))
            
        qgis_fields = qgis_layer.dataProvider().fields()
        
        # Clear the table
        self.tabMapping.clearContents()
        self.tabMapping.setRowCount(len(qgis_fields) if qgis_fields.fieldNameIndex(PagLuxembourg.project.PK) == -1 else len(qgis_fields) - 1)
        
        rowindex = 0
        
        # Fill mapping
        for field in qgis_fields:
            # Skip PK field
            if field.name() == PagLuxembourg.project.PK:
                continue
        
            source, destination, constant_value, enabled, value_map = self.mapping.getFieldMappingForDestination(field.name())
            
            self.tabMapping.setItem(rowindex, 0, QTableWidgetItem(field.name())) # QGIS field
            self.tabMapping.setCellWidget(rowindex, 1, self._getShpFieldsCombobox(field, destination)) # SHP fields
            self.tabMapping.setCellWidget(rowindex, 2, self._getFieldsMappingTableItemWidget(qgis_layer, field.name(), constant_value)) # Constant value
            self.tabMapping.setCellWidget(rowindex, 3, self._getCenteredCheckbox(enabled if enabled is not None else True)) # Enabled checkbox
            
            rowindex +=  1
        
        self._loadValueMap()
        
        self.is_loading_mapping = False
    
    def _getShpFieldsCombobox(self, qgisfield, selected_shpfield = None):
        '''
        Get a combobox filled with the SHP layer fields to insert in a table widget
        
        :param qgisfield: The SHP field
        :type qgisfield: QgsField
        
        :param selected_shpfield: The QGIS field to select
        :type selected_shpfield: QString, str
        
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
        
        shplayer = self.shplayer
        shplayer_fields = shplayer.dataProvider().fields()
        
        current_item_index = 0
        selected_index = 0
        
        combobox.addItem(QCoreApplication.translate('ImportShpDialog','<None>'), None)
        current_item_index += 1
        
        for field in shplayer_fields:
            # Include only fields with compatible data type
            for shp_type, qgis_type in SHP_QGIS_ALLOWED_DATATYPE_MAP:
                if field.type() == shp_type and qgisfield.type() == qgis_type:
                    combobox.addItem(field.name(), field.name())
                    # Select field if same name
                    if field.name() == qgisfield.name() and selected_index == -1:
                        selected_index = current_item_index
                    if field.name() == selected_shpfield:
                        selected_index = current_item_index
                    current_item_index += 1
                    break;
        
        combobox.setCurrentIndex(selected_index)
        combobox.currentIndexChanged.connect(self._comboboxShpFieldIndexChanged)
        
        return widget
    
    def _tabMappingCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        
        if self.is_loading_mapping:
            return
        
        # Update mapping
        self._updateMappingFromUI(previousRow)
        
        # Load mapping into the table
        self._loadValueMap()
    
    def _comboboxShpFieldIndexChanged(self, index):
        # Get the row of the combobox which changed
        rowindex = 0
        
        for i in range(self.tabMapping.rowCount()):
            if self.tabMapping.cellWidget(i, 1) is self.sender().parent():
                rowindex = i
                
        # Layer mapping corresponding to the selected row
        self._updateMappingFromUI(rowindex)
        
        if rowindex == self.tabMapping.currentRow():
            self._loadValueMap()
        
    def _loadValueMap(self):
        # Disable the table
        self.tabValueMap.setEnabled(False)
        
        # Clear the table
        self.tabValueMap.clearContents()
        self.tabValueMap.setRowCount(0)
        
        mapping_rowindex = self.tabMapping.currentRow()
        
        if mapping_rowindex == -1:
            return
        
        shp_field = self._getCellValue(self.tabMapping, mapping_rowindex, 1)
        
        if shp_field is None:
            return
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]
        qgis_field = self._getCellValue(self.tabMapping, mapping_rowindex, 0)
                
        # Check if field editor is ValueMap
        if qgis_layer.editorWidgetV2(qgis_layer.fieldNameIndex(qgis_field)) != 'ValueMap':
            return
            
        shp_values = self._getFieldUniqueValue(self.shplayer, shp_field)
        valuemap = self.mapping.getValueMapForDestination(qgis_field)
        
        self.tabValueMap.setRowCount(len(shp_values))
        
        rowindex = 0
        
        for shp_value in shp_values:
            qgis_value = None
            for shp, qgis in valuemap:
                if shp == shp_value:
                    qgis_value = qgis
            self.tabValueMap.setItem(rowindex, 0, QTableWidgetItem(shp_value)) # SHP value
            self.tabValueMap.setCellWidget(rowindex, 1, self._getFieldsMappingTableItemWidget(qgis_layer, qgis_field, qgis_value, shp_value)) # QGIS value
            
            rowindex +=  1
        
        # Enable the table
        self.tabValueMap.setEnabled(True)
    
    def _getFieldUniqueValue(self, layer, field):
        
        result = set()
        
        fieldindex = layer.fieldNameIndex(field)
        
        for feature in layer.getFeatures():
            value = feature[fieldindex]
            result.add(value if value != NULL else 'NULL')
            
        return result
        
    def _updateMappingFromUI(self, mapping_rowindex = None):
        '''
        Get the field mapping between the source layer and destination layer
        
        :returns: A list of tuples : SHP field index, QGIS field index, None, Enabled (not a constant value)
        :rtype: List of tuples : str, str, None, Boolean, []
        '''
        
        if mapping_rowindex is None:
            mapping_rowindex = self.tabMapping.currentRow()
            
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]
        
        newmapping = LayerMapping()
        newmapping.setDestinationLayerName(PagLuxembourg.main.current_project.getLayerTableName(qgis_layer))
        
        for rowindex in range(self.tabMapping.rowCount()):
            qgis_field = self._getCellValue(self.tabMapping, rowindex, 0)
            valuemap = self.mapping.getValueMapForDestination(qgis_field)
            
            # If row is selected, update field mapping
            if rowindex == mapping_rowindex:
                del valuemap[:]
                for valuemap_rowindex in range(self.tabValueMap.rowCount()):
                    shp_value = self._getCellValue(self.tabValueMap, valuemap_rowindex, 0)
                    valuemap.append((
                                     shp_value if shp_value != 'NULL' else shp_value, 
                                     self._getCellValue(self.tabValueMap, valuemap_rowindex, 1)
                                     ))
                    
            newmapping.addFieldMapping(self._getCellValue(self.tabMapping, rowindex, 1),
                                       self._getCellValue(self.tabMapping, rowindex, 0),
                                       self._getCellValue(self.tabMapping, rowindex, 2),
                                       self._getCellValue(self.tabMapping, rowindex, 3),
                                       valuemap)        
        del self.mapping
        self.mapping = newmapping
    
    def _validateMapping(self):
        '''
        Validate the mapping
        
        :returns: True if the mapping is valid
        :rtype: Boolean
        '''
        
        self._updateMappingFromUI()
        
        mapping = self.mapping.fieldMappings()
        
        for shpfield, qgisfield, constant_value, enabled, value_map in mapping:
            pass
            
        return True
    
    def _launchImport(self):
        '''
        Launch the import
        '''
        
        if not self._validateMapping():
            return
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]        
        
        # Import the layer, and get the imported extent
        imported_extent = self._importLayer(
                                            self.shplayer, 
                                            qgis_layer, 
                                            self.mapping.asIndexFieldMappings(qgis_layer.dataProvider().fields(), self.shpfields)
                                            )
        
        # Zoom to selected
        if imported_extent is not None:
            PagLuxembourg.main.qgis_interface.mapCanvas().setExtent(imported_extent)
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ImportShpDialog','Success'), 
                                                                       QCoreApplication.translate('ImportShpDialog','Importation was successful'))
        
        self.close()
    
    def _loadConfig(self):
        '''
        Load a JSON configuration
        '''
        
        # Select config file to load
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setOption(QFileDialog.ReadOnly)
        dialog.setNameFilter('Json file (*.json)');
        dialog.setWindowTitle(QCoreApplication.translate('ImportShpDialog','Select the configuration file to load'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files)==0:
            return
        
        filename = selected_files[0]
        
        # Load mapping
        mapping = Mapping()
        mapping.parseJson(filename)
        
        if len(mapping.layerMappings()) != 1:
            return
        
        self.mapping = mapping.layerMappings()[0]
        self._loadMapping()
        
    def _saveConfig(self):
        '''
        Save the configuration to JSON
        '''
        
        if not self._validateMapping():
            return
        
        # Select json file to save
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter('Json file (*.json)');
        dialog.setWindowTitle(QCoreApplication.translate('ImportShpDialog','Select the json location'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files) == 0:
            return
        
        filename = selected_files[0]
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Generates the mapping and save it
        mapping = Mapping()
        mapping.addLayerMapping(self.mapping)
        mapping.writeJson(filename)
        
        QMessageBox.information(self, 
                                QCoreApplication.translate('ImportShpDialog','Success'),
                                QCoreApplication.translate('ImportShpDialog','Mapping configuration saved'))