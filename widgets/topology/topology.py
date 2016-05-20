'''
Created on 25 sept. 2015

Updated on 11 may 2016

@author: arxit
'''

import os
import json

from qgis.core import *
import qgis.utils
from PyQt4.QtGui import QAction
from PyQt4.QtCore import QCoreApplication
import PagLuxembourg.main

TOPOL_SECTION = "Topol"

class TopologyChecker(object):
    '''
    Main class for the topology checker widget
    '''

    def __init__(self, action):
        '''
        Constructor
        '''
        self.topology_action=action
    
    def run(self):
        '''
        Runs the widget
        '''
        
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        self.topology_action.trigger()
        
        # Zoom to selected onclick button
        modification_pag_layer=project.getModificationPagLayer()
        
        if modification_pag_layer is not None:
            entity_count = modification_pag_layer.selectedFeatureCount()
            canvas = qgis.utils.iface.mapCanvas()
            canvas.zoomToSelected(modification_pag_layer)
            if entity_count==1:
                
                PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
                PagLuxembourg.main.qgis_interface.messageBar().pushMessage(QCoreApplication.translate('Topology','Information'),
                                                                   QCoreApplication.translate('Topology','There is 1 selected entity in MODIFICATION PAG layer. You can now check topology'))
            elif entity_count==0:
                PagLuxembourg.main.qgis_interface.messageBar().pushMessage(QCoreApplication.translate('Topology_no','Information'),
                                                                   QCoreApplication.translate('Topology_no','There is no selected entity in MODIFICATION PAG layer. You can now check topology'))
            else:
                qgis.utils.iface.messageBar().pushMessage(QCoreApplication.translate('Topology_many', 'Information'),
                                                                   QCoreApplication.translate('Topology_many','There are {} selected entities in MODIFICATION PAG layer. You can now check topology').format(entity_count))
        else :
            qgis.utils.iface.messageBar().pushMessage("Error", "MODIFICATION PAG layer is not correct")
    
    def updateProjectRules(self):
        '''
        Updates the topology check rules of the project
        '''
        
        # Get rules config
        config_path = os.path.join(PagLuxembourg.main.plugin_dir,
                               'widgets',
                               'topology',
                               'config.json')
        
        f = open(config_path, 'r')
        config_file = f.read()
        config = json.loads(config_file)
        f.close()
        
        # Get project rules
        project_rules_count,topol_section_exists = QgsProject.instance().readNumEntry(TOPOL_SECTION, "/testCount" );
        project_rules = list()
        if topol_section_exists:
            for i in range(project_rules_count):
                project_rule = self._readTest(i)
                if project_rule.layer1 is not None:
                    project_rules.append(project_rule)
        
        # Loop each rule and update
        for rule in config['Rules']:
            config_rule = TopologyRule()
            config_rule.layer1 = str(rule['Layer1'])
            config_rule.layer1 = config_rule.layer1 if config_rule.layer1 is not None and len(config_rule.layer1) >0 else QCoreApplication.translate('rulesDialog','No layer')
            config_rule.layer2 = str(rule['Layer2'])
            config_rule.layer2 = config_rule.layer2 if config_rule.layer2 is not None and len(config_rule.layer2) >0 else QCoreApplication.translate('rulesDialog','No layer')
            config_rule.rule = QCoreApplication.translate('topolTest',str(rule['Rule']).lower())
            config_rule.tolerance = str(rule['Tolerance'])
            
            if config_rule not in project_rules:
                self._addRule(config_rule)
        
        QgsProject.instance().write()
        
    def _readTest(self, index):
        project = QgsProject.instance()
        postfix = str(index)
        rule,r = project.readEntry(TOPOL_SECTION, "/testname_" + postfix, "" )
        tolerance,t = project.readEntry(TOPOL_SECTION, "/tolerance_" + postfix, "" )
        layer1Id,l1 = project.readEntry(TOPOL_SECTION, "/layer1_" + postfix, "" )
        layer2Id,l2 = project.readEntry(TOPOL_SECTION, "/layer2_" + postfix, "" )
        
        layer_registry = QgsMapLayerRegistry.instance()
        layer1 = layer_registry.mapLayer(layer1Id)
        layer2 = layer_registry.mapLayer(layer2Id)
        
        current_project = PagLuxembourg.main.current_project
        layer1_table = current_project.getUriInfos(layer1.source())[1] if layer1 is not None else None
        layer2_table = current_project.getUriInfos(layer2.source())[1] if layer2 is not None else None
        
        result = TopologyRule()
        result.layer1 = str(layer1_table) if layer1_table is not None and len(layer1_table)>0 else QCoreApplication.translate('rulesDialog','No layer')
        result.layer2 = str(layer2_table) if layer2_table is not None and len(layer2_table)>0 else QCoreApplication.translate('rulesDialog','No layer')
        result.rule = str(rule) if rule is not None else None
        result.tolerance = str(tolerance) if tolerance is not None else None
        
        return result
    
    def _addRule(self, rule):
        # Get project rules count
        project = QgsProject.instance()
        project_rules_count, topol_section_exists = project.readNumEntry(TOPOL_SECTION, "/testCount" )
        project_rules_count = str(project_rules_count) if topol_section_exists else '0'
        
        # Get layer id from table name
        layer_registry = QgsMapLayerRegistry.instance()
        current_project = PagLuxembourg.main.current_project
        for layerid, layer in layer_registry.mapLayers().iteritems():
            layer_table = current_project.getUriInfos(layer.source())[1]
            if rule.layer1 == layer_table:
                rule.layer1=layerid
            if rule.layer2 == layer_table:
                rule.layer2=layerid
        
        # Write rule
        project.writeEntry(TOPOL_SECTION, "/testname_" + project_rules_count, QCoreApplication.translate('topolTest',rule.rule))
        project.writeEntry(TOPOL_SECTION, "/tolerance_" + project_rules_count, rule.tolerance)
        project.writeEntry(TOPOL_SECTION, "/layer1_" + project_rules_count, rule.layer1)
        project.writeEntry(TOPOL_SECTION, "/layer2_" + project_rules_count, rule.layer2)
        project.writeEntry(TOPOL_SECTION, "/testCount", int(project_rules_count) + 1 );
        #project.write()
    
class TopologyRule(object):
    def __init__(self):
        pass
    
    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__