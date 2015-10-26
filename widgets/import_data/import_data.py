'''
Created on 22 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from PyQt4.QtGui import QFileDialog, QMessageBox
from PyQt4.QtCore import QCoreApplication, QFile, QIODevice

import PagLuxembourg.main

class ImportData(object):
    '''
    Main class for the import data widget
    '''


    def __init__(self):
        '''
        Constructor
        '''
        pass
    
    def run(self):
        '''
        Runs the widget
        '''
        
        if not PagLuxembourg.main.current_project.isPagProject():
            pass#return
        
        # Select file to import
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setOption(QFileDialog.ReadOnly)
        dialog.setNameFilter('Vector file (*.gml *.shp *.dxf)');
        dialog.setWindowTitle(QCoreApplication.translate('ImportData','Select the file to import'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_file = dialog.selectedFiles()
        
        if len(selected_file)==0:
            return
        
        # Dispatch to the right importer
        importer = {
                    'gml':self.importGml,
                    'shp':None,
                    'dxf':None
                    }
        
        extension = os.path.splitext(selected_file[0])[1][1:]
        importer[extension](selected_file[0])
        
        # Success message
        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ImportData','Success'), 
                                                                   QCoreApplication.translate('ImportData','Importation was successful'))
    
    def importGml(self, filename):
        '''
        Import a GML file
        
        :param filename: The GML filename
        :type filename: str, QString
        '''
        
        # Open GML
        file = QFile(filename)
        file.open(QIODevice.ReadOnly)
        gmlcontent = file.readAll()
        
        # Guess GML schema
        gmlschema = QgsGmlSchema()
        gmlschema.guessSchema(gmlcontent)
        
        # XSD Schema
        xsdschema = PagLuxembourg.main.xsd_schema
        
        unknowntypes = list()
        
        # Check schema structure table and datatypes
        
        # Loop GML types
        for gmltype in gmlschema.typeNames():
            xsdtype = xsdschema.getType(gmltype)
            if xsdtype is None:
                unknowntypes.append(gmltype)
                continue
            
            gmllayer = QgsVectorLayer('{}|layername={}'.format(filename,gmltype), gmltype, "ogr")
            self._importGmlLayer(gmllayer, xsdtype)
    
    def _importGmlLayer(self, gml_layer, xsdtype):
        '''
        Import a GML layer
        
        :param gml_layer: The GML layer to import
        :type gml_layer: QgsVectorLayer
        
        :param xsdtype: XSD schema type
        :type xsdtype: PAGType
        '''
        
        xsd_layer = PagLuxembourg.main.current_project.getLayer(xsdtype)
        
        if xsd_layer is None:
            return
        
        gml_dp = gml_layer.dataProvider()
        xsd_dp = xsd_layer.dataProvider()
        xsd_layer_fields = xsd_dp.fields()
        gml_xsd_fieldindexmap = self._getFieldMap(gml_layer, xsd_layer)
        newfeatures = list()
        
        # Iterate GML features
        for gmlfeature in gml_dp.getFeatures():
            feature = QgsFeature(xsd_layer_fields)
            for gmlindex, xsdindex in gml_xsd_fieldindexmap.iteritems():
                # Validate field length, enumeration, nullable
                feature.setAttribute(xsdindex,gmlfeature[gmlindex])
            feature.setGeometry(gmlfeature.geometry())
            newfeatures.append(feature)
            
        xsd_dp.addFeatures(newfeatures)
        xsd_layer.reload()
    
    def _getFieldMap(self, source_layer, destination_layer):
        '''
        Get the field index map between the source layer and destination layer
        
        :param source_layer: The source layer to import
        :type source_layer: QgsVectorLayer
        
        :param destination_layer: The destination layer to write to
        :type destination_layer: QgsVectorLayer
        '''
        
        source_fields = source_layer.dataProvider().fields()
        destination_fields = destination_layer.dataProvider().fields()
        indexmap = dict()
        
        for source_field in source_fields:
            if source_field.name() == 'GEOMETRIE':
                continue
            
            if source_field.name() == 'gml_id':
                continue
            
            destination_field_index = destination_fields.fieldNameIndex(source_field.name())
            
            if destination_field_index == -1:
                continue
            
            indexmap[source_fields.fieldNameIndex(source_field.name())] = destination_field_index
            
        return indexmap