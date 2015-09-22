'''
Created on 22 sept. 2015

@author: arxit
'''

import os

from qgis.core import *

import PagLuxembourg.main

class StylizeProject(object):
    '''
    Main class for the layers stylize widget
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
        
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        # Map layers in the TOC
        maplayers = QgsMapLayerRegistry.instance().mapLayers()
        
        # Iterates through XSD types
        for type in PagLuxembourg.main.xsd_schema.types:
            if type.geometry_type is None:
                continue
            
            uri = project.getTypeUri(type)
            found = False
            
            # Check whether a layer with type data source exists in the map
            for k,v in maplayers.iteritems():
                if project.compareURIs(v.source(), uri):
                    found = True
                    layer = v
                    break
            
            if not found:
                continue
            
            sld = os.path.join(PagLuxembourg.main.plugin_dir,
                               'styles',
                               '%s.sld'%type.name)
            
            layer.loadSldStyle(sld)