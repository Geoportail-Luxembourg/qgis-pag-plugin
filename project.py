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
    PAG project
    '''

    def __init__(self):
        '''
        Constructor
        '''
        pass    
    
    def create(self, folder, name):
        '''
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
        QgsProject.instance().write()
        
        self.updateDatabase()
        
    def updateDatabase(self):
        self.database = os.path.join(self.folder, DATABASE)
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
            uri = QgsDataSourceURI()
            uri.setDatabase(self.database)
            geom_column = 'GEOMETRY' if type.geometry_type is not None else ''
            uri.setDataSource('', type.name, geom_column,'','OGC_FID')            
            display_name = type.name
            layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
            
            # Create layer if not valid
            if not layer.isValid():
                self.createTable(conn, type, layer)
                layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
                QgsMapLayerRegistry.instance().addMapLayer(layer)
                
            self.updateTable(type, layer)
            
        conn.close()
        del conn
        
    def createTable(self, conn, type, layer):
            # Create table
            query="CREATE TABLE '%s' (OGC_FID integer primary key autoincrement,"%type.name
            
            # Geometry column
            if type.geometry_type is not None: #add geocol
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
    
    def updateTable(self, type, layer):
        for field in type.fields:
            if layer.fieldNameIndex(field.name)<0:
                layer.dataProvider().addAttributes([self.getField(field)])
        
        layer.updateFields()
        
    datatypeMap = {DataType.STRING:QVariant.String,
               DataType.INTEGER:QVariant.Int,
               DataType.DOUBLE:QVariant.Double,
               DataType.DATE:QVariant.String}

    def getField(self, pagfield):
        return QgsField(pagfield.name,
                        self.datatypeMap[pagfield.type],
                        pagfield.type,
                        int(pagfield.length) if pagfield.length is not None else 0)