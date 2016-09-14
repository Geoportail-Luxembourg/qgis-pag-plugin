'''
Created on 11 dec. 2015

@author: arxit
'''

import os

from qgis.core import *
import qgis.utils
from PyQt4.QtGui import QAction
from PyQt4.QtCore import QCoreApplication
import PagLuxembourg.main

class TopoClean(object):
    '''
    Main class for the snapping widget
    '''

    def __init__(self, action):
        '''
        Constructor
        '''
        self.topoclean_action=action
    
    def run(self):
        '''
        Runs the widget
        '''
        
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        self.topoclean_action.trigger()
        
        # Zoom to selected onclick button
        modification_pag_layer=project.getModificationPagLayer()
        
        if modification_pag_layer is not None:
            # Map layers in the TOC
            maplayers = QgsMapLayerRegistry.instance().mapLayers()
            
            # Selection by intersection with 'MODIFICATION PAG' layer
            for k,layer in maplayers.iteritems():
                if layer.type() != QgsMapLayer.VectorLayer or not PagLuxembourg.main.current_project.isPagLayer(layer):
                    continue
               
                areas = []
                for PAG_feature in modification_pag_layer.selectedFeatures():
                    cands = layer.getFeatures()
                    for layer_features in cands:
                        if PAG_feature.geometry().intersects(layer_features.geometry()):
                            areas.append(layer_features.id())

                layer.select(areas)
            
            entity_count = modification_pag_layer.selectedFeatureCount()            
            canvas = qgis.utils.iface.mapCanvas()
            canvas.zoomToSelected(modification_pag_layer)
            if entity_count==1:
                
                PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
                PagLuxembourg.main.qgis_interface.messageBar().pushMessage(QCoreApplication.translate('TopoClean','Information'),
                                                                   QCoreApplication.translate('TopoClean','There is 1 selected entity in MODIFICATION PAG layer. You can now check geometries'))
            elif entity_count==0:
                PagLuxembourg.main.qgis_interface.messageBar().pushMessage(QCoreApplication.translate('TopoClean','Information'),
                                                                   QCoreApplication.translate('TopoClean','There is no selected entity in MODIFICATION PAG layer. You can now check geometries'))
            else:
                qgis.utils.iface.messageBar().pushMessage(QCoreApplication.translate('TopoClean', 'Information'),
                                                                   QCoreApplication.translate('TopoClean','There are {} selected entities in MODIFICATION PAG layer. You can now check geometries').format(entity_count))
        else :
            qgis.utils.iface.messageBar().pushMessage("Error", "MODIFICATION PAG layer is not correct")