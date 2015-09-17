'''
Created on 9 sept. 2015

@author: arxit
'''

from create_project_dialog import CreateProjectDialog
from PagLuxembourg.schema import *

class CreateProject(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
        self.dlg = CreateProjectDialog()
    
    def run(self):
        self.dlg.show()