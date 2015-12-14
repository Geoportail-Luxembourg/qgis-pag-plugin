'''
Created on 11 dec. 2015

@author: arxit
'''

import os

from qgis.core import *
from qgis.gui import *
import processing

from PyQt4.QtGui import QFileDialog, QProgressBar
from PyQt4.QtCore import *

import PagLuxembourg.main
import PagLuxembourg.project

class TopoClean(object):
    '''
    Main class for the snapping widget
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
            return
        
        #self.dlg = ImportManagerDialog()
        #self.dlg.show()
        
        layer = PagLuxembourg.main.qgis_interface.layerTreeView().currentLayer()
        
        self.cleanLayer(layer)
    
    def cleanLayer(self, layer):
        if not (layer.type() == QgsMapLayer.VectorLayer and PagLuxembourg.main.current_project.isPagLayer(layer)):
            return
        
        # Run the GRASS clean topology tool
        result = processing.runalg('grass:v.clean.advanced', # Processing
                                   layer, # Layer
                                   'rmarea', # Tools
                                   0.1, # Threshold
                                   None, # Extent
                                   -1, # Snapping tolerance
                                   0.0001, # Min area
                                   None, # Output layer (auto)
                                   None) # Output errors (auto)
        
        # Start editing session
        if not layer.isEditable():
            layer.startEditing()
        
        # Empty layer
        layer.selectAll()
        layer.deleteSelectedFeatures()
        
        # Add cleaned features
        clean_layer = QgsVectorLayer(result['output'], 'Clean', 'ogr')
        
        # Progress bar + message
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('TopoClean','Adding cleaned features'))
        progress = QProgressBar()
        progress.setMaximum(clean_layer.featureCount())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, QgsMessageBar.INFO)
        
        # Adding features
        for feature in clean_layer.getFeatures():
            dst_feature = QgsFeature(layer.fields())
            for index in range(1,layer.fields().count()):
                dst_feature.setAttribute(index, feature[index])
            dst_feature.setGeometry(feature.geometry())
            layer.addFeatures([dst_feature], False)
            progress.setValue(progress.value() + 1)
        
        PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
        
        # Commit    
        if not layer.commitChanges():
            layer.rollBack()
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('TopoClean','Error'), 
                                                                        QCoreApplication.translate('TopoClean','Commit error on layer {}').format(layer.name()))
            errors = layer.commitErrors()
            for error in errors:
                QgsMessageLog.logMessage(error, 'Clean topology on {}'.format(layer.name()), QgsMessageLog.CRITICAL)
            PagLuxembourg.main.qgis_interface.openMessageLog()
        else:
            PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('TopoClean','Success'), 
                                                                       QCoreApplication.translate('TopoClean','Layer cleaned successfully'))