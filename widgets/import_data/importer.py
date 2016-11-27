'''
Created on 04 nov. 2015

@author: arxit
'''

import os.path
import json
from collections import OrderedDict
import uuid

from PyQt4.QtCore import QCoreApplication, QVariant, Qt, QDate, QDateTime, QSettings
from PyQt4.QtGui import QCheckBox, QWidget, QHBoxLayout, QComboBox, QDoubleSpinBox, QDateTimeEdit, QLineEdit, QPushButton, QFileDialog

from qgis.core import *
from qgis.gui import *

import PagLuxembourg.main
import PagLuxembourg.project
from PagLuxembourg.controls.filename import SimpleFilenamePicker

class Importer(object):
    '''
    Base class for the differents importers (GML, SHP, DXF)
    '''

    def __init__(self, filename):
        '''
        Constructor.
        '''
        self.import_filename = os.path.basename(filename.strip())
        
    def _startImportSession(self):
        self.importid = str(uuid.uuid1())
        self.import_date = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        self.imported_layers = set()
        self.imported_extent=None
        self.features_errors=[]
        self.commit_errors=[]
    
    def _commitImport(self):
        '''
        Add to import log
        '''
        
        importlog_layer = PagLuxembourg.main.current_project.getImportLogLayer()
        dst_feature = QgsFeature(importlog_layer.fields())
        dst_feature.setAttribute(1, self.importid)
        dst_feature.setAttribute(2, self.import_date)
        dst_feature.setAttribute(3, self.import_filename)
        dst_feature.setAttribute(4, "|".join(self.imported_layers))
        
        # Start editing session
        if not importlog_layer.isEditable():
            importlog_layer.startEditing()
        
        # Add features    
        importlog_layer.addFeatures([dst_feature], False)
        
        # Commit    
        if not importlog_layer.commitChanges():
            importlog_layer.rollBack()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('Importer','Error'), 
                                                                        QCoreApplication.translate('Importer','Commit error on layer {}').format(importlog_layer.name()))
            errors = importlog_layer.commitErrors()
            for error in errors:
                QgsMessageLog.logMessage(error, 'PAG Luxembourg', QgsMessageLog.CRITICAL)
            PagLuxembourg.main.qgis_interface.openMessageLog()
        
        '''
        Process import result
        '''
            
        # Zoom to selected
        if self.imported_extent is not None:
            PagLuxembourg.main.qgis_interface.mapCanvas().setExtent(self.imported_extent)
        
        PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
        
        # Display features errors
        if len(self.features_errors) > 0:
            messageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('Importer','Warning'), 
                                                                                      QCoreApplication.translate('Importer','Import was successful, but some features could not be imported'))
            btnExportCsv = QPushButton(QCoreApplication.translate('Importer','Export to CSV'))
            btnExportCsv.clicked.connect(self._exportErrorsToCsv)
            messageBar.layout().addWidget(btnExportCsv)
            PagLuxembourg.main.qgis_interface.messageBar().pushWidget(messageBar, QgsMessageBar.WARNING)
        
        # Display commit errors
        for error in self.commit_errors:
            messageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('Importer','Error'), 
                                                                                      error)
            btnOpenLog = QPushButton(QCoreApplication.translate('Importer','Open log'))
            btnOpenLog.clicked.connect(PagLuxembourg.main.qgis_interface.openMessageLog)
            messageBar.layout().addWidget(btnOpenLog)
            PagLuxembourg.main.qgis_interface.messageBar().pushWidget(messageBar, QgsMessageBar.CRITICAL)
            
        # Display success message
        if (len(self.features_errors) + len(self.commit_errors)) == 0:
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('Importer','Success'), 
                                                                       QCoreApplication.translate('Importer','Import was successful'))
        
    def _exportErrorsToCsv(self):
        # Select CSV file to export
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter('CSV file (*.csv)');
        dialog.setWindowTitle(QCoreApplication.translate('Importer','Select the csv location'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files)==0:
            return
        try:
            # CSV filename and directory
            csv_filename = selected_files[0]
            csvfile = open(csv_filename, 'wb')
            
            # Header
            csvfile.write(';'.join(['Layer name', 'Feature ID', 'Message', 'Centroid X', 'Centroid Y']))
            csvfile.write('\n')
            
            # Iterate errors
            for layer, featureid, messsage, centroid in self.features_errors:
                row = []
                
                # Feature info
                row.append(layer)
                row.append(str(featureid))
                row.append(messsage)
                    
                # Centroid
                if centroid is not None:
                    row.append(str(centroid.x()))
                    row.append(str(centroid.y()))
                               
                csvfile.write(';'.join(row).encode('UTF-8'))
                csvfile.write('\n')
                
            csvfile.close()
            
            # Success message
            PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('Importer','Success'),
                                                                       QCoreApplication.translate('Importer','CSV export was successful'))
        except:
            # Error message
            PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('Importer','Error'),
                                                                        QCoreApplication.translate('Importer','Error writing CSV file'))
        
    def _importLayer(self, src_layer, dst_layer, mapping, progressbar = None):
        '''
        Launch the import
        '''
        
        src_dp = src_layer.dataProvider()
        dst_dp = dst_layer.dataProvider()
        dst_layer_fields = dst_dp.fields()
        newfeatures = list()
        
        feature_request = None
        
        importid_index = dst_layer.fieldNameIndex(PagLuxembourg.project.IMPORT_ID)
        
        # Set layer filter if existing, for DXF
        if mapping.sourceLayerFilter() is None:
            feature_request = QgsFeatureRequest()
        else:
            expr = QgsExpression(mapping.sourceLayerFilter())
            feature_request = QgsFeatureRequest(expr)
            
        # Explode multi-parts
        source_features = list()
        
        for src_feature in src_dp.getFeatures(feature_request):
            if dst_layer.geometryType()== QGis.NoGeometry:
                source_features.append(src_feature)
                continue
            
            geometry = src_feature.geometry()
            
            # Check if geometry is empty
            if geometry is None or geometry.isEmpty():
                self.features_errors.append((
                                         mapping.sourceLayerName() if mapping.sourceLayerName() is not None else src_layer.name(),
                                         src_feature.id(),
                                         QCoreApplication.translate('Importer','Geometry is empty'),
                                         None
                                         ))
                continue
            
            # Check if feature geometry is multipart
            if geometry.isMultipart():
                temp_feature = QgsFeature(src_feature)
                # create a new feature using the geometry of each part
                for part in geometry.asGeometryCollection():
                    temp_feature.setGeometry(part)
                    source_features.append(QgsFeature(temp_feature))
            else:
                source_features.append(src_feature)
        
        # Iterate source features
        for src_feature in source_features:
            dst_feature = QgsFeature(dst_layer_fields)
            for src_index, dst_index, constant_value, enabled, value_map in mapping.fieldMappings():
                value = constant_value if src_index is None else src_feature[src_index]
                
                # Manage value map
                for shp, qgis in value_map:
                    if value == shp:
                        value = qgis
                
                # Check if numeric value needs to be casted
                if value == NULL or value is None:
                    dst_feature.setAttribute(dst_index, NULL)
                elif dst_feature.fields()[dst_index].type() == QVariant.String and not isinstance(value, basestring):
                    dst_feature.setAttribute(dst_index, str(value))
                else:
                    dst_feature.setAttribute(dst_index, value)
            
            if dst_layer.hasGeometryType():
                # Import closed polylines as polygon
                if dst_layer.geometryType() == QGis.Polygon and src_layer.geometryType() == QGis.Line:
                    src_polyline = src_feature.geometry().asPolyline()
                    if len(src_polyline)==0:
                        del dst_feature
                        continue
                    
                    if src_polyline[0] == src_polyline[-1]:
                        # It's a closed polyline
                        src_polygon = QgsGeometry.fromPolygon([src_polyline])
                        src_geometry = self._validateGeometry(
                                                              mapping.sourceLayerName(), 
                                                              src_polygon, 
                                                              src_feature.id())
                        if src_geometry is None:
                            del dst_feature
                            continue
                        
                        dst_feature.setGeometry(src_geometry)
                    else:
                        # It's a classical polyline, skip
                        del dst_feature
                        continue
                else:
                    src_geometry = self._validateGeometry(
                                                          mapping.sourceLayerName() if mapping.sourceLayerName() is not None else src_layer.name(), 
                                                          src_feature.geometry(), 
                                                          src_feature.id())
                    if src_geometry is None:
                        del dst_feature
                        continue
                    
                    dst_feature.setGeometry(src_geometry)
                
                # Update imported extent
                if self.imported_extent is None:
                    self.imported_extent = src_geometry.boundingBox()
                else:
                    self.imported_extent.combineExtentWith(src_geometry.boundingBox())
            
            
            # Add import ID
            dst_feature.setAttribute(importid_index, self.importid)
            
            # Add feature to new features list
            newfeatures.append(dst_feature)
            
            # Increment progress bar
            if progressbar is not None:
                progressbar.setValue(progressbar.value() + 1)
        
        # Start editing session
        if not dst_layer.isEditable():
            dst_layer.startEditing()
        
        # Add features    
        dst_layer.addFeatures(newfeatures, True)
        
        # Commit    
        if dst_layer.commitChanges():
            # Add layer to imported layers
            self.imported_layers.add(dst_layer.name())
        else:
            dst_layer.rollBack()
            self.commit_errors.append(QCoreApplication.translate('Importer','Commit error on layer {}').format(dst_layer.name()))
            errors = dst_layer.commitErrors()
            for error in errors:
                QgsMessageLog.logMessage(error, 'Import {}'.format(self.import_filename), QgsMessageLog.CRITICAL)
            
        # Reload layer
        dst_layer.reload()
        
    def _validateGeometry(self, layer_name, geometry, feature_id):
        clean_geometry = self._getCleanGeometry(geometry)
        
        if clean_geometry is None:
            self.features_errors.append((
                                         layer_name,
                                         feature_id,
                                         QCoreApplication.translate('Importer','Invalid geometry, maybe all vertices have the same coordinates'),
                                         self._getCentroid(geometry)
                                         ))
            return None
        
        errors = clean_geometry.validateGeometry()
                    
        for error in errors:
            self.features_errors.append((
                                         layer_name,
                                         feature_id,
                                         error.what(),
                                         error.where()
                                         ))
        
        return clean_geometry if len(errors) == 0 else None
    
    def _getCleanGeometry(self, geometry, simplify_tolerance=0):
        if geometry is None:
            return None
        
        clean_geometry = geometry.simplify(simplify_tolerance)
        
        if clean_geometry is None:
            return None
        
        # Simplify seems to corrupt some geometries, so we have to recreate the geometry
        if geometry.type() == QGis.Point:
            return QgsGeometry.fromPoint(clean_geometry.asPoint())
        elif geometry.type() == QGis.Line:
            return QgsGeometry.fromPolyline(clean_geometry.asPolyline())
        elif geometry.type() == QGis.Polygon:
            return QgsGeometry.fromPolygon(clean_geometry.asPolygon())
        
        return None
    
    def _getCentroid(self, geometry):
        try:
            return geometry.centroid().asPoint()
        except:
            return None
    
    def _getFieldsMappingTableItemWidget(self, layer, fieldname, value, secondary_value = None):
        '''
        Gets the table widget corresponding to the current field
        
        :param layer: The QGIS layer
        :type layer: QgsVectorLayer
        
        :param field: The QGIS field
        :type field: QgsField
        '''
        
        field_index = layer.fieldNameIndex(fieldname)
        
        # Field editor is ValueMap
        if layer.editorWidgetV2(field_index) == 'ValueMap':
            config = layer.editorWidgetV2Config(field_index)
            config = dict((v, k) for k, v in config.iteritems())
            ordered_config = OrderedDict(sorted(config.items(), key=lambda t: t[1]))
            return self._getCombobox(ordered_config, value, secondary_value)
        
        # Field editor is range
        elif layer.editorWidgetV2(field_index) == 'PreciseRange':
            config = layer.editorWidgetV2Config(field_index)
            return self._getSpinbox(config['Min'], config['Max'], config['Step'], config['AllowNull'], value)
        
        # Field editor is datetime
        elif layer.editorWidgetV2(field_index) == 'DateTime':
            config = layer.editorWidgetV2Config(field_index)
            return self._getCalendar(config['display_format'], value)
        
        # Field editor is simple filename
        elif layer.editorWidgetV2(field_index) == 'SimpleFilename':
            return self._getSimpleFilenamePicker(value)
        
        # Other editors
        return self._getTextbox(value)
    
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
    
    def _setCheckboxChecked(self, table, row, column, checked = True):
        '''
        Set the checked status of a checkbox in a table
        '''
        
        # It is a widget
        for child in table.cellWidget(row, column).children():
            if type(child) is QCheckBox:
                child.setChecked(checked)
                return
        
        raise TypeError('No widget found')
    
    def _setTableCheckboxChecked(self, table, column, checked = True):
        '''
        Set the checked status of all checkboxes in a table
        '''
        
        for row in range(table.rowCount()):
            self._setCheckboxChecked(table, row, column, checked)
    
    def _getCombobox(self, values, primary_selected_value = None, secondary_selected_value = None, currentindex_changed_callback = None):
        '''
        Get a combobox filled with the given values
        
        :param values: The values as key = value, value = description or text
        :type values: Dict
        
        :returns: A combobox
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
        selected_index = 0
        
        for key, value in values.iteritems():
            combobox.addItem(value, key)
            
            # Select value
            if key == secondary_selected_value and selected_index == 0:
                selected_index = current_item_index
            if key == primary_selected_value:
                selected_index = current_item_index
                
            current_item_index += 1
        
        combobox.setCurrentIndex(selected_index)
            
        if currentindex_changed_callback is not None:
            combobox.currentIndexChanged.connect(currentindex_changed_callback)
                
        return widget
    
    def _getSpinbox(self, minvalue, maxvalue, step, nullable = True, value = 0):
        '''
        Get a combobox filled with the given values
        
        :param values: The values as key = value, value = description or text
        :type values: Dict
        
        :returns: A combobox
        :rtype: QWidget
        '''
        
        widget = QWidget()
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(minvalue)
        spinbox.setMaximum(maxvalue)
        spinbox.setSingleStep(step)
        spinbox.setDecimals(len(str(step).split('.')[1]) if len(str(step).split('.'))==2 else 0)
        if nullable:
            spinbox.setMinimum(minvalue - step)
            spinbox.setValue(spinbox.minimum())
            spinbox.setSpecialValueText(str(QSettings().value('qgis/nullValue', 'NULL' )))
        if value is not None:
            spinbox.setValue(value)
        layout = QHBoxLayout(widget)
        layout.addWidget(spinbox, 1);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(5,0,5,0);
        widget.setLayout(layout);
                
        return widget
    
    def _getCalendar(self, display_format, value = None):
        '''
        Get a combobox filled with the given values
        
        :param values: The values as key = value, value = description or text
        :type values: Dict
        
        :returns: A combobox
        :rtype: QWidget
        '''
        
        
        widget = QWidget()
        calendar = QDateTimeEdit()
        calendar.setCalendarPopup(True)
        calendar.setDisplayFormat(display_format)
        if value is not None:
            calendar.setDate(QDate.fromString(value, display_format))
        else:
            calendar.setDate(QDate.currentDate())
        layout = QHBoxLayout(widget)
        layout.addWidget(calendar, 1);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(5,0,5,0);
        widget.setLayout(layout);
                
        return widget
    
    def _getTextbox(self, value = None):
        '''
        Get a combobox filled with the given values
        
        :param values: The values as key = value, value = description or text
        :type values: Dict
        
        :returns: A combobox
        :rtype: QWidget
        '''
        
        widget = QWidget()
        textbox = QLineEdit()
        textbox.setText(value)
        layout = QHBoxLayout(widget)
        layout.addWidget(textbox, 1);
        layout.setAlignment(Qt.AlignCenter);
        layout.setContentsMargins(5,0,5,0);
        widget.setLayout(layout);
                
        return widget
    
    def _getSimpleFilenamePicker(self, value = None):
        '''
        Get a combobox filled with the given values
        
        :param values: The filename
        :type values: str
        
        :returns: A simple filename picker
        :rtype: SimpleFilenamePicker
        '''
        
        widget = SimpleFilenamePicker()
        widget.setValue(value)
                
        return widget
    
    def _getCellValue(self, table, row, column):
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
        
        # Check whether it is an item
        item = table.item(row, column)
        if item is not None:
            text = item.text().strip()
            return text if not text == '' else None
        
        # It is a widget
        widget = table.cellWidget(row, column)
        if type(widget) is SimpleFilenamePicker:
            return widget.value()
        
        for child in widget.children():
            if type(child) is QCheckBox:
                return child.isChecked()
            elif type(child) is QComboBox:
                return child.itemData(child.currentIndex())
            elif type(child) is SimpleFilenamePicker:
                return child.value()
            elif type(child) is QLineEdit:
                text = child.text().strip()
                return text if not text == '' else None
            elif type(child) is QDoubleSpinBox:
                value = child.value()
                if value == child.minimum() and child.specialValueText() != '':
                    return None
                else:
                    return value
            elif type(child) is QDateTimeEdit:
                return child.date().toString(child.displayFormat())
        
        raise TypeError('No widget found')
    
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
    
    def getLayerMappingForSource(self, source_layer):
        for mapping in self._mappings:
            if mapping.sourceLayerName() == source_layer:
                return mapping
        
        return None
        
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
        self.setEnabled(True)
        self.setValid(False)
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
        
    def isEnabled(self):
        return self._mapping['Enabled']
        
    def setEnabled(self, enabled):
        self._mapping['Enabled'] = enabled
        
    def isValid(self):
        return self._mapping['Valid']
        
    def setValid(self, enabled):
        self._mapping['Valid'] = enabled
    
    def fieldMappings(self):
        return self._mapping['FieldMapping']
    
    def getFieldMappingForSource(self, source_fieldname):
        for source, destination, constant_value, enabled, value_map in self._mapping['FieldMapping']:
            if source == source_fieldname:
                return source, destination, constant_value, enabled, value_map
        
        return None, None, None, None, None
    
    def getFieldMappingForDestination(self, destination_fieldname):
        for source, destination, constant_value, enabled, value_map in self._mapping['FieldMapping']:
            if destination == destination_fieldname:
                return source, destination, constant_value, enabled, value_map
        
        return None, None, None, None, None
    
    def getValueMapForDestination(self, destination_fieldname):
        for source, destination, constant_value, enabled, value_map in self._mapping['FieldMapping']:
            if destination == destination_fieldname:
                return value_map
        
        return []
    
    def asIndexFieldMappings(self, destination_fields, source_fields=None):
        mapping = LayerMapping()
        mapping.setSourceLayerName(self.sourceLayerName())
        mapping.setDestinationLayerName(self.destinationLayerName())
        mapping.setSourceLayerFilter(self.sourceLayerFilter())
        mapping.setEnabled(self.isEnabled())
        mapping.setValid(self.isValid())
        
        for source, destination, constant_value, enabled, value_map in self.fieldMappings():
            mapping.addFieldMapping(
                                    source_fields.fieldNameIndex(source) if source is not None else source, 
                                    destination_fields.fieldNameIndex(destination), 
                                    constant_value, 
                                    enabled,
                                    value_map)
        
        return mapping
        
    def addFieldMapping(self, source, destination, constant_value, enabled, value_map = []):
        self._mapping['FieldMapping'].append((source, destination, constant_value, enabled, value_map))
    
    def clearFieldMapping(self):
        del self._mapping['FieldMapping'][:]
        
    def asDictionary(self):
        return self._mapping