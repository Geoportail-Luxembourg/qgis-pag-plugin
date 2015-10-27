'''
Created on 26 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from qgis.gui import *
from PyQt4.QtGui import QFileDialog, QMessageBox, QProgressBar
from PyQt4.QtCore import *

import PagLuxembourg.main
from PagLuxembourg.widgets.data_checker.data_checker import *

class ExportGML(object):
    '''
    Main class for the export data widget
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
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        # Select file to import
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setWindowTitle(QCoreApplication.translate('ExportGML','Select the gml location'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files)==0:
            return
        
        # Progress bar
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('ExportGML','Exporting to GML'))
        progress = QProgressBar()
        progress.setMaximum(len(QgsMapLayerRegistry.instance().mapLayers()))
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, QgsMessageBar.INFO)
        
        # Iterates through XSD types
        for type in PagLuxembourg.main.xsd_schema.types:
            layer = project.getLayer(type)
            
            if layer is None:
                continue
            
            filename = os.path.join(selected_files[0],
                               '{}.gml'.format(type.name))
            
            QgsVectorFileWriter.writeAsVectorFormat(layer, 
                                                    filename, 
                                                    'utf-8', 
                                                    None, 
                                                    'GML')
            
            progress.setValue(progress.value() + 1)
        
        PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ExportGML','Success'),
                                                                   QCoreApplication.translate('ExportGML','GML export was successful'))