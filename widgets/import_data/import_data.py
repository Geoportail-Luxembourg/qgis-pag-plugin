'''
Created on 22 oct. 2015

@author: arxit
'''

import os

from qgis.core import *
from qgis.gui import *
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import *

import PagLuxembourg.main

from import_gml import ImportGML
from import_shp import ImportSHP
from import_dxf import ImportDXF

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
        importers = {
                    'gml':ImportGML,
                    'shp':ImportSHP,
                    'dxf':ImportDXF
                    }
        
        extension = os.path.splitext(selected_file[0])[1][1:]
        self.importer = importers[extension](selected_file[0])
        self.importer.runImport()