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

from import_gml import ImportGML
from import_shp_dialog import ImportShpDialog

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
                    'shp':self.importShp,
                    'dxf':None
                    }
        
        extension = os.path.splitext(selected_file[0])[1][1:]
        importer[extension](selected_file[0])
        
    def importGml(self, filename):
        '''
        Import a GML file
        
        :param filename: The GML filename
        :type filename: str, QString
        '''
        
        gmlimporter = ImportGML()
        gmlimporter.importGml(filename)
    
    def importShp(self, filename):
        '''
        Import a shapefile
        
        :param filename: The SHP filename
        :type filename: str, QString
        '''
    
        self.dlg = ImportShpDialog(filename)
        if self.dlg.valid:
            self.dlg.show()