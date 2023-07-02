#! /usr/bin/python3

import fileinput
import importlib
import lxml
import lxml.html
import os
import requests
import shapely.ops
import sys
import modules.OsmGeom

main_url = "http://polygons.openstreetmap.fr/"
relation_generation_url = main_url + "index.py"
polygon_union_url = main_url + "get_poly.py"

def generate_poly(country_name, polygon_id):
  print("  ", country_name, polygon_id)

  out_file = os.path.join("generated-polygons", country_name + ".poly")
  if os.path.exists(out_file):
    return

  dir_name = os.path.join("generated-polygons", os.path.dirname(country_name))
  if not os.path.exists(dir_name):
    os.makedirs(dir_name)

  # generate relation boundary
  x = 0
  y = 0
  z = 0

  if isinstance(polygon_id, int):
    polygon_id = (polygon_id, )
  for id in polygon_id:
    r = requests.get(relation_generation_url, params={"id": id})
    parser = lxml.html.HTMLParser(encoding='UTF-8')
    p = lxml.html.fromstring(r.text, parser=parser)

    print(relation_generation_url + "?id=" + str(id))

    try:
      form = p.forms[1]
      x = max(x, float(form.inputs["x"].value))
      y = max(y, float(form.inputs["y"].value))
      z = max(z, float(form.inputs["z"].value))
    except:
      print("    * ERROR * ")
      return

  for id in polygon_id:
    r = requests.get(relation_generation_url, params={"id": id})
    parser = lxml.html.HTMLParser(encoding='UTF-8')
    p = lxml.html.fromstring(r.text, parser=parser)

    if not ("%f-%f-%f" % (x, y, z)) in r.text:
      r = requests.post(relation_generation_url, params={"id": id}, data={"x": x, "y": y, "z": z})


  r = requests.get(polygon_union_url, params={"id": ",".join(map(str, polygon_id)),
                                              "params": "%f-%f-%f" % (x,y,z)})
  print(r.url)

  out_file = os.path.join("generated-polygons", country_name + ".poly")
  with open(out_file, "wb") as text_file:
    text_file.write(r.content)

def read_polygon(f_name):
  with open(f_name, "r") as f:
    name = f.readline().strip()
    return modules.OsmGeom.read_multipolygon(f)

def write_polygon(f_name, geom):
  os.makedirs(os.path.dirname(f_name), exist_ok=True)
  with open(f_name, "w") as f:
    return modules.OsmGeom.write_multipolygon(f, geom)

def union_update(country_name, polygon_id):
  if isinstance(polygon_id, int):
    polygon_id = (polygon_id, )

  orig_poly = read_polygon(os.path.join("polygons", country_name + ".poly"))
  generated_poly = read_polygon(os.path.join("generated-polygons", country_name + ".poly"))

  relation_file = os.path.join("relation-polygons", country_name + ".poly")
  if not os.path.exists(relation_file):
    dir_name = os.path.join("relation-polygons", os.path.dirname(country_name))
    if not os.path.exists(dir_name):
      os.makedirs(dir_name)

    r = requests.get(polygon_union_url, params={"id": ",".join(map(str, polygon_id)),
                                                "params": "0"})
    print(r.url)
    with open(relation_file, "wb") as text_file:
      text_file.write(r.content)

  relation_poly = read_polygon(relation_file)

  if not orig_poly.contains(relation_poly):
    new_poly = shapely.ops.unary_union([orig_poly, generated_poly])
    write_polygon(os.path.join("updated-polygons", country_name + ".poly"), shapely.wkt.loads(shapely.wkt.dumps(new_poly, rounding_precision=3)).wkt)
    print("   updated")
  else:
    try:
      os.unlink(os.path.join("updated-polygons", country_name + ".poly"))
    except:
      pass

def generate_poly_merge(merge_name, merge_sources):
  print(merge_name, merge_sources)

  merge_polys = []

  for m in merge_sources:
    merge_polys.append(read_polygon(os.path.join("polygons", m + ".poly")))

  merge_poly = shapely.ops.unary_union(merge_polys)
  write_polygon(os.path.join("polygons-merge", merge_name + ".poly"), shapely.wkt.loads(shapely.wkt.dumps(merge_poly, rounding_precision=3)).wkt)
  print("   generated")


if __name__ == '__main__':

  import argparse

  parser = argparse.ArgumentParser(description="Initialise polygon files from %s" % main_url)
  parser.add_argument("--file", dest="file", action="store",
                      help="Get list of extracts to generate - format 'name rel_id' per line")
  parser.add_argument("--region", dest="regions", action="store", nargs="+",
                      help="Get list of region to generate - rel_id from osmose backend")
  parser.add_argument("--country", dest="country", action="store", nargs="+",
                      help="Get list of country to generate - rel_id from osmose backend")
  parser.add_argument("--union-update", dest="union_update", action="store_true",
                      help="Update polygon, by doing an Union with previous polygon")
  parser.add_argument("--merge", dest="merge", action="store_true",
                      help="Generate merge polygons")
  args = parser.parse_args()

  if args.file:
    with open(args.file) as f:
      for line in f.readlines():
        (country_name, polygon_id) = line.split()
        polygon_id = [int(i) for i in polygon_id.split(",")]
        generate_poly(country_name, polygon_id)

  if args.regions:
    sys.path.insert(0, "osmose-backend")
    importlib.reload(modules)  # needed as was loaded by import modules.OsmGeom
    import osmose_config
    for r in osmose_config.config.values():
      if not "state.txt" in r.download:
        continue
      if not "download.openstreetmap.fr" in r.download["state.txt"]:
        continue
      found = False
      for region in args.regions:
        if not found and region in r.download["state.txt"]:
          found = True
          country_name = r.download["state.txt"].split("extracts/")[1].split(".state.txt")[0]
          if args.country and not country_name.split("/")[-1] in args.country:
            continue
          polygon_id = r.polygon_id
          print(country_name)
          if country_name in ("north-america/canada/nunavut", "north-america/canada/quebec/nord_du_quebec"):
            print("  - skipped")
            continue
          generate_poly(country_name, polygon_id)
          if args.union_update:
            union_update(country_name, polygon_id)

  if args.merge:
    for merge_name in os.listdir('merge'):
      merge_sources = []
      with open(os.path.join('merge', merge_name)) as f:
        for line in f.readlines():
           merge_sources.append(line.strip())
      generate_poly_merge(merge_name, merge_sources)
