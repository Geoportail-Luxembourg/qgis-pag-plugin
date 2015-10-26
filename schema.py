'''
Created on 17 sept. 2015

@author: arxit
'''

import os.path
import xml.etree.ElementTree as ET
from PyQt4.QtCore import QFile, QIODevice, QVariant
from qgis.core import *

import main

class PAGSchema(object):
    '''
    The PAG schema parsed from the XSD
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.parseXSD()
    
    def parseXSD(self):
        '''
        Parses the XSD
        '''
        
        xsd_path = os.path.join(
            main.plugin_dir,
            'assets',
            'PAGschema.xsd')
        
        # Parse as QgsGmlSchema
        file = QFile(xsd_path)
        file.open(QIODevice.ReadOnly)
        xsdcontent = file.readAll()
        
        schema = QgsGmlSchema()
        schema.parseXSD(xsdcontent)
        
        #Parse as XML
        ns = {'xsd': 'http://www.w3.org/2001/XMLSchema'} # XSD namespace
        xsd = ET.parse(xsd_path)
        
        topics = list() # Topics : PAG, ARTIKEL17, GESTION
        concrete_typenames = list()
        
        # Loop GML schema type names
        for typename in schema.typeNames():
            # Remove GEOMETRIE types
            if typename.endswith('.GEOMETRIE'):
                continue
            
            # Topics ILI
            if len(schema.fields(typename))==1 and schema.fields(typename)[0].name() == 'member':
                topics.append((typename,self._getTopicMembers(schema.fields(typename)[0].typeName(), xsd.getroot(), ns)))
                continue
            
            # Concretes types
            concrete_typenames.append(typename)
        
        self.types = list()
        
        # Loop concrete type names and parse to PAGType
        for typename in concrete_typenames:
            xml_element = xsd.getroot().find('xsd:complexType[@name="{}Type"]'.format(typename),ns)
            pag_type = PAGType()
            pag_type.parse(typename, xml_element, ns)
            self.types.append(pag_type)

        # Add topic to types
        for topic, members in topics:
            for member in members:
                for type in self.types:
                    if type.name == member:
                        type.name = '{}.{}'.format(topic,member)
                        break
    
    def getType(self, typename):
        '''
        Get a type from the name
        
        :param typename: The type name (ex : BIOTOPE_LIGNE)
        :type typename: str, QString
        '''
        
        for type in self.types:
            if type.friendlyName() == typename:
                return type
        
        return None
    
    def _getTopicMembers(self, typename, xml_root, ns):
        '''
        Parse XML node
        
        :param typename: The type name of the topic (ex : PAGMemberType)
        :type typename: str, QString
        
        :param ns: XSD namespaces
        :type ns: dict
        '''
        
        xml_element = xml_root.find('xsd:complexType[@name="{}"]'.format(typename), ns)
        members_elements = xml_element.findall('.//xsd:choice/xsd:element', ns)
        
        members = list()
        
        for element in members_elements:
            name = element.get('ref')
            if not name.endswith('.GEOMETRIE'):
                members.append(name)
        
        return members
    
class PAGType(object):
    '''
    A PAG XSD type
    '''
    
    def __init__(self):
        '''
        Constructor
        '''
        
        self.geometry_type = None        
        self.fields = list()
    
    def parse(self, name, xml_element, ns):
        '''
        Parse XML node
        
        :param name: The name of the type
        :type name: str, QString
        
        :param xml_element: The root XML node of the type (xsd:complexType)
        :type xml_element: Element
        
        :param ns: XSD namespaces
        :type ns: dict
        '''
        
        # Type name
        self.name = name
        self.geometry_type = None
        
        self.fields = list()
        
        sequence = xml_element.find('.//xsd:sequence',ns)
        elements = sequence.findall('xsd:element',ns)
        
        for element in elements:
            # Process geometry
            if element.get('name')=='GEOMETRIE':
                self.geometry_type = self._getGeometry(element, ns)
            # Process field
            else:
                pag_field = PAGField()
                pag_field.parse(element, ns)
                self.fields.append(pag_field)
                
    def friendlyName(self):
        '''
        Gets the friendly name of the type aka table name
        E.g. BIOTOPE_LIGNE for ARTIKEL17.BIOTOPE_LIGNE
        '''
        
        if self.name is None:
            return ''
        
        split = self.name.split('.')
        
        return split[-1]
        
    def topic(self):
        '''
        Gets the topic of the type
        E.g. ARTIKEL17 for ARTIKEL17.BIOTOPE_LIGNE
        '''
        
        if self.name is None:
            return ''
        
        split = self.name.split('.')
        
        return split[0]
    
    def getField(self, fieldname):
        '''
        Get a field from the name
        
        :param fieldname: The field name (ex : CODE)
        :type fieldname: str, QString
        '''
        
        for field in self.fields:
            if field.name == fieldname:
                return field
        
        return None
    
    def _getGeometry(self, xml_element, ns):
        '''
        Returns the geometry of the type
        
        :param xml_element: The root XML node of the geometry (xsd:element)
        :type xml_element: Element
        
        :param ns: XSD namespaces
        :type ns: dict
        '''
        
        geometries = {'LUREF':GeometryType.POINT,
                      'gml:CurvePropertyType':GeometryType.POLYLINE,
                      'gml:SurfacePropertyType':GeometryType.POLYGON}
        
        return geometries[xml_element.get('type')]
    
class PAGField(object):
    '''
    A PAG XSD field
    '''
    
    def __init__(self):
        '''
        Constructor
        '''
        self.nullable = True
        self.type = DataType.STRING
        self.length = None
        self.minvalue = None
        self.maxvalue = None
        self.listofvalues = None
    
    def parse(self, xml_element, ns):
        '''
        Parse XML node
        
        :param xml_element: The root XML node of the field (xsd:element)
        :type xml_element: Element
        
        :param ns: XSD namespaces
        :type ns: dict
        '''
        
        # Field name
        self.name = xml_element.get('name')
        
        # Field is nullable
        self.nullable = xml_element.get('minOccurs') is not None and xml_element.get('minOccurs')=='0'
        
        type = self._getDataType(xml_element, ns)
        
        # Data type
        self.type = type[0]
        
        # Text length
        self.length = type[1]
        
        # Numeric or date min value
        self.minvalue = type[2]
        
        # Numeric or date max value
        self.maxvalue = type[3]
        
        # List of possible values, enumeration
        self.listofvalues = type[4]
        
    def _getDataType(self, xml_element, ns):
        '''
        Returns the datatype of the field
        
        :param xml_element: The root XML node of the data type (xsd:element)
        :type xml_element: Element
        
        :param ns: XSD namespaces
        :type ns: dict
        '''
        
        # Dictionary of data types
        datatypes = {'xsd:string':DataType.STRING,
                     'xsd:normalizedString':DataType.STRING,
                     'xsd:integer':DataType.INTEGER,
                     'xsd:double':DataType.DOUBLE,
                     'xsd:decimal':DataType.DOUBLE,
                     'xsd:date':DataType.DATE}
        
        # XSD restriction element
        restriction = xml_element.find('.//xsd:restriction',ns)
        
        # Data type
        type = datatypes[restriction.get('base')]
        
        # Length
        length_element = restriction.find('xsd:maxLength',ns)
        length = length_element.get('value') if length_element is not None else None
        
        # Minimum inclusive value
        minvalue_element = restriction.find('xsd:minInclusive',ns)
        minvalue = minvalue_element.get('value') if minvalue_element is not None else None
        
        # Maximum inclusive value
        maxvalue_element = restriction.find('xsd:maxInclusive',ns)
        maxvalue = maxvalue_element.get('value') if maxvalue_element is not None else None
        
        # Enumeration
        enumeration_elements = restriction.findall('xsd:enumeration',ns)
        enumeration = list()
        for enumeration_element in enumeration_elements:
            enumeration.append(enumeration_element.get('value'))
        
        return type, length, minvalue, maxvalue, enumeration if len(enumeration)>0 else None
    
    def getEnumerationMap(self):
        map = dict()
        
        for element in self.listofvalues:
            split = element.split(',')
            map[split[0]]=split[0] #split1
            
        return map
    
class GeometryType:
    '''
    Geometry types
    '''
    
    POINT='POINT'
    POLYLINE='LINESTRING'
    POLYGON='POLYGON'
    
class DataType:
    '''
    Data types
    '''
    
    STRING='string'
    INTEGER='integer'
    DOUBLE='double'
    DATE='date'

XSD_QGIS_DATATYPE_MAP = {DataType.STRING:QVariant.String,
               DataType.INTEGER:QVariant.LongLong,
               DataType.DOUBLE:QVariant.Double,
               DataType.DATE:QVariant.String}

XSD_QGIS_GEOMETRYTYPE_MAP = {GeometryType.POINT:QGis.Point,
                             GeometryType.POLYLINE:QGis.Line,
                             GeometryType.POLYGON:QGis.Polygon}