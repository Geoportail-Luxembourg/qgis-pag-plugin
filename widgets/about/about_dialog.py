# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CreateProjectDialog
                                 A QGIS plugin
 Gestion de Plans d'Aménagement Général du Grand-Duché de Luxembourg
                             -------------------
        begin                : 2015-09-09
        git sha              : $Format:%H$
        copyright            : (C) 2015 by arx iT
        email                : mba@arxit.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QFileDialog, QMessageBox, QPixmap
from PyQt4.QtCore import QCoreApplication

import PagLuxembourg.main

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'about_dialog.ui'))


class AboutDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        '''
        Constructor.
        '''
        
        super(AboutDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        logo_path = os.path.join(
            PagLuxembourg.main.plugin_dir,
            'widgets',
            'about',
            'logo_pag.png')
        pixmap = QPixmap(logo_path)
        self.lblLogoPlugin.setPixmap(pixmap)
        
        logo_path = os.path.join(
            PagLuxembourg.main.plugin_dir,
            'widgets',
            'about',
            'logo_arxit.png')
        pixmap = QPixmap(logo_path)
        self.lblLogoArxit.setPixmap(pixmap)