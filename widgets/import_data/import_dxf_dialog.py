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
        self.tabLayersMapping.horizontalHeader().setResizeMode(QHeaderView.Stretch);
        self.tabFieldsMapping.setHorizontalHeaderLabels([QCoreApplication.translate('ImportDxfDialog','QGIS Field'),
                                                         QCoreApplication.translate('ImportDxfDialog','Value'),
                                                         QCoreApplication.translate('ImportDxfDialog','Enabled')])
        self.tabFieldsMapping.horizontalHeader().setResizeMode(QHeaderView.Stretch);
        
        # Load dxf layers
        self._loadDxfLayers(filename)
        
        # If not valid, return
        self.valid = self.dxflayer_points.isValid() or self.dxflayer_linestrings.isValid() or self.dxflayer_polygons.isValid()
        if not self.valid :
            return
        
        # Load the QGIS layers
        self._loadQgisLayers()
            
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
        
        self.dxflayers = list()
        
        self._loadUniqueLayersNames(self.dxflayer_points, self.dxflayers)
        self._loadUniqueLayersNames(self.dxflayer_linestrings, self.dxflayers)
        self._loadUniqueLayersNames(self.dxflayer_polygons, self.dxflayers)
        
        settings.setValue( "/Projections/defaultBehaviour", oldProjValue )
    
    def _loadUniqueLayersNames(self, layer, layernames):
        '''
        Retrieves unique layer names from the DXF
        
        :param layer: The layer to search values
        :type layer: QgsVectorLayer
        
        :param layernames: The existing unique layer names list
        :type layernames: list
        '''
        
        dp = layer.dataProvider()
        layerfield_index = dp.fields().fieldNameIndex('Layer')
        
        for feature in dp.getFeatures():
            value = feature[layerfield_index]
            
            if value not in layernames:
                layernames.append(value)
    
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
        
        qgislayer = self.qgislayers[self.cbbLayers.currentIndex()]
        qgislayer_fields = qgislayer.dataProvider().fields()
        
        current_item_index = 0
        selected_index = -1
        
        # Add all PAG layers to combobox
        for layer in self.qgislayers:
            self.combobox.addItem(layer.name())
            
            # Select layer
            if PagLuxembourg.main.current_project.getLayerTableName(layer) == selected_layer:
                selected_index = current_item_index
            
            current_item_index += 1
                
        combobox.setCurrentIndex(selected_index)
        
        return widget
        
    def _tabLayersMappingCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        pass
    
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