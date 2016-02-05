'''
Created on 26 oct. 2015

@author: arxit
'''

import os
import shutil
import uuid
from xml.dom.minidom import *

from qgis.core import *
from qgis.gui import *
from PyQt4.QtGui import QFileDialog, QMessageBox, QProgressBar
from PyQt4.QtCore import *

import PagLuxembourg.main
import PagLuxembourg.project
from PagLuxembourg.widgets.data_checker.data_checker import *

class ExportGML(object):
    '''
    Main class for the export data widget
    '''
    
    

    def __init__(self):
        '''
        Constructor
        '''
        pass
    
    DEFAULT_XLMNS = 'http://www.interlis.ch/INTERLIS2.3/GML32/PAG'
    
    def run(self):
        '''
        Runs the widget
        '''
        project = PagLuxembourg.main.current_project
        
        if not project.isPagProject():
            return
        
        # Check data before exporting
        self.data_checker = DataChecker()
        if not self.data_checker.run():
            return
        
        # Select file to export
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter('GML file (*.gml)');
        dialog.setWindowTitle(QCoreApplication.translate('ExportGML','Select the gml location'))
        dialog.setSizeGripEnabled(False)
        result = dialog.exec_()
        
        if result == 0:
            return
        
        selected_files = dialog.selectedFiles()
        
        if len(selected_files)==0:
            return
        
        # GML filename and directory
        gml_filename = selected_files[0]
        gml_directory = os.path.dirname(gml_filename)
        temp_dir = os.path.join(gml_directory, str(uuid.uuid1()))
        os.makedirs(temp_dir)
        
        # Progress bar
        progressMessageBar = PagLuxembourg.main.qgis_interface.messageBar().createMessage(QCoreApplication.translate('ExportGML','Exporting to GML'))
        progress = QProgressBar()
        progress.setMaximum(len(QgsMapLayerRegistry.instance().mapLayers()))
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        PagLuxembourg.main.qgis_interface.messageBar().pushWidget(progressMessageBar, QgsMessageBar.INFO)
        
        # Create final GML document
        gml = getDOMImplementation().createDocument('http://www.interlis.ch/INTERLIS2.3/GML32/INTERLIS', 'ili:TRANSFER', None)
        gml_root = gml.documentElement
        gml_root.setAttribute('xmlns:ili', 'http://www.interlis.ch/INTERLIS2.3/GML32/INTERLIS')
        gml_root.setAttribute('xmlns:gml', 'http://www.opengis.net/gml/3.2')
        gml_root.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
        gml_root.setAttribute('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        gml_root.setAttribute('xmlns', 'http://www.interlis.ch/INTERLIS2.3/GML32/PAG')
        gml_root.setAttribute('xsi:schemaLocation', 'http://www.interlis.ch/INTERLIS2.3/GML32/PAG PAG.xsd')
        gml_root.setAttribute('gml:id', 'x'+str(uuid.uuid1()))
        
        # Baskets topic
        topic_baskets = dict()
        
        # Iterates through XSD types
        for type in PagLuxembourg.main.xsd_schema.types:
            layer = project.getLayer(type)
            
            if layer is None:
                continue
            
            # Progression message
            progressMessageBar.setText(QCoreApplication.translate('ExportGML','Exporting {}').format(layer.name()))
            
            filename = os.path.join(temp_dir,
                                    '{}.gml'.format(type.friendlyName()))
            
            QgsVectorFileWriter.writeAsVectorFormat(layer, 
                                                    filename, 
                                                    'utf-8', 
                                                    None, 
                                                    'GML',
                                                    datasourceOptions = ['FORMAT=GML3.2',
                                                                         'TARGET_NAMESPACE={}'.format(self.DEFAULT_XLMNS),
                                                                         'GML3_LONGSRS=YES',
                                                                         'SRSDIMENSION_LOC=GEOMETRY',
                                                                         'WRITE_FEATURE_BOUNDED_BY=NO',
                                                                         'STRIP_PREFIX=TRUE',
                                                                         'SPACE_INDENTATION=NO'])
            
            members = self._getXsdCompliantGml(filename, gml, type)
            
            if type.topic() not in topic_baskets:
                basket = gml.createElement('ili:baskets')
                gml_root.appendChild(basket)
                
                topic = gml.createElement(type.topic())
                topic.setAttribute('gml:id','x'+str(uuid.uuid1()))
                basket.appendChild(topic)
                
                topic_baskets[type.topic()] = topic
                
            for member in members:
                topic_baskets[type.topic()].appendChild(member)
            
            progress.setValue(progress.value() + 1)
        
        file = open(gml_filename, 'wb')
        file.write(gml.toprettyxml('','\n','utf-8'))
        file.close()
        shutil.rmtree(temp_dir)
        
        PagLuxembourg.main.qgis_interface.messageBar().clearWidgets()
        PagLuxembourg.main.qgis_interface.messageBar().pushSuccess(QCoreApplication.translate('ExportGML','Success'),
                                                                   QCoreApplication.translate('ExportGML','GML export was successful'))
    
    def _getXsdCompliantGml(self, filename, gml, xsdtype):
        '''
        Transform the OGR gml to a XSD compliant GML
        
        :param filename: The GML filename
        :type filename: str, QString
        
        :returns: A list of xml element compliant to the XSD
        :rtype: list(element)
        '''
        
        result = list()
        
        # Parse as XML
        xml_root = parse(filename) # parse an XML file by name
        
        feature_members = xml_root.getElementsByTagName('featureMember')
        
        for feature_member in feature_members:
            #Create member element
            member = gml.createElement('member')
            feature_member_type = feature_member.getElementsByTagName(xsdtype.friendlyName())[0]
            member.appendChild(feature_member_type.cloneNode(False))
            member_type = member.firstChild
            
            # Iterate XSD ordered fields
            for fieldname in xsdtype.ordered_field_names:
                element = None
                elements = feature_member.getElementsByTagName(fieldname)
                if len(elements)>0:
                    element = elements[0]
                
                # Process geometry fields
                if fieldname == xsdtype.geometry_fieldname:
                    elements = feature_member.getElementsByTagName('geometryProperty')
                    if len(elements)>0:
                        element = elements[0]
                        self._processGmlGeometry(element, gml, xsdtype)
                        
                if element is not None:
                    member_type.appendChild(element)
            
            result.append(member)
            
        return result
    
    def _processGmlGeometry(self, geometry_element, gml, xsdtype):
        
        # Rename tag
        geometry_element.tagName = xsdtype.geometry_fieldname
        
        first_child = geometry_element.firstChild
        
        if first_child is None:
            return
        
        if first_child.tagName == 'gml:Point': # Process point
            # Nothing to do
            return
        
        elif first_child.tagName == 'gml:LineString':
            first_child.tagName = 'gml:Curve'
            
            poslist = first_child.firstChild
            first_child.removeChild(poslist)
            
            segments = gml.createElement('gml:segments')
            first_child.appendChild(segments)
            
            linestring_segment = gml.createElement('gml:LineStringSegment')
            linestring_segment.setAttribute('interpolation','linear')
            linestring_segment.appendChild(poslist)            
            segments.appendChild(linestring_segment)
        
        elif first_child.tagName == 'gml:Polygon':
            rings = first_child.getElementsByTagName('LinearRing')
            
            for ring in rings:
                ring.tagName = 'gml:Ring'
            
                poslist = ring.firstChild
                ring.removeChild(poslist)
            
                curve_member = gml.createElement('gml:curveMember')
                ring.appendChild(curve_member)
                
                curve = gml.createElement('gml:Curve')
                curve.setAttribute('gml:id','x'+str(uuid.uuid1()))
                curve_member.appendChild(curve)
                
                segments = gml.createElement('gml:segments')
                curve.appendChild(segments)
            
                linestring_segment = gml.createElement('gml:LineStringSegment')
                linestring_segment.setAttribute('interpolation','linear')
                linestring_segment.appendChild(poslist)            
                segments.appendChild(linestring_segment)