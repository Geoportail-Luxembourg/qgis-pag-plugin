'''
Created on 17 sept. 2015

@author: arxit
'''

from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import QCoreApplication

import os

class CreateProject(object):
    '''
    classdocs
    '''


    def __init__(self, iface):
        '''
        Constructor
        '''
        
        self.iface = iface
    
    def run(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setWindowTitle(QCoreApplication.translate('CreateProject','Select the new project location'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files)==0:
            return
        
        selected_folder = selected_files[0]
        pass