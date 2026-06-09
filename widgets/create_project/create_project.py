'''
Created on 17 sept. 2015

@author: arxit
'''
from __future__ import absolute_import

from builtins import object
import os

from .create_project_dialog import CreateProjectDialog

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
        
        self.dlg.clear()
        self.dlg.show()