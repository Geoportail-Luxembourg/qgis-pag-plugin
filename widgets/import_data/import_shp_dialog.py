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
                                                      QCoreApplication.translate('ImportShpDialog','SHP Field'),
                                                      QCoreApplication.translate('ImportShpDialog','QGIS Field'),
                                                      QCoreApplication.translate('ImportShpDialog','Enabled')])
        self.tabMapping.setColumnWidth(0, 245)
        self.tabMapping.setColumnWidth(1, 245)
        
        # Load shp layer
        self.shplayer = QgsVectorLayer(filename, filename, "ogr")
        
        # If not valid, don't show the dialog
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
            self._loadMapping()
    
    def _loadMapping(self, mapping = None):
        '''
        Loads a mapping using an existing one or a default one
        
        :param mapping: An existing Mapping
        :type mapping: LayerMapping
        '''
        
        qgislayer = None
        
        if mapping is None:
            # Loads default mapping
            mapping = LayerMapping()
            qgislayer = self.qgislayers[self.cbbLayers.currentIndex()]
        else:
            # Gets the mapping destination layer
            for layer in self.qgislayers:
                if PagLuxembourg.main.current_project.getLayerTableName(layer) == mapping.destinationLayerName():
                    qgislayer = layer
            
            if qgislayer is None:
                QMessageBox.critical(self, 
                                     QCoreApplication.translate('ImportShpDialog','Error'),
                                     QCoreApplication.translate('ImportShpDialog','Destination layer {} not found.').format(mapping.destinationLayerName()))
                return
            
            # Loads a config file mapping
            self.is_loading_mapping = True
            self.cbbLayers.setCurrentIndex(self.qgislayers.index(qgislayer))
            
        qgislayer_fields = qgislayer.dataProvider().fields()
        
        # Clear the table
        self.tabMapping.clearContents()
        self.tabMapping.setRowCount(len(self.shpfields))
        
        rowindex = 0
        
        # Fill mapping
        for shpfield in self.shpfields:
            source, destination, constant_value, enabled = mapping.getFieldMappingForSource(shpfield.name())
            
            self.tabMapping.setItem(rowindex, 0, QTableWidgetItem(shpfield.name())) # SHP field name
            self.tabMapping.setCellWidget(rowindex, 1, self._getQgisFieldsCombobox(shpfield, destination)) # QGIS fields
            self.tabMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox(enabled if enabled is not None else True)) # Enabled checkbox
            
            rowindex +=  1
        
        self.is_loading_mapping = False
    
    def _getMappingRowEnabled(self, rowindex):
        '''
        Get the checked state of the checkbox at the given row
        
        :param rowindex: The row index
        :type rowindex: Int
        
        :returns: True if checked
        :rtype: Boolean
        '''
        
        return self._getCellValue(self.tabMapping, rowindex, 2)
    
    def _getQgisFieldsCombobox(self, shpfield, selected_qgisfield = None):
        '''
        Get a combobox filled with the QGIS layer fields to insert in a table widget
        
        :param shpfield: The SHP field
        :type shpfield: QgsField
        
        :param selected_qgisfield: The QGIS field to select
        :type selected_qgisfield: QString, str
        
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
                    if field.name() == shpfield.name() and selected_index == -1:
                        selected_index = current_item_index
                    if field.name() == selected_qgisfield:
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
        
        return self._getCellValue(self.tabMapping, rowindex, 1)[0]
    
    def _getMapping(self, export = False):
        '''
        Get the field mapping between the source layer and destination layer
        
        :param export: Gets the mapping for export, with enabled and field name instead of index
        :type export: Boolean
        
        :returns: A list of tuples : SHP field index, QGIS field index, None, Enabled (not a constant value)
        :rtype: List of tuples : int, int, None, Boolean
        '''
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]
        
        mapping = LayerMapping()
        mapping.setDestinationLayerName(PagLuxembourg.main.current_project.getLayerTableName(qgis_layer))
        
        source_fields = self.shpfields
        destination_fields = qgis_layer.dataProvider().fields()
        
        for rowindex in range(self.tabMapping.rowCount()):
            enabled = self._getMappingRowEnabled(rowindex)
            if export:
                mapping.addFieldMapping(self.tabMapping.item(rowindex, 0).text(),
                                        self._getSelectedQgisField(rowindex),
                                        None,
                                        enabled)
            elif enabled:
                mapping.addFieldMapping(source_fields.fieldNameIndex(self.tabMapping.item(rowindex, 0).text()),
                                        destination_fields.fieldNameIndex(self._getSelectedQgisField(rowindex)),
                                        None,
                                        enabled)
        
        return mapping
    
    def _validateMapping(self):
        '''
        Validate the mapping
        
        :returns: True if the mapping is valid
        :rtype: Boolean
        '''
        
        mapping = self._getMapping().fieldMappings()
        unique_qgisfields = list()
        
        for shpfield_index, qgisfield_index, constant_value, enabled in mapping:
            # Check whether QGIS field is empty
            if qgisfield_index < 0:
                QMessageBox.critical(self, 
                                 QCoreApplication.translate('ImportShpDialog','Error'),
                                 QCoreApplication.translate('ImportShpDialog','No QGIS field selected for SHP field {}.').format(self.shpfields[shpfield_index].name()))
                return False
            
            # Check whether QGIS field is unique
            if qgisfield_index in unique_qgisfields:
                QMessageBox.critical(self, 
                                 QCoreApplication.translate('ImportShpDialog','Error'),
                                 QCoreApplication.translate('ImportShpDialog','QGIS field {} is selected more than one time.').format(self.qgislayers[self.cbbLayers.currentIndex()].dataProvider().fields()[qgisfield_index].name()))
                return False
            
            unique_qgisfields.append(qgisfield_index)
        
        return True
    
    def _launchImport(self):
        '''
        Launch the import
        '''
        
        if not self._validateMapping():
            return
        
        qgis_layer = self.qgislayers[self.cbbLayers.currentIndex()]        
        
        # Import the layer, and get the imported extent
        imported_extent = self._importLayer(self.shplayer, qgis_layer, self._getMapping())
        
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
        
        self._loadMapping(mapping.layerMappings()[0])
        
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
        mapping.addLayerMapping(self._getMapping(True))
        mapping.writeJson(filename)
        
        QMessageBox.information(self, 
                                QCoreApplication.translate('ImportShpDialog','Success'),
                                QCoreApplication.translate('ImportShpDialog','Mapping configuration saved'))