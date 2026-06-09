'''
Created on 05 nov. 2015

@author: arxit
'''
from __future__ import absolute_import

import os

from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QProgressBar
from qgis.PyQt.QtCore import *

import PagLuxembourg.main
from PagLuxembourg.widgets.data_checker.data_checker import *

from .importer import *

class ImportGML(Importer):
    '''
    Main class for the import data widget
    '''

    data_checker = DataChecker()

    def __init__(self, filename):
        Importer.__init__(self, filename)
        '''
        Constructor

        :param filename: The GML filename
        :type filename: str, QString
        '''
        self.filename = filename

    def runImport(self):
        '''
        Import a GML file
        '''

        # Open GML
        file = QFile(self.filename)
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
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('ImportGML', 'Importing GML'))
        progress = QProgressBar()
        progress.setMaximum(len(gmlschema.typeNames()))
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        progress2 = QProgressBar()
        progress2.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress2)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, 0) # Qgis.Info = 0

        # Start import session
        self._startImportSession()

        # Loop GML types
        for gmltype in gmlschema.typeNames():
            xsdtype = xsdschema.getType(gmltype)
            if xsdtype is None:
                unknowntypes.append(gmltype)
                continue

            # Progression message
            progressMessageBar.setText(QCoreApplication.translate('ImportGML', 'Importing {}').format(gmltype))

            gmllayer = QgsVectorLayer(u'{}|layername={}'.format(self.filename,gmltype), gmltype, "ogr")

            # Check schema structure table and datatypes
            warn_errors, fatal_errors = self.data_checker.checkLayerStructure(gmllayer, xsdtype)

            if len(fatal_errors) == 0:
                self._importGmlLayer(gmllayer, xsdtype, progress2)
            else:
                for layer, field, message in fatal_errors:
                    self.commit_errors.append(message)

            progress.setValue(progress.value() + 1)

        # Commit import session
        self._commitImport()

    def _importGmlLayer(self, gml_layer, xsdtype, progress):
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

        progress.setMaximum(gml_layer.featureCount())
        progress.setValue(0)

        self._importLayer(gml_layer,
                          xsd_layer,
                          self._getFieldMap(gml_layer, xsd_layer, xsdtype),
                          progress)

    def _getFieldMap(self, source_layer, destination_layer, xsdtype):
        '''
        Get the field index map between the source layer and destination layer

        :param source_layer: The source layer to import
        :type source_layer: QgsVectorLayer

        :param destination_layer: The destination layer to write to
        :type destination_layer: QgsVectorLayer
        '''

        mapping = LayerMapping()

        source_fields = source_layer.dataProvider().fields()
        destination_fields = destination_layer.dataProvider().fields()

        for source_field in source_fields:
            if source_field.name() == xsdtype.geometry_fieldname:
                continue

            if source_field.name() == 'gml_id':
                continue

            destination_field_index = destination_fields.indexFromName(source_field.name())

            if destination_field_index == -1:
                continue

            mapping.addFieldMapping(source_fields.indexFromName(source_field.name()),
                                    destination_field_index,
                                    None,
                                    True)

        return mapping
