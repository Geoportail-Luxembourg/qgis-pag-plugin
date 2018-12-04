'''
Created on 05 nov. 2015

@author: arxit
'''

from import_shp_dialog import ImportShpDialog

class ImportGeoJSON(object):
    '''
    Main class for the import data widget
    '''
    
    def __init__(self, filename):
        '''
        Constructor
        
        :param filename: The GeoJSON filename
        :type filename: str, QString
        '''
        self.filename = filename
    
    def runImport(self):
        '''
        Import a GeoJSON file
        '''
        
        self.dlg = ImportShpDialog(self.filename)
        if self.dlg.valid:
            self.dlg.show()