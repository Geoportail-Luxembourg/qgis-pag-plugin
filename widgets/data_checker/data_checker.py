'''
Created on 23 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from PyQt4.QtGui import QAction

from PagLuxembourg.schema import *
import PagLuxembourg.main

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
        '''
        
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
    def checkLayerStructure(self, layer, xsd_type):
        '''
        Checks a layer against the XSD type
        
        :param layer: The vector layer to check
        :type layer: QgsVectorLayer
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        layer_fields = layer.dataProvider().fields()
        errors = list()
        
        for field in xsd_type.fields:
            # Check field missing
            layer_index = layer_fields.fieldNameIndex(field.name)
            if layer_index == -1:
                if field.nullable:
                    errors.append((layer, field, 'Field is missing', ErrorLevel.WARNING))
                else:
                    errors.append((layer, field, 'Field is missing', ErrorLevel.FATAL))
                
                continue
            
            # Check field datatype
            layer_field = layer_fields[layer_index]
            found = False
            for xsd_type, qgis_type in XSD_QGIS_DATATYPE_MAP.iteritems():
                if layer_field.type() == qgis_type and field.type == xsd_type:
                    found = True
                    break
            
            if not found:
                errors.append((layer, field, 'Field datatype mismatch', ErrorLevel.FATAL))
        
        return errors
    
class ErrorLevel:
    WARNING = 'W' # Warning only, ex field is missing, but nullable
    FATAL = 'F' # Error, ex : non nullable field missing