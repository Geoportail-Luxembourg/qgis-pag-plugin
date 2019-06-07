'''
Created on 22 sept. 2015

@author: arxit
'''

from builtins import object
import os

from qgis.core import *
from qgis.PyQt.QtCore import QCoreApplication

import PagLuxembourg.main

class StylizeProject(object):
    '''
    Main class for the layers stylize widget
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

        project = PagLuxembourg.main.current_project

        if not project.isPagProject():
            return

        # Map layers in the TOC
        maplayers = QgsProject.instance().mapLayers()

        # Iterates through XSD types
        for type in PagLuxembourg.main.xsd_schema.types:
            if type.geometry_type is None:
                continue

            uri = project.getTypeUri(type)
            found = False

            # Check whether a layer with type data source exists in the map
            for k,v in list(maplayers.items()):
                if project.compareURIs(v.source(), uri):
                    found = True
                    layer = v
                    break

            if not found:
                continue

            self.stylizeLayer(layer, type)

        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('StylizeProject','Success'),
                                                                   QCoreApplication.translate('StylizeProject','The layers styling is finished.'))

    def stylizeLayer(self, layer, type):
        '''
        Stylize the current layer

        :param layer: The layer to update
        :type layer: QgsVectorLayer

        :param type: XSD schema type
        :type type: PAGType
        '''

        qml = os.path.join(PagLuxembourg.main.plugin_dir,
                               'styles',
                               '{}.qml'.format(type.name))

        layer.loadNamedStyle(qml)