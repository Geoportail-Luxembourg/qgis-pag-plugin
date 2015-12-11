'''
Created on 11 dec. 2015

@author: arxit
'''

import os

from qgis.core import *
from qgis.gui import *
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import *

import PagLuxembourg.main
import PagLuxembourg.project

class Snapping(object):
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