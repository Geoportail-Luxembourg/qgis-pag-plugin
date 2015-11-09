'''
Created on 23 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from PyQt4.QtGui import QAction
from PyQt4.QtCore import QCoreApplication

from PagLuxembourg.schema import *
import PagLuxembourg.main

from error_summary_dialog import ErrorSummaryDialog

class DataChecker(object):
    '''
    Main class for the data checker widget
    '''

    def __init__(self):
        '''
        Constructor
        '''
    
    def run(self):
        '''
        Runs the widget
        
        :returns: True if there's no errors
        :rtype: Boolean
        '''
        
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        layer_structure_errors = list()
        data_errors = list()
        
        # Iterates through XSD types
        for type in PagLuxembourg.main.xsd_schema.types:
            layer = project.getLayer(type)
            
            if layer is None:
                continue
            
            warn_errors, fatal_errors = self.checkLayerStructure(layer, type)
            layer_structure_errors = layer_structure_errors + warn_errors + fatal_errors
            
            if len(fatal_errors)>0:
                continue
            
            layer_data_errors = self.checkLayerData(layer, type)
            data_errors.append(layer_data_errors)
        
        # Flatten data errors
        data_errors_flat = list()
        for layer, errors in data_errors:
            for feature, field, message in errors:
                data_errors_flat.append((layer, feature, field, message))
        
        valid = (len(layer_structure_errors) + len(data_errors_flat)) == 0
        
        if valid:
            PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('DataChecker','Success'),
                                                                       QCoreApplication.translate('DataChecker','No errors found.'))
        else:
            self.dlg = ErrorSummaryDialog(layer_structure_errors, data_errors)
            self.dlg.show()
        
        return valid 
        
    # Datatype mapping allowed while checking. For a given XSD type, several QGIS type may be allowed or compatible
    XSD_QGIS_ALLOWED_DATATYPE_MAP = [(DataType.STRING, QVariant.String),
                                     (DataType.STRING, QVariant.LongLong),
                                     (DataType.STRING, QVariant.Int),
                                     (DataType.STRING, QVariant.Double),
                                     (DataType.INTEGER, QVariant.LongLong),
                                     (DataType.INTEGER, QVariant.Int),
                                     (DataType.DOUBLE, QVariant.Double),
                                     (DataType.DOUBLE, QVariant.LongLong),
                                     (DataType.DOUBLE, QVariant.Int),
                                     (DataType.DATE, QVariant.String)]
    
    def checkLayerStructure(self, layer, xsd_type):
        '''
        Checks a layer structure against the XSD type
        Missing field, data type mismatch
        
        :param layer: The vector layer to check
        :type layer: QgsVectorLayer
        
        :param type: XSD schema type
        :type type: PAGType
        
        :returns: A list of warning and fatal error
        :rtype: Tuple : warning, fatal. Layer (QgsVectorLayer), field (PAGField), message (str, QString)
        '''
        
        layer_fields = layer.dataProvider().fields()
        warn_errors = list()
        fatal_errors = list()
        
        # Check geometry type
        if xsd_type.geometry_type is not None and XSD_QGIS_GEOMETRYTYPE_MAP[xsd_type.geometry_type] != layer.geometryType():
            fatal_errors.append((layer, None, QCoreApplication.translate('DataChecker','Geometry type mismatch, expected : {}').format(xsd_type.geometry_type)))
        
        # Check field structure
        for field in xsd_type.fields:
            # Check field missing
            layer_index = layer_fields.fieldNameIndex(field.name)
            if layer_index == -1:
                if field.nullable:
                    warn_errors.append((layer, field, QCoreApplication.translate('DataChecker','Nullable field is missing')))
                else:
                    warn_errors.append((layer, field, QCoreApplication.translate('DataChecker','Non nullable field is missing')))
                
                continue
            
            # Check field datatype
            layer_field = layer_fields[layer_index]
            found = False
            for xsd_type, qgis_type in self.XSD_QGIS_ALLOWED_DATATYPE_MAP:
                if layer_field.type() == qgis_type and field.type == xsd_type:
                    found = True
                    break
            
            if not found:
                fatal_errors.append((layer, field, QCoreApplication.translate('DataChecker','Field datatype mismatch, expected : {}').format(field.type)))
        
        return warn_errors, fatal_errors
    
    def checkLayerData(self, layer, xsd_type):
        '''
        Checks the data of a layer against the XSD type
        
        :param layer: The vector layer to check
        :type layer: QgsVectorLayer
        
        :param type: XSD schema type
        :type type: PAGType
        
        :returns: A list of data error
        :rtype: Tuples : Layer (QgsVectorLayer), list of tuple Feature (QgsFeature), field (PAGField), message (str, QString)
        '''
        
        errors = list()
        
        for feature in layer.dataProvider().getFeatures():
            errors += self.checkFeatureData(feature, xsd_type)
        
        return layer, errors
    
    def checkFeatureData(self, feature, xsd_type):
        '''
        Checks the data of a feature against the XSD type
        
        :param feature: The feature to check
        :type feature: QgsFeature
        
        :param type: XSD schema type
        :type type: PAGType
        
        :returns: A list of  error
        :rtype: List of tuples : Feature (QgsFeature), field (PAGField), message (str, QString)
        '''
        
        errors = list()
        
        for field in feature.fields():
            xsd_field = xsd_type.getField(field.name())
            
            # Check if field exists in XSD
            if xsd_field is None:
                continue
            
            errors += self.checkFeatureFieldData(feature, xsd_field)
        
        return errors
    
    def checkFeatureFieldData(self, feature, xsd_field):
        '''
        Checks the data of a feature against the XSD type
        
        :param feature: The feature to check
        :type feature: QgsFeature
        
        :param xsd_field: XSD type field
        :type xsd_field: PAGField
        
        :returns: A list of  error
        :rtype: List of tuples : Feature (QgsFeature), field (PAGField), message (str, QString)
        '''
        
        errors = list()
        
        field_value = feature.attribute(xsd_field.name)
        
        # Check null value
        if field_value is None or field_value == NULL:
            if not xsd_field.nullable:
                errors.append((feature, xsd_field, QCoreApplication.translate('DataChecker','Null value in non nullable field')))
            
            return errors
        
        # Check numeric values
        if xsd_field.type in [DataType.INTEGER,DataType.DOUBLE]:
            numeric_value = float(field_value)
            
            # Check min value
            if xsd_field.minvalue is not None:
                min_value = float(xsd_field.minvalue)
                if numeric_value < min_value:
                    errors.append((feature, xsd_field, QCoreApplication.translate('DataChecker','Value ({}) less than minimum value ({})').format(numeric_value, min_value)))
            
            # Check max value
            if xsd_field.maxvalue is not None:
                max_value = float(xsd_field.maxvalue)
                if numeric_value > max_value:
                    errors.append((feature, xsd_field, QCoreApplication.translate('DataChecker','Value ({}) greater than maximum value ({})').format(numeric_value, max_value)))
            
        # Check string values
        if xsd_field.type == DataType.STRING:
            text_value = unicode(field_value)
            
            # Check value length
            if xsd_field.length is not None:
                text_length = len(text_value)
                max_length = int(xsd_field.length)
                if text_length > max_length:
                    errors.append((feature, xsd_field, QCoreApplication.translate('DataChecker','Text length ({}) greater than field length ({})').format(text_length, max_length)))
            
            # Check enumeration
            if xsd_field.listofvalues is not None:
                if text_value not in xsd_field.listofvalues:
                    errors.append((feature, xsd_field, QCoreApplication.translate('DataChecker','Text ({}) not in field list of values').format(text_value)))
        
        return errors
    
    def checkFeatureGeometry(self, feature):
        '''
        Checks the geometry of a feature
        
        :param feature: The feature to check
        :type feature: QgsFeature
        
        :returns: A list of  error
        :rtype: List of tuples : Feature (QgsFeature), field (PAGField), message (str, QString)
        '''
        
        errors = list()
        
        if feature.geometry() is None:
            errors.append((feature, None, QCoreApplication.translate('DataChecker','Geometry is empty')))
        
        return errors