'''
Created on 05 nov. 2015

@author: arxit
'''

from PyQt4.QtCore import QCoreApplication
from qgis.core import *

import PagLuxembourg.main

from import_dxf_dialog import ImportDxfDialog

class ImportDXF(object):
    '''
    Main class for the DXF importer
    '''
    
    def __init__(self, filename):
        '''
        Constructor
        
        :param filename: The DXF filename
        :type filename: str, QString
        '''
        self.filename = filename
    
    def runImport(self):
        '''
        Import a DXF file
        '''
        
        self.dlg = ImportDxfDialog(self.filename)
        
        if self.dlg.valid:
            self.dlg.show()
        else:
            PagLuxembourg.main.qgis_interface.messageBar().pushCritical(QCoreApplication.translate('ImportDXF','Error'),
                                                                        QCoreApplication.translate('ImportDXF','DXF file is not valid'))