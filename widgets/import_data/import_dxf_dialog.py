'''
Created on 05 nov. 2015

@author: arxit
'''

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QColor, QCheckBox, QWidget, QHBoxLayout, QComboBox
from PyQt4.QtCore import QCoreApplication, Qt, QVariant, QSettings

from qgis.core import *

import PagLuxembourg.main
import PagLuxembourg.project

from importer import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_dxf_dialog.ui'))


class ImportDxfDialog(QtGui.QDialog, FORM_CLASS, Importer):
    def __init__(self, filename, parent=None):
        '''
        Constructor.
        '''
        
        super(ImportDxfDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        # Don't trigger combobox index changed if loading from config file
        self.is_loading_mapping = False
        
        # Filename
        self.lblFilename.setText(filename)
        
        # Setup tables
        self.tabLayersMapping.setHorizontalHeaderLabels([QCoreApplication.translate('ImportDxfDialog','DXF Layer'),
                                                         QCoreApplication.translate('ImportDxfDialog','QGIS Layer'),
                                                         QCoreApplication.translate('ImportDxfDialog','Enabled')])
        self.tabLayersMapping.setColumnWidth(0, 200)
        self.tabLayersMapping.setColumnWidth(1, 200)
        self.tabFieldsMapping.setHorizontalHeaderLabels([QCoreApplication.translate('ImportDxfDialog','QGIS Field'),
                                                         QCoreApplication.translate('ImportDxfDialog','Value'),
                                                         QCoreApplication.translate('ImportDxfDialog','Enabled')])
        self.tabFieldsMapping.setColumnWidth(0, 200)
        self.tabFieldsMapping.setColumnWidth(1, 200)
        
        # Load dxf layers
        self._loadDxfLayers(filename)
        
        # If DXF is not valid, return
        if not self.valid :
            return
        
        # Load the QGIS layers
        self._loadQgisLayers()
        
        # Load the default mapping
        self._generateDefaultMapping()
        self._loadMapping()
            
    def _loadQgisLayers(self):
        '''
        Loads the QGIS layers
        '''
        
        self.qgislayers = list()
        
        # Adds the PAG map layers
        for layer in PagLuxembourg.main.qgis_interface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer and PagLuxembourg.main.current_project.isPagLayer(layer):
                self.qgislayers.append(layer)
    
    def _loadDxfLayers(self, filename):
        '''
        Loads the DXF geometrical layers, and the DXF layers names
        
        :param filename: The DXF filename
        :type filename: str, QString
        '''
        
        # Change project settings to avoid the select CRS box
        settings = QSettings()
        oldProjValue = settings.value( "/Projections/defaultBehaviour", "prompt", type=str )
        settings.setValue( "/Projections/defaultBehaviour", "useProject" )

        self.dxflayer_points = QgsVectorLayer('{}|layername=entities|geometrytype=Point'.format(filename), 'Points', 'ogr')
        self.dxflayer_linestrings = QgsVectorLayer('{}|layername=entities|geometrytype=LineString'.format(filename), 'LineString', 'ogr')
        self.dxflayer_polygons = QgsVectorLayer('{}|layername=entities|geometrytype=Polygon'.format(filename), 'Polygon', 'ogr')
        
        self.valid = self.dxflayer_points.isValid() or self.dxflayer_linestrings.isValid() or self.dxflayer_polygons.isValid()
        
        if not self.valid:
            return
        
        self.dxf_layernames = list()
        
        self._loadUniqueLayersNames(self.dxflayer_points)
        self._loadUniqueLayersNames(self.dxflayer_linestrings)
        self._loadUniqueLayersNames(self.dxflayer_polygons)
        
        settings.setValue( "/Projections/defaultBehaviour", oldProjValue )
    
    def _loadUniqueLayersNames(self, layer):
        '''
        Retrieves unique layer names from the DXF
        
        :param layer: The layer to search values
        :type layer: QgsVectorLayer
        '''
        
        dp = layer.dataProvider()
        layerfield_index = dp.fields().fieldNameIndex('Layer')
        
        for feature in dp.getFeatures():
            value = feature[layerfield_index]
            
            if value not in self.dxf_layernames:
                self.dxf_layernames.append(value)
    
    def _getQgisLayersCombobox(self, selected_layer = None):
        '''
        Get a combobox filled with the QGIS layers to insert in a table widget
        
        :param selected_layer: The QGIS layer table name to select
        :type selected_layer: QString, str
        
        :returns: A combobox with the QGIS layer fields
        :rtype: QWidget
        '''
        widget = QWidget()
        combobox = QComboBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(combobox, 1);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(5,0,5,0);
        widget.setLayout(layout);
        
        current_item_index = 0
        selected_index = -1
        
        # Add all PAG layers to combobox
        for layer in self.qgislayers:
            combobox.addItem(layer.name())
            
            # Select layer
            if PagLuxembourg.main.current_project.getLayerTableName(layer) == selected_layer:
                selected_index = current_item_index
            
            current_item_index += 1
                
        combobox.setCurrentIndex(selected_index)
        
        return widget
        
    def _generateDefaultMapping(self):
        '''
        Gets the default mappings for the current DXF file
        '''
        
        self.mapping = Mapping()
        
        for layer_name in self.dxf_layernames:
            layer_mapping = LayerMapping()
            layer_mapping.setSourceLayerName(layer_name)
            self.mapping.addLayerMapping(layer_mapping)
    
    def _loadMapping(self):
        '''
        Loads the current mapping
        '''
        
        # Clear the table
        self.tabLayersMapping.clearContents()
        self.tabLayersMapping.setRowCount(len(self.dxf_layernames))
        
        rowindex = 0
        
        # Fill layers mapping
        for layername in self.dxf_layernames:
            layer_mapping = self.mapping.getLayerMappingForSource(layername)
            
            self.tabLayersMapping.setItem(rowindex, 0, QTableWidgetItem(layername)) # DXF layer name
            self.tabLayersMapping.setCellWidget(rowindex, 1, self._getQgisLayersCombobox(layer_mapping.destinationLayerName())) # QGIS layers
            self.tabLayersMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox(layer_mapping.isEnabled())) # Enabled checkbox
            
            rowindex +=  1
        
        self.is_loading_mapping = False
    
    def _tabLayersMappingCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        # Layer mapping corresponding to the selected row
        layer_mapping = self._getCurrentLayersMapping()
        
        # Corresponding QGIS layer
        qgis_layer = self._getLayerFromTableName(layer_mapping.destinationLayerName)
        qgis_layername = qgis_layer.name() if qgis_layer is not None else None
        
        # Update label
        self.lblCurrentFieldMapping.setText(QCoreApplication.translate('ImportDxfDialog','Mapping for DXF layer {} to QGIS layer {}').format(layer_mapping.sourceLayerName(), qgis_layername))
        
        # Load mapping into the table
        self._loadCurrentFieldMapping()
    
    def _getCurrentLayersMapping(self):
        '''
        Gets the current field mapping corresponding to the selected layers mapping
        '''
        
        rowindex = self.tabLayersMapping.currentRow()
        dxf_layername = self.tabLayersMapping.item(rowindex, 0).text()
        qgis_layer = self._getLayerFromLayerName(self._getComboboxText(self.tabLayersMapping, rowindex, 1))
        qgis_tablename = PagLuxembourg.main.current_project.getLayerTableName(qgis_layer)
        
        layer_mapping = self.mapping.getLayerMappingForSource(dxf_layername)
        
        # Get or add current layer mapping
        if layer_mapping is None:
            layer_mapping = LayerMapping()
            layer_mapping.setSourceLayerName(dxf_layername)
            self.mapping.addLayerMapping(layer_mapping)
        
        # Check whether the destination layer is the same
        if qgis_tablename is None or layer_mapping.destinationLayerName() != qgis_tablename:
            layer_mapping.clearFieldMapping()
        
        # Add or update field mapping
        if qgis_layer is not None:
            destination_fields = qgis_layer.dataProvider().fields()
            for field in destination_fields:
                # Skip PK field
                if field.name() == PagLuxembourg.project.PK:
                    continue
                
                # Add or update mapping for every fields
                source, destination, constant_value, enabled = layer_mapping.getFieldMappingForDestination(field.name())
                if destination is None:
                    layer_mapping.addFieldMapping(None, field.name(), None, True)
        
        layer_mapping.setDestinationLayerName(qgis_tablename)
        
        return layer_mapping
        
        
    def _getLayerFromLayerName(self, layername):
        '''
        Gets the layer from the layer name
        '''
        
        for layer in self.qgislayers:
            if layer.name() == layername:
                return layer
        
        return None    
    
    def _getLayerFromTableName(self, tablename):
        '''
        Gets the layer from the table name
        '''
        
        for layer in self.qgislayers:
            if PagLuxembourg.main.current_project.getLayerTableName(layer) == tablename:
                return layer
        
        return None
        
    def _loadCurrentFieldMapping(self):
        '''
        Loads the current field mapping corresponding to the selected layers mapping
        '''
        
        # Current field mapping
        layer_mapping = self._getCurrentLayersMapping()
        
        # Clear the table
        self.tabFieldsMapping.clearContents()
        self.tabFieldsMapping.setRowCount(0)
        
        # If no destination layer, return
        if layer_mapping.destinationLayerName() is None:
            return
        
        qgis_layer = self._getLayerFromTableName(layer_mapping.destinationLayerName())
        qgis_fields = qgis_layer.dataProvider().fields()
        
        self.tabFieldsMapping.setRowCount(len(layer_mapping.fieldMappings()))
        
        rowindex = 0
        
        # Fill layers mapping
        for field in qgis_fields:
            # Skip PK field
            if field.name() == PagLuxembourg.project.PK:
                continue
                
            source, destination, constant_value, enabled = layer_mapping.getFieldMappingForDestination(field.name())
            
            self.tabFieldsMapping.setItem(rowindex, 0, QTableWidgetItem(destination)) # QGIS field
            self.tabFieldsMapping.setCellWidget(rowindex, 1, self._getTableItemWidget(qgis_layer, field)) # Constant value
            self.tabFieldsMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox(enabled)) # Enabled checkbox
            
            rowindex +=  1
        
        self.is_loading_mapping = False
    
    def _getTableItemWidget(self, layer, field):
        '''
        Gets the table widget corresponding to the current field
        
        :param layer: The QGIS layer
        :type layer: QgsVectorLayer
        
        :param field: The QGIS field
        :type field: QgsField
        '''
        
        return self._getCombobox([field.name()])
        
    def _launchImport(self):
        '''
        Launch the import
        '''
        pass
    
    def _loadConfig(self):
        '''
        Load a JSON configuration
        '''
        pass
        
    def _saveConfig(self):
        '''
        Save the configuration to JSON
        '''
        pass