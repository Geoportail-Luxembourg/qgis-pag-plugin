'''
Created on 18 sept. 2015

@author: arxit
'''

import os.path
from pyspatialite import dbapi2 as db

from qgis.core import *
from PyQt4.QtCore import QFileInfo, QVariant
from PyQt4.QtGui import QMessageBox

import main
from PagLuxembourg.schema import *

FILENAME = 'project.qgs'
DATABASE = 'database.sqlite'

class Project(object):
    '''
    A class which represent a PAG project
    '''

    def __init__(self):
        '''
        Constructor
        '''
        pass    
    
    def open(self, filename):
        '''
        Called when a QGIS project is opened
        
        :param filename: Project filename
        :type filename: str, QString
        '''
        
        # Setting 
        self.folder = os.path.dirname(filename)
        self.filename = filename
        self.database = os.path.join(self.folder, DATABASE)
        
        # Update database
        self._updateDatabase()
        
        # Update map layers
        self._updateLayers()
        
        QgsProject.instance().write()
        
    def create(self, folder, name):
        '''
        Creates a new projects, and loads it in the interface
        
        :param folder: Folder path which will contain the new project folder
        :type folder: str, QString
        
        :param name: Project name, will be the project folder name
        :type name: str, QString
        '''
        
        # Create project path
        self.folder = os.path.join(folder,name)
                
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        
        # Create project filename
        self.filename = os.path.join(self.folder, FILENAME)
        main.qgis_interface.newProject(True)
        QgsProject.instance().setFileName(self.filename)
        #QgsProject.instance().write()
        
        # Database
        self.database = os.path.join(self.folder, DATABASE)
        self._updateDatabase()
        
        # Update map layers
        self._updateLayers()
        
        QgsProject.instance().write()
        
    def _updateDatabase(self):
        '''
        Updates the project database
        '''
        
        xsd_schema = main.xsd_schema
        createdb = not os.path.isfile(self.database)
        
        conn = db.connect(self.database)
        
        # Create database if not exist
        if createdb:
            cursor=conn.cursor() 
            cursor.execute("SELECT InitSpatialMetadata()")
            del cursor
        
        # Check and update fields
        for type in xsd_schema.types:
            uri = self._getTypeUri(type)
            layer = QgsVectorLayer(uri, type.name, 'spatialite')
            
            # Create layer if not valid
            if not layer.isValid():
                self._createTable(conn, type)
                layer = QgsVectorLayer(uri, type.name, 'spatialite')
                
            self._updateTable(type, layer)
            
        conn.close()
        del conn
        
    def _getTypeUri(self, type):
        '''
        Gets a uri to the table according to the XSD
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        uri = QgsDataSourceURI()
        uri.setDatabase(self.database)
        geom_column = 'GEOMETRY' if type.geometry_type is not None else ''
        uri.setDataSource('', type.name, geom_column,'','OGC_FID')
        
        return uri.uri()
        
    def _createTable(self, conn, type):
        '''
        Creates a new table in the spatialite database according to the XSD
        
        :param conn: The database connection
        :type conn: Connection
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        # Create table
        query="CREATE TABLE '%s' (OGC_FID integer primary key autoincrement,"%type.name
        
        # Geometry column
        if type.geometry_type is not None:
            query+="'GEOMETRY' %s,"%type.geometry_type
        
        query=query[:-1]+")"
        cursor=conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        del cursor
        
        # Register geometry column
        if type.geometry_type is not None:
            query="SELECT RecoverGeometryColumn('%s','GEOMETRY',2169,'%s',2)"%(type.name,type.geometry_type)
            cursor=conn.cursor()
            cursor.execute(query)
            rep=cursor.fetchall()
            
            if rep[0][0]==0:
                conn.rollback()
            else:
                conn.commit()
            
            cursor.close()
            del cursor
    
    def _updateTable(self, type, layer):
        '''
        Updates the layer's table according to the XSD
        
        :param type: XSD schema type
        :type type: PAGType
        
        :param layer: the QGIS vector layer object
        :type layer: QgsVectorLayer
        '''
        
        for field in type.fields:
            if layer.fieldNameIndex(field.name)<0:
                layer.dataProvider().addAttributes([self._getField(field)])
        
        layer.updateFields()
        
    # Mapping between XSD datatype and QGIS datatype
    datatypeMap = {DataType.STRING:QVariant.String,
               DataType.INTEGER:QVariant.Int,
               DataType.DOUBLE:QVariant.Double,
               DataType.DATE:QVariant.String}

    def _getField(self, pagfield):
        '''
        Creates a QGIS Field according to the XSD
        
        :param pagfield: XSD schema field
        :type pagfield: PAGField
        
        :returns: The corresponding QGIS Field
        :rtype: QgsField
        '''
        
        return QgsField(pagfield.name,
                        self.datatypeMap[pagfield.type],
                        pagfield.type,
                        int(pagfield.length) if pagfield.length is not None else 0)
        
    def _updateLayers(self):
        '''
        Update layers attributes editors
        '''
        # Map layers in the TOC
        maplayers = QgsMapLayerRegistry.instance().mapLayers()
        
        # Keep only vector layers
        for k,v in maplayers.iteritems():
            if v.type()!=QgsMapLayer.VectorLayer:
                del maplayers[k]
        
        maplayers = QgsMapLayerRegistry.instance().mapLayers()
        
        # Iterates through XSD types
        for type in main.xsd_schema.types:
            uri = self._getTypeUri(type)
            found = False
            
            # Check is a layer with type datasource exists in the TOC
            for k,v in maplayers.iteritems():
                if self._compareURIs(v.source(), uri):
                    found = True
                    break
            
            # If not found, add to the TOC
            if not found:
                layer = QgsVectorLayer(uri, type.name, 'spatialite')
                QgsMapLayerRegistry.instance().addMapLayer(layer)
                
        
                
    def _compareURIs(self, uri1, uri2):
        '''
        Compares 2 URIs
        In case direct string comparison is not enough
        
        :param uri1: URI 1
        :type uri1: QString
        
        :param uri2: URI 2
        :type uri2: QString
        
        :returns: True is the URIs point to the same table
        :rtype: Boolean
        '''
        
        return v.source() == uri