'''
Created on 09 nov. 2015

@author: arxit
'''

import os

from about_dialog import AboutDialog

class About(object):
    '''
    Main class for the create project widget
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
        self.dlg = AboutDialog()
    
    def run(self):
        '''
        Runs the widget
        '''
        
        self.dlg.show()