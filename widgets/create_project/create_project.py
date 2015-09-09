'''
Created on 9 sept. 2015

@author: arxit
'''

from create_project_dialog import CreateProjectDialog

class CreateProject(object):
    '''
    classdocs
    '''


    def __init__(self, iface):
        '''
        Constructor
        '''
        self.iface=iface
        self.dlg=CreateProjectDialog()
    
    def run(self):
        self.dlg.show()