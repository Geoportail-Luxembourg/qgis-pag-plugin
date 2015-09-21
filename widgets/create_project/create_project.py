'''
Created on 17 sept. 2015

@author: arxit
'''

import os

from create_project_dialog import CreateProjectDialog
from PagLuxembourg.project import *

class CreateProject(object):
    '''
    Main class for the create project widget
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
        self.dlg = CreateProjectDialog()
    
    def run(self):
        '''
        Runs the widget
        '''
        
        #self.dlg.show()
        project = Project()
        project.create('C:/Users/arxit/Documents','Test')