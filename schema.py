'''
Created on 17 sept. 2015

@author: arxit
'''

import os.path
import xml.etree.ElementTree as ET
import main

class PAGSchema(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.parseXSD()
    
    def parseXSD(self):
        xsd_path = os.path.join(
            main.plugin_dir,
            'assets',
            'PAGschema.xsd')
        
        # XSD namespace
        ns = {'xsd': 'http://www.w3.org/2001/XMLSchema'}
        
        # Parse XSD and get all complex types = tables
        xsd = ET.parse(xsd_path)
        xsd_types = xsd.getroot().findall('xsd:complexType',ns)
        
        self.types = list()
        
        for type in xsd_types:
            # Filtering types to keep those starting with PAG. and having 2 dots (remove PAG.GESTION for example)
            if type.get('name').startswith('PAG.') and type.get('name').count('.')==2:
                self.types.append(PAGType(type,ns))

class PAGType(object):
    '''
    A type contained in the xsd
    '''
    
    def __init__(self, xml_element, ns):
        '''
        Constructor
        '''
        
        # Type name
        self.name = xml_element.get('name')
        self.geometry_type = None
        
        self.fields = list()
        
        sequence = xml_element.find('xsd:sequence',ns)
        elements = sequence.findall('xsd:element',ns)
        
        for element in elements:
            # Process geometry
            if element.get('name')=='GEOMETRIE':
                self.geometry_type = self.getGeometry(element, ns)
            # Process field
            else:
                self.fields.append(PAGField(element, ns))
                
    def getGeometry(self, xml_element, ns):
        '''
        Returns the geometry of the type
        '''
        
        geometries = {'PAG.LUREF':GeometryType.POINT,
                      'POLYLINE':GeometryType.POLYLINE,
                      'SURFACE':GeometryType.POLYGON}
        
        geom_element = xml_element.find('.//xsd:element',ns)
        
        if geom_element is None:
            # Point = PAG.LUREF
            return geometries[xml_element.get('type')]
        else:
            # Polyline, surface
            return geometries[geom_element.get('name')]
    
class PAGField(object):
    '''
    A field
    '''
    
    def __init__(self, xml_element, ns):
        '''
        Constructor
        '''
        
        # Field name
        self.name = xml_element.get('name')
        
        # Field is nullable
        self.nullable = xml_element.get('minOccurs') is not None and xml_element.get('minOccurs')=='0'
        
        type = self.getType(xml_element, ns)
        
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
        
    def getType(self, xml_element, ns):
        '''
        Returns the datatype of the field
        '''
        
        # Dictionary of data types
        datatypes = {'xsd:string':DataType.STRING,
                     'xsd:normalizedString':DataType.STRING,
                     'xsd:integer':DataType.INTEGER,
                     'xsd:double':DataType.DOUBLE,
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
    
class GeometryType:
    '''
    Geometry types
    '''
    
    POINT='point'
    POLYLINE='polyline'
    POLYGON='polygon'
    
class DataType:
    '''
    Data types
    '''
    
    STRING='string'
    INTEGER='integer'
    DOUBLE='double'
    DATE='date'