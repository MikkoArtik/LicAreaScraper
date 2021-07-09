# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LicAreaScraper
                                 A QGIS plugin
 Plugin for getting licence area SHP-file 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Michael Chernov
        email                : mihail.tchernov@yandex.ru
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
from typing import NamedTuple, List, Tuple
import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsVectorLayer, QgsProject
from qgis.core import QgsFillSymbol
from qgis.core import QgsApplication

from .resources import *
from .lic_area_scraper_dialog import LicAreaScraperDialog

from .core.scraper import get_coords_lines
from .core.parser import line_parse
from .core.processing import split_points_by_polygon_nodes
from .core.processing import create_polygon
from .core.processing import create_shp_file


SHP_FILENAME = 'LicArea.shp'


class FormContainer(NamedTuple):
    url: str
    export_folder: str
    deposit_name: str
    is_add_to_map: bool


def show_message(message_text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(message_text)
    msg.exec_()


class LicAreaScraper:
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LicAreaScraper_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Licence area scraper')

        self.dlg = LicAreaScraperDialog()
        self.dlg.bOpenFolder.clicked.connect(self.open_folder_dialog)
        self.dlg.bCreate.clicked.connect(self.create_shp_file)

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LicAreaScraper', message)

    def add_action( self, icon_path, text, callback, enabled_flag=True,
            add_to_menu=True, add_to_toolbar=True, status_tip=None,
            whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/LicAreaScraper/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Licence area scraper'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Licence area scraper'),
                action)
            self.iface.removeToolBarIcon(action)

    def set_start_form_state(self):
        ui = self.dlg
        ui.eUrl.clear()
        ui.eFolderPath.clear()
        ui.eDepositName.clear()
        ui.cbIsAddToMap.setChecked(False)

    def open_folder_dialog(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory()
        self.dlg.eFolderPath.setText(folder_path)

    def get_form_data(self) -> FormContainer:
        ui = self.dlg
        return FormContainer(ui.eUrl.text(), ui.eFolderPath.text(),
                             ui.eDepositName.text(),
                             ui.cbIsAddToMap.isChecked()
                             )

    def get_vertexes(self) -> List[Tuple[float, float]]:
        result = []
        form_data = self.get_form_data()
        for line in get_coords_lines(form_data.url):
            longitude, latitude = line_parse(line)
            result.append((longitude, latitude))
        return result

    def add_vector_layer(self):
        form_data = self.get_form_data()
        path = os.path.join(form_data.export_folder, SHP_FILENAME)
        if not os.path.exists(path):
            return
        deposit_name = 'LicArea' if not form_data.deposit_name else form_data.deposit_name
        layer = QgsVectorLayer(path, deposit_name, 'ogr')
        if not layer.isValid():
            return

        symbol = QgsFillSymbol.createSimple({"color": "0,0,0,0",
                                             "outline_color": "255,0,0",
                                             "outline_style": "solid",
                                             "outline_width": "1"}
                                            )
        render = layer.renderer()
        render.setSymbol(symbol)
        QgsProject.instance().addMapLayer(layer)

    def create_shp_file(self):
        form_data = self.get_form_data()
        all_vertexes = self.get_vertexes()
        polygons_nodes = split_points_by_polygon_nodes(all_vertexes)
        polygons = [create_polygon(x) for x in polygons_nodes]
        if not polygons:
            show_message('No data for saving. Please check '
                         'url-address and web-page content.\n\n'
                         'Notice: now plugin make scrape data only '
                         'site https://www.nedraexpert.ru/\n'
                         'If you want add new site for scraping, please '
                         'write me email: mihail.tchernov@yandex.ru')
            return

        path = os.path.join(form_data.export_folder, SHP_FILENAME)

        deposit_name = 'NULL' if not form_data.deposit_name else form_data.deposit_name
        create_shp_file(path, polygons, deposit_name)
        if form_data.is_add_to_map:
            self.add_vector_layer()

    def run(self):
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            pass
        self.set_start_form_state()
