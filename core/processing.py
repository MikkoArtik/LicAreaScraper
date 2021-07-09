from typing import List, Tuple

from qgis.core import QgsGeometry
from qgis.core import QgsPointXY, QgsPolygon
from qgis.core import QgsFields, QgsField, QgsFeature
from qgis.core import QgsVectorFileWriter, QgsWkbTypes
from qgis.core import QgsCoordinateReferenceSystem

from qgis.PyQt.QtCore import QVariant


WGS84_EPSG_ID = 4326


def split_points_by_polygon_nodes(nodes: List[Tuple[float, float]]) -> \
        List[List[Tuple[float, float]]]:
    all_polygons, current_polygon = [], []
    for node in nodes:
        if not current_polygon:
            current_polygon.append(node)
            continue

        current_polygon.append(node)
        if node == current_polygon[0]:
            all_polygons.append(current_polygon)
            current_polygon = []
    return all_polygons


def create_polygon(nodes: List[Tuple[float, float]]) -> QgsPolygon:
    return QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in nodes]])


def create_shp_file(export_path: str, polygons: List[QgsPolygon],
                    deposit_name='NULL'):
    fields = QgsFields()
    fields.append(QgsField('Deposit', QVariant.String))

    writer = QgsVectorFileWriter(
        export_path, 'UTF-8', fields, QgsWkbTypes.Polygon,
        QgsCoordinateReferenceSystem(WGS84_EPSG_ID), 'ESRI Shapefile')

    for polygon_item in polygons:
        item = QgsFeature()
        item.setGeometry(polygon_item)
        item.setAttributes([deposit_name])
        writer.addFeature(item)
