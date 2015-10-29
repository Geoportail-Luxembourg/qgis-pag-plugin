'''
Created on 22 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from qgis.gui import *
from PyQt4.QtGui import QFileDialog, QMessageBox, QProgressBar
from PyQt4.QtCore import *

import PagLuxembourg.main
from PagLuxembourg.widgets.data_checker.data_checker import *

class ImportData(object):
    '''
    Main class for the import data widget
    '''
    
    data_checker = DataChecker()

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
            return
        
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
        layer_structure_errors = importer[extension](selected_file[0])
        
        # Success message
        if len(layer_structure_errors) == 0:
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ImportData','Success'), 
                                                                       QCoreApplication.translate('ImportData','Importation was successful'))
        else:
            PagLuxembourg.main.qgis_interface.messageBar().pushWarning(QCoreApplication.translate('ImportData','Warning'), 
                                                                       QCoreApplication.translate('ImportData','Some errors encountered during importation'))
            
            self.dlg = ErrorSummaryDialog(layer_structure_errors, list())
            self.dlg.show()
        
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
        layer_structure_errors = list()
        
        # Progress bar + message
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('ImportData','Importing GML'))
        progress = QProgressBar()
        progress.setMaximum(len(gmlschema.typeNames()))
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, QgsMessageBar.INFO)

        # Loop GML types
        for gmltype in gmlschema.typeNames():
            xsdtype = xsdschema.getType(gmltype)
            if xsdtype is None:
                unknowntypes.append(gmltype)
                continue
            
            # Progression message
            progressMessageBar.setText(QCoreApplication.translate('ImportData','Importing {}').format(gmltype))
            
            gmllayer = QgsVectorLayer('{}|layername={}'.format(filename,gmltype), gmltype, "ogr")
            
            # Check schema structure table and datatypes
            warn_errors, fatal_errors = self.data_checker.checkLayerStructure(gmllayer, xsdtype)
            layer_structure_errors = layer_structure_errors + fatal_errors
            
            if len(fatal_errors) == 0:
                self._importGmlLayer(gmllayer, xsdtype)
            
            progress.setValue(progress.value() + 1)
            
        PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
        
        return layer_structure_errors
    
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
        gml_xsd_fieldindexmap = self._getFieldMap(gml_layer, xsd_layer, xsdtype)
        newfeatures = list()
        
        # Iterate GML features
        for gmlfeature in gml_dp.getFeatures():
            feature = QgsFeature(xsd_layer_fields)
            for gmlindex, xsdindex in gml_xsd_fieldindexmap.iteritems():
                # Check if numeric value needs to be casted
                if gmlfeature[gmlindex] == NULL:
                    feature.setAttribute(xsdindex, NULL)
                elif feature.fields()[xsdindex].type() == QVariant.String and not isinstance(gmlfeature[gmlindex], basestring):
                    feature.setAttribute(xsdindex, str(gmlfeature[gmlindex]))
                else:
                    feature.setAttribute(xsdindex, gmlfeature[gmlindex])
            
            if xsdtype.geometry_type is not None:
                feature.setGeometry(gmlfeature.geometry())
            
            newfeatures.append(feature)
        
        # Start editing session
        if not xsd_layer.isEditable():
            xsd_layer.startEditing()
        
        # Add features    
        xsd_layer.addFeatures(newfeatures, False)
        
        # Commit    
        if not xsd_layer.commitChanges():
            xsd_layer.rollBack()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('ImportData','Error'), 
                                                                       QCoreApplication.translate('ImportData','Commit error on layer {}').format(xsd_layer.name()))
        
        xsd_layer.reload()
    
    def _getFieldMap(self, source_layer, destination_layer, xsdtype):
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
            if source_field.name() == xsdtype.geometry_fieldname:
                continue
            
            if source_field.name() == 'gml_id':
                continue
            
            destination_field_index = destination_fields.fieldNameIndex(source_field.name())
            
            if destination_field_index == -1:
                continue
            
            indexmap[source_fields.fieldNameIndex(source_field.name())] = destination_field_index
            
        return indexmap