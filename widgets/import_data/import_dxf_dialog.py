'''
Created on 05 nov. 2015

@author: arxit
'''
from __future__ import absolute_import

from builtins import range
import os

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QCheckBox, QWidget, QHBoxLayout, QComboBox, QProgressBar
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QCoreApplication, Qt, QVariant, QSettings

from qgis.core import *
from qgis.utils import *

import PagLuxembourg.main
import PagLuxembourg.project

from .importer import *
from collections import OrderedDict

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_dxf_dialog.ui'))


class ImportDxfDialog(QDialog, FORM_CLASS, Importer):
    def __init__(self, filename, parent=None):
        '''
        Constructor.
        '''

        super(ImportDxfDialog, self).__init__(parent)
        Importer.__init__(self, filename)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # Filename
        self.lblFilename.setText(filename)

        # Setup tables
        self.tabLayersMapping.setHorizontalHeaderLabels([QCoreApplication.translate('ImportDxfDialog', 'DXF Layer'),
                                                         QCoreApplication.translate('ImportDxfDialog', 'QGIS Layer'),
                                                         QCoreApplication.translate('ImportDxfDialog', 'Enabled')])
        self.tabLayersMapping.setColumnWidth(0, 460)
        self.tabLayersMapping.setColumnWidth(1, 200)
        self.tabFieldsMapping.setHorizontalHeaderLabels([QCoreApplication.translate('ImportDxfDialog', 'QGIS Field'),
                                                         QCoreApplication.translate('ImportDxfDialog', 'Value'),
                                                         QCoreApplication.translate('ImportDxfDialog', 'Enabled')])
        self.tabFieldsMapping.setColumnWidth(0, 200)
        self.tabFieldsMapping.setColumnWidth(1, 460)

        # Load dxf layers
        self._loadDxfLayers(filename)

        # If DXF is not valid, return
        if not self.valid :
            return

        # Don't trigger events if loading from config file
        self.is_loading_mapping = False

        # Load the QGIS layers
        self._loadQgisLayers()

        # Load the default mapping
        self.mapping = Mapping()

        self._loadLayersMapping()

    def _toggleLayersMappingCheckboxes(self):
        self._setTableCheckboxChecked(self.tabLayersMapping, 2, self.chkEnableAllLayersMapping.isChecked())

    def _toggleFieldsMappingCheckboxes(self):
        self._setTableCheckboxChecked(self.tabFieldsMapping, 2, self.chkEnableAllFieldsMapping.isChecked())

    def _loadQgisLayers(self):
        '''
        Loads the QGIS layers
        '''

        self.qgislayers = list()

        # Adds the PAG map layers
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        #for layer in PagLuxembourg.main.qgis_interface.legendInterface().layers():
        for layer in layers:
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

        self.dxflayer_points = QgsVectorLayer(u'{}|layername=entities|geometrytype=Point'.format(filename), 'Points', 'ogr')
        self.dxflayer_linestrings = QgsVectorLayer(u'{}|layername=entities|geometrytype=LineString'.format(filename), 'LineString', 'ogr')
        self.dxflayer_polygons = QgsVectorLayer(u'{}|layername=entities|geometrytype=Polygon'.format(filename), 'Polygon', 'ogr')

        self.valid = self.dxflayer_points.isValid() or self.dxflayer_linestrings.isValid() or self.dxflayer_polygons.isValid()

        if not self.valid:
            return

        self.dxf_layernames = list()

        self._loadUniqueLayersNames(self.dxflayer_points)
        self._loadUniqueLayersNames(self.dxflayer_linestrings)
        self._loadUniqueLayersNames(self.dxflayer_polygons)

        # Restore project settings
        settings.setValue( "/Projections/defaultBehaviour", oldProjValue )

    def _loadUniqueLayersNames(self, layer):
        '''
        Retrieves unique layer names from the DXF

        :param layer: The layer to search values
        :type layer: QgsVectorLayer
        '''

        dp = layer.dataProvider()
        layerfield_index = dp.fields().indexFromName('Layer')

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

        layers = OrderedDict()

        for layer in self.qgislayers:
            layers[PagLuxembourg.main.current_project.getLayerTableName(layer)]=layer.name()

        return self._getCombobox(layers,
                                 primary_selected_value=selected_layer,
                                 currentindex_changed_callback=self._comboboxQgisLayersIndexChanged)

    def _getLayerMappingFromSourceDxfLayer(self, dxf_layername):
        '''

        '''

        layer_mapping = self.mapping.getLayerMappingForSource(dxf_layername)

        if layer_mapping is None:
            layer_mapping = LayerMapping()
            layer_mapping.setSourceLayerName(dxf_layername)
            layer_mapping.setSourceLayerFilter(u'Layer=\'{}\''.format(dxf_layername.replace('\'', '\'\'')))
            self.mapping.addLayerMapping(layer_mapping)

        return layer_mapping

    def _loadLayersMapping(self):
        '''
        Loads the layers mapping
        '''

        self.is_loading_mapping = True

        # Clear the table
        self.tabLayersMapping.clearContents()
        self.tabLayersMapping.setRowCount(len(self.dxf_layernames))
        self.tabFieldsMapping.clearContents()
        self.tabFieldsMapping.setRowCount(0)

        rowindex = 0

        # Fill layers mapping
        for dxf_layername in self.dxf_layernames:
            layer_mapping = self._getLayerMappingFromSourceDxfLayer(dxf_layername)

            self.tabLayersMapping.setItem(rowindex, 0, QTableWidgetItem(dxf_layername)) # DXF layer name
            self.tabLayersMapping.setCellWidget(rowindex, 1, self._getQgisLayersCombobox(layer_mapping.destinationLayerName())) # QGIS layers
            self.tabLayersMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox(layer_mapping.isEnabled())) # Enabled checkbox

            rowindex +=  1

        self.is_loading_mapping = False

    def _tabLayersMappingCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):

        if self.is_loading_mapping:
            return

        # Update mapping
        self._updateMappingFromUI(previousRow)

        # Load mapping into the table
        self._loadCurrentFieldMapping()

    def _comboboxQgisLayersIndexChanged(self, index):
        # Get the row of the combobox which changed
        rowindex = 0

        for i in range(self.tabLayersMapping.rowCount()):
            if self.tabLayersMapping.cellWidget(i, 1) is self.sender().parent():
                rowindex = i

        # Layer mapping corresponding to the selected row
        self._updateAndGetFieldsMapping(rowindex)

        if rowindex == self.tabLayersMapping.currentRow():
            self._loadCurrentFieldMapping()

    def _updateAndGetFieldsMapping(self, layersmapping_rowindex = None):
        '''
        Gets the current field mapping corresponding to the selected layers mapping
        '''

        if layersmapping_rowindex is None:
            layersmapping_rowindex = self.tabLayersMapping.currentRow()

        dxf_layername = self._getCellValue(self.tabLayersMapping, layersmapping_rowindex, 0)
        qgis_layer = self._getQgisLayerFromTableName(self._getCellValue(self.tabLayersMapping, layersmapping_rowindex, 1))
        qgis_tablename = PagLuxembourg.main.current_project.getLayerTableName(qgis_layer)

        layer_mapping = self._getLayerMappingFromSourceDxfLayer(dxf_layername)

        # Check whether the destination layer is the same
        if qgis_tablename is None or layer_mapping.destinationLayerName() != qgis_tablename:
            layer_mapping.clearFieldMapping()
            layer_mapping.setValid(False)

        # Add or update field mapping
        if qgis_layer is not None:
            destination_fields = qgis_layer.dataProvider().fields()
            for field in destination_fields:
                # Skip PK field
                if field.name() == PagLuxembourg.project.PK:
                    continue
                # Skip IMPORT_ID field
                if field.name() == PagLuxembourg.project.IMPORT_ID:
                    continue

                # Add or update mapping for every fields
                source, destination, constant_value, enabled, valuemap = layer_mapping.getFieldMappingForDestination(field.name())
                if destination is None:
                    layer_mapping.addFieldMapping(None, field.name(), None, True, valuemap)

        layer_mapping.setDestinationLayerName(qgis_tablename)

        return layer_mapping

    def _getQgisLayerFromLayerName(self, layername):
        '''
        Gets the layer from the layer name
        '''

        for layer in self.qgislayers:
            if layer.name() == layername:
                return layer

        return None

    def _getQgisLayerFromTableName(self, tablename):
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
        layer_mapping = self._updateAndGetFieldsMapping()

        # Clear the table
        self.tabFieldsMapping.clearContents()
        self.tabFieldsMapping.setRowCount(0)

        # If no destination layer, return
        if layer_mapping.destinationLayerName() is None:
            return

        qgis_layer = self._getQgisLayerFromTableName(layer_mapping.destinationLayerName())
        qgis_fields = qgis_layer.dataProvider().fields()

        # Update label
        self.lblCurrentFieldMapping.setText(QCoreApplication.translate('ImportDxfDialog', 'Mapping for DXF layer "{}" to QGIS layer "{}"').format(layer_mapping.sourceLayerName(), qgis_layer.name()))


        self.tabFieldsMapping.setRowCount(len(layer_mapping.fieldMappings()))

        rowindex = 0

        # Fill layers mapping
        for field in qgis_fields:
            # Skip PK field
            if field.name() == PagLuxembourg.project.PK:
                continue
            # Skip IMPORT_ID field
            if field.name() == PagLuxembourg.project.IMPORT_ID:
                continue

            source, destination, constant_value, enabled, valuemap = layer_mapping.getFieldMappingForDestination(field.name())

            self.tabFieldsMapping.setItem(rowindex, 0, QTableWidgetItem(destination)) # QGIS field
            self.tabFieldsMapping.setCellWidget(rowindex, 1, self._getFieldsMappingTableItemWidget(qgis_layer, field.name(), constant_value)) # Constant value
            self.tabFieldsMapping.setCellWidget(rowindex, 2, self._getCenteredCheckbox(enabled)) # Enabled checkbox

            rowindex +=  1

        layer_mapping.setValid(True)

    def _updateMappingFromUI(self, layersmapping_rowindex = None):

        if layersmapping_rowindex is None:
            layersmapping_rowindex = self.tabLayersMapping.currentRow()

        newmapping = Mapping()

        for layermapping_rowindex in range(self.tabLayersMapping.rowCount()):
            dxf_layername = self._getCellValue(self.tabLayersMapping, layermapping_rowindex, 0)

            # Layer mapping
            layer_mapping = self._getLayerMappingFromSourceDxfLayer(dxf_layername)

            qgis_layer = self._getQgisLayerFromTableName(self._getCellValue(self.tabLayersMapping, layermapping_rowindex, 1))
            qgis_tablename = PagLuxembourg.main.current_project.getLayerTableName(qgis_layer)

            # Check whether the destination layer is the same
            if qgis_tablename is None or layer_mapping.destinationLayerName() != qgis_tablename:
                layer_mapping.clearFieldMapping()

            # Set destination table name
            layer_mapping.setDestinationLayerName(qgis_tablename)

            # Set is enabled
            layer_mapping.setEnabled(self._getCellValue(self.tabLayersMapping, layermapping_rowindex, 2))

            # If row is selected, update field mapping
            if layermapping_rowindex == layersmapping_rowindex:
                layer_mapping.clearFieldMapping()
                for field_rowindex in range(self.tabFieldsMapping.rowCount()):
                    qgis_field = self._getCellValue(self.tabFieldsMapping, field_rowindex, 0)
                    value = self._getCellValue(self.tabFieldsMapping, field_rowindex, 1)
                    enabled = self._getCellValue(self.tabFieldsMapping, field_rowindex, 2)
                    layer_mapping.addFieldMapping(None, qgis_field, value[1] if type(value) is tuple else value, enabled)

            newmapping.addLayerMapping(layer_mapping)

        del self.mapping
        self.mapping = newmapping

    def _validateMapping(self):
        '''
        Validate the mapping

        :returns: True if the mapping is valid
        :rtype: Boolean
        '''

        self._updateMappingFromUI()

        # Loop layer mappings to check whether it is valid
        for layer_mapping in self.mapping.layerMappings():
            if layer_mapping.isEnabled() and not layer_mapping.isValid():
                QMessageBox.critical(
                    self,
                    QCoreApplication.translate('ImportDxfDialog', 'Error'),
                    QCoreApplication.translate('ImportDxfDialog', 'Mapping for DXF layer {} is not valid, please check it again.').format(layer_mapping.sourceLayerName())
                )
                return False

        return True

    def _launchImport(self):
        '''
        Launch the import
        '''

        if not self._validateMapping():
            return

        self.close()

        # Progress bar + message
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('ImportDxfDialog','Importing DXF'))
        progress = QProgressBar()
        progress.setMaximum(self._getEnabledLayerMappingCount())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        progress2 = QProgressBar()
        progress2.setMaximum(self.dxflayer_points.featureCount() + self.dxflayer_linestrings.featureCount() + self.dxflayer_polygons.featureCount())
        progress2.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress2)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, 0) # QGis.Info = 0

        # Start import session
        self._startImportSession()

        for layer_mapping in self.mapping.layerMappings():
            # Skip if not enabled
            if not layer_mapping.isEnabled():
                continue

            # Progression message
            progressMessageBar.setText(QCoreApplication.translate('ImportDxfDialog', 'Importing {}').format(layer_mapping.sourceLayerName()))

            # QGIS layer
            qgis_layer = self._getQgisLayerFromTableName(layer_mapping.destinationLayerName())

            layer_indexmapping = layer_mapping.asIndexFieldMappings(qgis_layer.dataProvider().fields())

            progress2.setValue(0)

            # Import features according to geometry type
            if qgis_layer.wkbType() == QgsWkbTypes.Point:
                self._importLayer(self.dxflayer_points, qgis_layer, layer_indexmapping, progress2)
            elif qgis_layer.wkbType() == QgsWkbTypes.LineGeometry:
                self._importLayer(self.dxflayer_linestrings, qgis_layer, layer_indexmapping, progress2)
            elif qgis_layer.wkbType() == QgsWkbTypes.LineString:
                self._importLayer(self.dxflayer_linestrings, qgis_layer, layer_indexmapping, progress2)
            elif qgis_layer.wkbType() == QgsWkbTypes.Polygon:
                self._importLayer(self.dxflayer_linestrings, qgis_layer, layer_indexmapping, progress2)
                self._importLayer(self.dxflayer_polygons, qgis_layer, layer_indexmapping, progress2)

        # Commit import session
        self._commitImport()

    def _getEnabledLayerMappingCount(self):
        count = 0

        for layer_mapping in self.mapping.layerMappings():
            if layer_mapping.isEnabled():
                count += 1

        return count

    def _loadConfig(self):
        '''
        Load a JSON configuration
        '''

        # Select config file to load
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setOption(QFileDialog.ReadOnly)
        dialog.setNameFilter('Json file (*.json)')
        dialog.setWindowTitle(QCoreApplication.translate('ImportDxfDialog', 'Select the configuration file to load'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()

        if result == 0:
            return

        selected_files = dialog.selectedFiles()

        if len(selected_files)==0:
            return

        filename = selected_files[0]

        # Load mapping
        self.mapping.parseJson(filename)

        self._loadLayersMapping()

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
        dialog.setNameFilter('Json file (*.json)')
        dialog.setWindowTitle(QCoreApplication.translate('ImportDxfDialog', 'Select the json location'))
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
        self.mapping.writeJson(filename)

        QMessageBox.information(self,
                                QCoreApplication.translate('ImportDxfDialog', 'Success'),
                                QCoreApplication.translate('ImportDxfDialog', 'Mapping configuration saved'))