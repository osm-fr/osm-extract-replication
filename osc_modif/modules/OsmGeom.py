#! /usr/bin/env python3
#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Jocelyn Jaubert <jocelyn.jaubert@gmail.com> 2011           ##
##                                                                       ##
## This program is free software: you can redistribute it and/or modify  ##
## it under the terms of the GNU General Public License as published by  ##
## the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                   ##
##                                                                       ##
## This program is distributed in the hope that it will be useful,       ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of        ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         ##
## GNU General Public License for more details.                          ##
##                                                                       ##
## You should have received a copy of the GNU General Public License     ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>. ##
##                                                                       ##
###########################################################################

import re
from shapely.wkt import loads
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.geometry import Point

# Read a polygon from file
# NB: holes aren't supported yet
def read_polygon_wkt(f):

    coords = []
    first_coord = True
    while True:
        line = f.readline()
        if not(line):
            break;
            
        line = line.strip()
        if line == "END":
            break
        
        if not(line):
            continue
        
        ords = line.split()
        coords.append("%f %f" % (float(ords[0]), float(ords[1])))
    
    if len(coords) < 3:
        return None

    polygon = "((" + ", ".join(coords) + "))"
    
    return polygon    

# Read a multipolygon from the file
# First line: name (discarded)
# Polygon: numeric identifier, list of lon, lat, END
# Last line: END
def read_multipolygon_wkt(f):

    polygons = []
    skip_polygon = False
    while True:
        dummy = f.readline()
        if not(dummy):
            break
        if dummy[0] == "!":
            # this is a hole
            skip_polygon = True
        
        polygon = read_polygon_wkt(f)
        if polygon != None and not skip_polygon:
            polygons.append(polygon)
        skip_polygon = False

    wkt = "MULTIPOLYGON (" + ",".join(polygons) + ")"
    
    return wkt        

def read_multipolygon(f):
    wkt = read_multipolygon_wkt(f)
    return loads(wkt)

def write_polygon(f, wkt, p):

    match = re.search("^\(\((?P<pdata>.*)\)\)$", wkt)
    pdata = match.group("pdata")
    rings = re.split("\), *\(", pdata)

    first_ring = True
    for ring in rings:
        coords = re.split(",", ring)

        p = p + 1
        if first_ring:
            f.write(str(p) + "\n")
            first_ring = False
        else:
            f.write("!" + str(p) + "\n")

        for coord in coords:
            ords = coord.split()
            f.write("\t%s\t%s\n" % (ords[0], ords[1]))

        f.write("END\n")

    return p

def write_multipolygon(f, wkt):

    match = re.search("^MULTIPOLYGON *\((?P<mpdata>.*)\)$", wkt)

    if match:
        f.write("polygon\n")
        mpdata = match.group("mpdata")
        polygons = re.split("(?<=\)\)), *(?=\(\()", mpdata)

        p = 0
        for polygon in polygons:
            p = write_polygon(f, polygon, p)

        f.write("END\n")
        return

    match = re.search("^POLYGON *(?P<pdata>.*)$", wkt)
    if match:
        f.write("polygon\n")
        pdata = match.group("pdata")
        write_polygon(f, pdata, 0)
        f.write("END\n")


def check_intersection(polygon, coords):
    if len(coords) == 2:
        (lat, lon) = coords
        obj = Point((lon, lat))
    elif len(coords) == 4:
        minlat = float(coords["minlat"])
        minlon = float(coords["minlon"])
        maxlat = float(coords["maxlat"])
        maxlon = float(coords["maxlon"])
        if minlat == maxlat and minlon == maxlon:
            obj = Point((minlon, minlat))
        elif minlat == maxlat or minlon == maxlon:
            obj = LineString([(minlon, minlat), (maxlon, maxlat)])
        else:
            obj = Polygon(((minlon, minlat), (minlon, maxlat),
                           (maxlon, maxlat), (maxlon, minlat)))

    return polygon.intersects(obj)

###########################################################################

if __name__ == "__main__":
    import sys
    f = sys.stdin
        
    name = f.readline().strip()
    geom = read_multipolygon(f)
    f.close()

    print(geom.area)

    print(check_intersection(geom, (1, 1)))
    print(check_intersection(geom, (48, 2)))

###########################################################################
import unittest

class Test(unittest.TestCase):
    def test_africa(self):
        f = open("polygons/africa.poly", "r")
        name = f.readline().strip()
        self.assertEqual(name, "africa")
        poly = read_multipolygon(f)
        self.assertEqual(poly, MultiPolygon([((
            (11.60092, 33.99875),
            (11.60207, 37.77817),
            (3.525989, 37.76444),
            (-1.967826, 36.32171),
            (-4.287849, 36.20082),
            (-5.60294, 35.9877),
            (-9.618688, 35.98102),
            (-15.514733, 29.500826),
            (-27.262032, 30.814),
            (-23.24536, -60.3167),
            (44.63942, -57.08798),
            (66.722766, -14.903707),
            (51.63025, 12.55015),
            (44.20775, 11.6786),
            (43.654172, 12.549204),
            (43.357541, 12.634981),
            (43.338315, 12.790377),
            (43.107602, 13.210537),
            (42.679135, 13.592602),
            (42.517084, 14.088635),
            (42.044667, 14.711145),
            (39.813119, 18.162296),
            (37.902821, 22.23827),
            (34.741261, 27.031591),
            (34.475784, 28.006527),
            (34.705809, 28.576081),
            (34.93741, 29.42519),
            (34.879703, 29.557033),
            (34.885883, 29.642857),
            (34.84924, 29.78666),
            (34.24284, 31.296815),
            (32.706293, 33.975258),
            (11.60092, 33.99875),
        ), [])]))

    def test_canarias(self):
        f = open("polygons/africa/spain/canarias.poly", "r")
        name = f.readline().strip()
        poly = read_multipolygon(f)
        self.assertEqual(len(poly.geoms), 9)
        self.assertEqual(len(poly.geoms[0].exterior.coords), 8)
        self.assertEqual(len(poly.geoms[1].exterior.coords), 55)
        self.assertEqual(len(poly.geoms[2].exterior.coords), 9)
        self.assertEqual(len(poly.geoms[3].exterior.coords), 61)
        self.assertEqual(len(poly.geoms[4].exterior.coords), 69)

        self.assertEqual(check_intersection(poly, (0, 0)), False)
        self.assertEqual(check_intersection(poly, (28.1876, -16.6015)), True)

        bbox = { "minlat": -26.6015000,
                 "maxlat": 0,
                 "minlon": -36.6015000,
                 "maxlon": -26.6015000,
               }
        self.assertEqual(check_intersection(poly, bbox), False)

        bbox = { "minlat": 28.1875000,
                 "maxlat": 28.1876000,
                 "minlon": -16.6015200,
                 "maxlon": -16.6015100,
               }
        self.assertEqual(check_intersection(poly, bbox), True)

        bbox = { "minlat": 28.1875000,
                 "maxlat": 28.1875000,
                 "minlon": -16.6015200,
                 "maxlon": -16.6015200,
               }
        self.assertEqual(check_intersection(poly, bbox), True)

        bbox = { "minlat": 28.1875000,
                 "maxlat": 28.1875000,
                 "minlon": -16.6015200,
                 "maxlon": -16.6015100,
               }
        self.assertEqual(check_intersection(poly, bbox), True)
