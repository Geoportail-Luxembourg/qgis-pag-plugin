'''
Created on 18 sept. 2015

@author: arxit
'''

import os.path
from pyspatialite import dbapi2 as db

from qgis.core import *
from PyQt4.QtCore import QFileInfo, QVariant, QObject, pyqtSignal
from PyQt4.QtGui import QMessageBox

import main
from PagLuxembourg.schema import *
from PagLuxembourg.widgets.stylize.stylize import *
from PagLuxembourg.widgets.topology.topology import *

FILENAME = 'project.qgs'
DATABASE = 'database.sqlite'
PK = 'OGC_FID'

class Project(QObject):
    '''
    A class which represent a PAG project
    '''

    ready = pyqtSignal()
    
    def __init__(self):
        '''
        Constructor
        '''
        super(Project, self).__init__()
        self.creation_mode = False
    
    def open(self):
        '''
        Called when a QGIS project is opened
        '''
        
        # Signal QgsInterface.projectRead seems to be emited twice
        if QgsProject is None:
            return
        
        # QGIS emits projectRead when creating a new project
        if self.creation_mode:
            return
        
        # Setting
        filename = QgsProject.instance().fileName()
        self.folder = os.path.normpath(os.path.dirname(filename))
        self.filename = os.path.normpath(filename)
        self.database = os.path.join(self.folder, DATABASE)
        
        # If not PAG project return
        if not self.isPagProject():
            self.ready.emit()
            return
        
        # Update database
        self._updateDatabase()
        
        # Update map layers
        self._updateMapLayers()
        
        QgsProject.instance().write()
        
        self.ready.emit()
        
    def create(self, folder, name):
        '''
        Creates a new projects, and loads it in the interface
        
        :param folder: Folder path which will contain the new project folder
        :type folder: str, QString
        
        :param name: Project name, will be the project folder name
        :type name: str, QString
        '''
        
        self.creation_mode = True
        
        # Create project path
        self.folder = os.path.normpath(os.path.join(folder,name))
                
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        
        # Create project filename
        self.filename = os.path.join(self.folder, FILENAME)
        main.qgis_interface.newProject(True)
        QgsProject.instance().setFileName(self.filename)
        
        QgsProject.instance().write()
        
        # Database
        self.database = os.path.join(self.folder, DATABASE)
        self._updateDatabase()
        
        # Update map layers
        self._updateMapLayers()
        
        QgsProject.instance().write()
        
        self.creation_mode = False
        
        # Notify project is ready
        self.ready.emit()
        
    def isPagProject(self):
        '''
        Indicates whether this is a PAG project
        '''
        #return True
        try:
            # New project
            if not os.path.isfile(self.filename):
                return False
            
            # Metadata table
            metadata_table = PAGType()
            metadata_table.name = 'Metadata'
            uri = self.getTypeUri(metadata_table)
            layer = QgsVectorLayer(uri, metadata_table.name, 'spatialite')
            
            if not layer.isValid():
                return False
            
            exp = QgsExpression('Key=\'ProjetPAG\'')
            features = layer.getFeatures(QgsFeatureRequest(exp))
            
            # Features count
            count = 0
            for feature in features:
                count = count + 1
            
            if count == 0:
                return False
            else:
                return True
        
        except AttributeError:
            return False
            
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
        
        # Check and update tables
        for type in xsd_schema.types:
            uri = self.getTypeUri(type)
            layer = QgsVectorLayer(uri, type.friendlyName(), 'spatialite')
            
            # Create layer if not valid
            if not layer.isValid():
                self._createTable(conn, type)
                layer = QgsVectorLayer(uri, type.friendlyName(), 'spatialite')
                
            self._updateTable(type, layer)
            
        # Check and update metadata
        self._updateMetadataTable(conn)
        
        conn.close()
        del conn
        
    def getTypeUri(self, type):
        '''
        Gets a uri to the table according to the XSD
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        uri = QgsDataSourceURI()
        uri.setDatabase(self.database)
        geom_column = 'GEOMETRY' if type.geometry_type is not None else ''
        uri.setDataSource('', type.name, geom_column,'',PK)
        
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
        query="CREATE TABLE '%s' (%s integer primary key autoincrement,"%(type.name,PK)
        
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
    
    def _updateMetadataTable(self, conn):
        '''
        Update the metadata table (Metadata)
        
        :param conn: The database connection
        :type conn: Connection
        '''
        
        # Metadata table
        metadata_table = PAGType()
        metadata_table.name = 'Metadata'
        
        # Key field
        key_field = PAGField()
        key_field.name = 'Key'
        key_field.type = DataType.STRING
        key_field.nullable = False
        metadata_table.fields.append(key_field)
        
        # Value field
        value_field = PAGField()
        value_field.name = 'Value'
        value_field.type = DataType.STRING
        value_field.nullable = False
        metadata_table.fields.append(value_field)
        
        uri = self.getTypeUri(metadata_table)
        layer = QgsVectorLayer(uri, metadata_table.friendlyName(), 'spatialite')
        
        # Create table if not valid
        if not layer.isValid():
            self._createTable(conn, metadata_table)
            layer = QgsVectorLayer(uri, metadata_table.friendlyName(), 'spatialite')
        
        # Update fields
        self._updateTable(metadata_table, layer)
        
        features = layer.getFeatures()
        
        # Add features if empty
        if layer.featureCount() == 0:
            feat = QgsFeature(layer.pendingFields())
            feat.setAttribute('Key', 'ProjetPAG')
            feat.setAttribute('Value', '1')
            layer.dataProvider().addFeatures([feat])
            feat = QgsFeature(layer.pendingFields())
            feat.setAttribute('Key', 'PluginVersion')
            feat.setAttribute('Value', main.PLUGIN_VERSION)
            layer.dataProvider().addFeatures([feat])
        else:
            exp = QgsExpression('Key=\'PluginVersion\'')
            feat = layer.getFeatures(QgsFeatureRequest(exp)).next()
            changes = {layer.fieldNameIndex('Value'):main.PLUGIN_VERSION}
            layer.dataProvider().changeAttributeValues({ feat.id() : changes })
        
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
        
    def _updateMapLayers(self):
        '''
        Update layers attributes editors and add missing layers to the TOC
        '''
        
        # Map layers in the TOC
        maplayers = QgsMapLayerRegistry.instance().mapLayers()
        
        # Iterates through XSD types
        for type in main.xsd_schema.types:
            uri = self.getTypeUri(type)
            found = False
            
            # Check is a layer with type data source exists in the map
            for k,v in maplayers.iteritems():
                if self.compareURIs(v.source(), uri):
                    found = True
                    layer = v
                    break
            
            # If not found, add to the map
            if not found:
                layer = QgsVectorLayer(uri, type.friendlyName(), 'spatialite')
                self._addMapLayer(layer, type)
            
            # Update attributes editors
            self._updateLayerEditors(layer, type)
        
        # Updates layers style
        StylizeProject().run()
        
        # Add topology rules
        TopologyChecker(None).updateProjectRules()
                
    def _addMapLayer(self, layer, type):
        '''
        Adds a layer to the map
        
        :param layer: The layer to update
        :type layer: QgsVectorLayer
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        # Add to map
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        
        # Add to the correct topic group
        legend = main.qgis_interface.legendInterface()
        
        if type.topic() not in legend.groups():
            legend.addGroup(type.topic())
        
        group_index = legend.groups().index(type.topic())
        legend.moveLayer(layer,group_index)
        
    def getUriInfos(self, uri):
        '''
        Gets the database and table name from uri
        
        :param uri: URI
        :type uri: QString
        
        :returns: Database and table name
        :rtype: tuple(QString, QString)
        '''
        split = uri.split(' ')
        for kv in split:
            if kv.startswith('dbname'):
                db = os.path.normpath(kv[8:-1])
            if kv.startswith('table'):
                table = kv[7:-1]
                
        return db,table
                
    def compareURIs(self, uri1, uri2):
        '''
        Compares 2 URIs
        
        :param uri1: URI 1
        :type uri1: QString
        
        :param uri2: URI 2
        :type uri2: QString
        
        :returns: True is the URIs point to the same table
        :rtype: Boolean
        '''
        
        # URI 1
        info1 = self.getUriInfos(uri1)
        
        # URI 2
        info2 = self.getUriInfos(uri2)
        
        return info1 == info2
    
    def _updateLayerEditors(self, layer, type):
        '''
        Update the layers attributes editors
        
        :param layer: The layer to update
        :type layer: QgsVectorLayer
        
        :param type: XSD schema type
        :type type: PAGType
        '''
        
        # Hide fields
        hidden = [PK,]
        for field in layer.pendingFields():
            if field.name() in hidden:
                layer.setEditorWidgetV2(layer.fieldNameIndex(field.name()),'Hidden')
        
        # Editors
        for field in type.fields:
            self._setupFieldEditor(field, layer)
    
    fileFields = ['NOM_FICHIER','NOM_EC','NOM_GR']
        
    def _setupFieldEditor(self, field, layer):
        '''
        Update the field editor
        
        :param pagfield: XSD schema field
        :type pagfield: PAGField
        
        :param layer: The layer to update
        :type layer: QgsVectorLayer
        '''
        
        fieldIndex = layer.fieldNameIndex(field.name)
        
        if fieldIndex == -1:
            return
        
        config = dict()
        
        # String
        if field.type == DataType.STRING:
            # Simple text
            editor = 'TextEdit'
            
            # File
            for fileField in self.fileFields:
                if field.name.startswith(fileField):
                    editor = 'FileName'
            
            # Enumeration
            if field.listofvalues is not None:
                editor = 'ValueMap'
                for element in field.listofvalues:
                    split = element.split(',')
                    config[split[0]]=split[0] #split1
            
        # Integer
        elif field.type == DataType.INTEGER:
            editor = 'Range'
            config['Style'] = 'SpinBox'
            config['Min'] = int(field.minvalue) if field.minvalue is not None else -sys.maxint-1
            config['Max'] = int(field.maxvalue) if field.maxvalue is not None else sys.maxint
            config['Step'] = 1
            config['AllowNull'] = field.nullable
            
        # Double
        elif field.type == DataType.DOUBLE:
            editor = 'Range'
            config['Style'] = 'SpinBox'
            config['Min'] = float(field.minvalue) if field.minvalue is not None else -sys.maxint-1
            config['Max'] = float(field.maxvalue) if field.maxvalue is not None else sys.maxint
            mindecimal = len(field.minvalue.split('.')[1]) if field.minvalue is not None and len(field.minvalue.split('.'))==2 else 0
            maxdecimal = len(field.maxvalue.split('.')[1]) if field.maxvalue is not None and len(field.maxvalue.split('.'))==2 else 0
            config['Step'] = 1.0/pow(10,max(mindecimal,maxdecimal))
            config['AllowNull'] = field.nullable
            
        # Date
        elif field.type == DataType.DATE:
            editor = 'DateTime'
            config['field_format'] = 'yyyy-MM-dd'
            config['display_format'] = 'yyyy-MM-dd'
            config['calendar_popup'] = True
            config['allow_null'] = field.nullable
            
        # Other
        else:
            raise NotImplementedError('Unknown datatype')
        
        layer.setEditorWidgetV2(fieldIndex,editor)
        layer.setEditorWidgetV2Config(fieldIndex, config)