# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PagLuxembourg
                                 A QGIS plugin
 Gestion de Plans d'Aménagement Général du Grand-Duché de Luxembourg
                             -------------------
        begin                : 2015-08-25
        copyright            : (C) 2015 by arx iT
        email                : mba@arxit.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load PagLuxembourg class from file PagLuxembourg.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .pag_luxembourg import PagLuxembourg
    return PagLuxembourg(iface)
