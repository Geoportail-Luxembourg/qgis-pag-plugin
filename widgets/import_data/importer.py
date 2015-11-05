'''
Created on 04 nov. 2015

@author: arxit
'''
import json

from PyQt4.QtCore import QCoreApplication, QVariant

from qgis.core import *

import PagLuxembourg.main

class Importer(object):
    '''
    Base class for the differents importers (GML, SHP, DXF)
    '''

    def _importLayer(self, src_layer, dst_layer, mapping):
        '''
        Launch the import
        '''
        
        src_dp = src_layer.dataProvider()
        dst_dp = dst_layer.dataProvider()
        dst_layer_fields = dst_dp.fields()
        newfeatures = list()
        
        # Iterate source features
        for src_feature in src_dp.getFeatures():
            dst_feature = QgsFeature(dst_layer_fields)
            for src_index, dst_index, constant_value, enabled in mapping.fieldMappings():
                value = constant_value if constant_value is not None else src_feature[src_index]
                
                # Check if numeric value needs to be casted
                if value == NULL:
                    dst_feature.setAttribute(dst_index, NULL)
                elif dst_feature.fields()[dst_index].type() == QVariant.String and not isinstance(value, basestring):
                    dst_feature.setAttribute(dst_index, str(value))
                else:
                    dst_feature.setAttribute(dst_index, value)
            
            if dst_layer.hasGeometryType():
                # TODO closed polylines
                dst_feature.setGeometry(src_feature.geometry())
            
            newfeatures.append(dst_feature)
        
        # Start editing session
        if not dst_layer.isEditable():
            dst_layer.startEditing()
        
        # Add features    
        dst_layer.addFeatures(newfeatures, True)
        
        # Commit    
        if not dst_layer.commitChanges():
            dst_layer.rollBack()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('Importer','Error'), 
                                                                        QCoreApplication.translate('Importer','Commit error on layer {}').format(qgis_layer.name()))
            return None
        
        # Reload layer
        dst_layer.reload()
        
        # Return extent
        return src_layer.extent()
    
        # Zoom to selected
        PagLuxembourg.main.qgis_interface.mapCanvas().zoomToSelected(dst_layer)
        
        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ImportShpDialog','Success'), 
                                                                   QCoreApplication.translate('ImportShpDialog','Importation was successful'))
        
    def _getCenteredCheckbox(self, checked = True):
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
    
    def _isCheckboxChecked(self, table, row, column):
        '''
        Get the checked state of the checkbox at the given row for a given table
        
        :param table: The table
        :type table: QTableWidget
        
        :param row: The row index
        :type row: Int
        
        :param column: The column index
        :type column: Int
        
        :returns: True if checked
        :rtype: Boolean
        '''
        
        for child in table.cellWidget(row, column).children():
            if type(child) is QCheckBox:
                return child.isChecked()
        
        raise TypeError('No checkbox found')
    
    def _getComboboxText(self, table, row, column):
        '''
        Get the selected combobox text
        
        :param table: The table
        :type table: QTableWidget
        
        :param row: The row index
        :type row: Int
        
        :param column: The column index
        :type column: Int
        
        :returns: The selected QGIS field name
        :rtype: QString, str
        '''
        
        for child in table.cellWidget(row, column).children():
            if type(child) is QComboBox:
                return child.currentText()
        
        raise TypeError('No combobox found')
    
class Mapping(object):
    '''
    Defines a complete mapping
    Contains one or more layer mapping
    '''

    def __init__(self):
        '''
        Constructor
        '''
        
        self._mappings = list()
    
    def layerMappings(self):
        return self._mappings
        
    def addLayerMapping(self, mapping):
        self._mappings.append(mapping)
    
    def writeJson(self, filename):
        mappings = list()
        
        for mapping in self._mappings:
            mappings.append(mapping.asDictionary())
        
        file = open(filename, 'wb')
        file.write(json.dumps(mappings))
        file.close()
    
    def parseJson(self, filename):
        f = open(filename, 'r')
        content = f.read()
        f.close()
        mappings = json.loads(content)
        
        del self._mappings[:]
        
        for mapping in mappings:
            self._mappings.append(LayerMapping(mapping))
        
class LayerMapping(object):
    '''
    Defines a complete mapping
    Contains one or more layer mapping
    '''

    def __init__(self, mapping = None):
        '''
        Constructor
        '''
        
        if mapping is not None:
            self._mapping = mapping
            return
        
        self._mapping = dict()
        self.setSourceLayerName(None)
        self.setDestinationLayerName(None)
        self.setSourceLayerFilter(None)
        self._mapping['FieldMapping'] = list()
    
    def sourceLayerName(self):
        return self._mapping['SourceLayerName']
        
    def setSourceLayerName(self, name):
        self._mapping['SourceLayerName'] = name
    
    def destinationLayerName(self):
        return self._mapping['DestinationLayerName']
        
    def setDestinationLayerName(self, name):
        self._mapping['DestinationLayerName'] = name
        
    def sourceLayerFilter(self):
        return self._mapping['SourceLayerFilter']
        
    def setSourceLayerFilter(self, filter):
        self._mapping['SourceLayerFilter'] = filter
    
    def fieldMappings(self):
        return self._mapping['FieldMapping']
    
    def getFieldMappingForSource(self, source_fieldname):
        for source, destination, constant_value, enabled in self._mapping['FieldMapping']:
            if source == source_fieldname:
                return source, destination, constant_value, enabled
        
        return None, None, None, None
        
    def addFieldMapping(self, source, destination, constant_value, enabled):
        self._mapping['FieldMapping'].append((source, destination, constant_value, enabled))
        
    def asDictionary(self):
        return self._mapping