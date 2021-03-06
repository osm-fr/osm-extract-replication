<?php
/*
Ce script est distribué sous licence BSD
*/

/* Petite bidouille pour fournir le code source de moi même si ?src est passé en paramètre */
if (isset($_GET['src']))
{
  header("Content-Type: text/plain"); // de toute façon ça se lance dans un cron, sauf cas du :
  die(file_get_contents($_SERVER['SCRIPT_FILENAME'])); 
}
else
  header("Content-type: text/html; charset=UTF-8");

include("../config.php");

function osm_link($type, $osm_id) {
  return "<a href='http://www.openstreetmap.org/browse/$type/$osm_id'>$osm_id</a>&nbsp;<a href='http://localhost:8111/import?url=http://api.openstreetmap.org/api/0.6/$type/$osm_id/full' target='suivi-josm'>josm</a>";
}
function sandre_link($sandre) {
  return "  <a href='http://sandre.eaufrance.fr/app/chainage/courdo/htm/$sandre.php'>$sandre</a>\n";
}


print "<html>
<head>
  <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\"/>
  <title>Affluents en date du $date</title>
</head>
<body>
<style type=\"text/css\">
<!--
table.liste {
  border-collapse: collapse;
}
table.liste tr.origine td {
  border-top: solid 1px;
}
table.liste tr.dernier td {
  border-bottom: solid 1px;
}
table.liste td {
  border-left: dotted 1px;
  border-right: dotted 1px;
  padding-left: 5px;
  padding-right: 5px;
}
table.liste th {
  border-left: dotted 1px;
  border-right: dotted 1px;
  padding-left: 5px;
  padding-right: 5px;
}

-->
</style>
<h2>Affluents en date du $date</h2>
\n";

$max_affluent = 10;  // TODO

$query_affluents ="SELECT ";
for ($i = 1; $i < $max_affluent; $i++) {
  $query_affluents .= "
       rivers[$i][1] AS order$i, rivers[$i][2] AS id$i, rivers[$i][3] AS type$i,
       (CASE WHEN rivers[$i][3] = ascii('R') THEN rt$i.tags->'name' ELSE wt$i.tags->'name' END) AS name$i,
       (CASE WHEN rivers[$i][3] = ascii('R') THEN rt$i.tags->'ref:sandre' ELSE wt$i.tags->'ref:sandre' END) AS sandre$i,
       (CASE WHEN rivers[$i][3] = ascii('R') THEN rt$i.tags->'waterway' ELSE wt$i.tags->'waterway' END) AS waterway$i,
";
  if ($i > 1) {
  $query_affluents .= "
       (CASE WHEN ria$i.way1 IS NOT NULL THEN ria$i.way1 ELSE rib$i.way2 END) AS waya$i,
       (CASE WHEN ria$i.way2 IS NOT NULL THEN ria$i.way2 ELSE rib$i.way1 END) AS wayb$i,
";
  }
}
$query_affluents .= "0
FROM rivers_tributary";
for ($i = 1; $i < $max_affluent; $i++) {
  $query_affluents .= "
LEFT JOIN relations rt$i ON rivers[$i][2] = rt$i.id
LEFT JOIN ways wt$i ON rivers[$i][2] = wt$i.id
";
  if ($i > 1) {
    $i2 = $i - 1;
    $query_affluents .= "
LEFT JOIN rivers_intersections ria$i ON ria$i.id1 = rivers[$i][2] AND ria$i.id2 = rivers[$i2][2]
LEFT JOIN rivers_intersections rib$i ON rib$i.id2 = rivers[$i][2] AND rib$i.id1 = rivers[$i2][2]
";
  }
}
$query_affluents .= "ORDER BY name1, id1, ";
for ($i = 2; $i < $max_affluent; $i++) {
  $query_affluents .= "order$i DESC, ";
}
$query_affluents .= "name1";

print "<div style='display: none'>
$query_affluents
</div>\n";

$prev_river = array();

$res_affluents=pg_query($query_affluents);

print "<table class='liste'>\n";
print "<tr>\n";
print "  <th>Rivière</th>\n";
print "  <th>osm id</th>\n";
print "  <th>sandre</th>\n";
print "  <th>waterway</th>\n";
print "  <th>Intersection (way id)</th>\n";
print "</tr>\n";

while($affluent=pg_fetch_object($res_affluents)) {
  print "<tr>\n";
  print "  <td>\n";
  for ($i = 1; $i < $max_affluent; $i ++) {
    $osm_id = $affluent->{"id$i"};
    if ($osm_id) {
      if (!isset($prev_river[$i]) || $prev_river[$i] != $osm_id) {
        if ($i == 1) {
          print "&nbsp;\n";
          print "  </td>\n";
          print "  <td>&nbsp;</td>\n";
          print "  <td>&nbsp;</td>\n";
          print "  <td>&nbsp;</td>\n";
          print "</tr>\n";
          print "<tr class='origine'>\n";
          print "  <td>\n";
        }
        $prev_river[$i] = $osm_id;
        $name = $affluent->{"name$i"};
        if (is_null($name)) {
          $name = "-";
        }
        print $name;
        print "  </td>\n";
        print "  <td>\n";
        if ($affluent->{"type$i"} == ord('R')) {
          $short_type = "r";
          $type = "relation";
        } else {
          $short_type = "w";
          $type = "way";
        }
        $osm_id_lien = osm_link($type, $osm_id);
        print "$osm_id_lien $short_type";
        print "  </td>\n";
        print "  <td>\n";
        $sandre = $affluent->{"sandre$i"};
        print sandre_link($sandre);
        print "  </td>\n";
        print "  <td>\n";
        $waterway = $affluent->{"waterway$i"};
        print "$waterway";
        print "  </td>\n";
        print "  <td>\n";
        if (isset($affluent->{"waya$i"})) {
          $osm_id_lien_a = osm_link("way", $affluent->{"waya$i"});
          $osm_id_lien_b = osm_link("way", $affluent->{"wayb$i"});
          print "$osm_id_lien_a $osm_id_lien_b";
        } else if ($i > 1) {
          if ($affluent->{"type$i"} == ord('R')) {
            print "pas d'intersection trouvée";

          } else {
            $rela = $prev_river[$i-1];
            $wayb = $osm_id;
            $query_croisement = "
SELECT wg.id AS waya, wg2.id AS wayb
FROM relation_members rm
JOIN ways wg ON wg.id = rm.member_id
JOIN ways wg2 ON ST_Intersects(wg.linestring, wg2.linestring)
WHERE rm.member_type = 'W' AND rm.member_role != 'tributary' AND
      rm.relation_id = $rela AND wg2.id = $wayb AND
      wg.nodes[array_length(wg.nodes, 1)] != wg2.nodes[array_length(wg2.nodes, 1)]
";
            $res_croisement=pg_query($query_croisement);
            if($croisement=pg_fetch_object($res_croisement)) {
              $osm_id_lien_a = osm_link("way", $croisement->{"waya"});
              $osm_id_lien_b = osm_link("way", $croisement->{"wayb"});
              print "$osm_id_lien_a $osm_id_lien_b";
            } else {
              print "pas d'intersection trouvée";
            }
            pg_free_result($res_croisement);
          }
        }

        if ($i == 1) {
          $i = 0;  // reprends à 0 pour afficher le premier affluent correctement
                   // (nécessaire parce que la bdd ne retourne que des chemins avec
                   // au moins 2 rivières)
          print "  </td>\n";
          print "</tr>\n";
          print "<tr>\n";
          print "  <td>\n";
        }
      } else {
        print "&nbsp;&nbsp;&nbsp;&nbsp;";
      }
    }
  }
  print "  </td>\n";
  print "</tr>\n";
}
pg_free_result($res_affluents);
print "</table>\n";

print "<h2>Connexions entre rivières sans affluent spécifié dans une relation</h2>\n";

$query_affluents = "
SELECT id1, name1, way1, id2, name2, way2,
       rt1.tags->'waterway' AS waterway1, rt2.tags->'waterway' as waterway2
FROM rivers_intersections
LEFT JOIN rivers_tributary ON id1 = ANY(rivers) AND id2 = ANY(rivers)
LEFT JOIN relations rt1 ON rt1.id = id1 AND rt1.tags ? 'waterway'
LEFT JOIN relations rt2 ON rt2.id = id2 AND rt2.tags ? 'waterway'
WHERE depth IS NULL AND rt1.tags->'waterway' != 'canal' AND rt2.tags->'waterway' != 'canal' AND
                        rt1.tags->'waterway' != 'riverbank' AND rt2.tags->'waterway' != 'riverbank'
ORDER BY name1, name2;
";

$res_affluents=pg_query($query_affluents);

print "<table border='1'>
<tr>
  <th colspan=4>Rivière 1</th>
  <th colspan=4>Rivière 2</th>
<tr>
  <th>Nom</th>
  <th>relation</th>
  <th>way</th>
  <th>waterway</th>
  <th>Nom</th>
  <th>relation</th>
  <th>way</th>
  <th>waterway</th>
</tr>
";

while($affluent=pg_fetch_object($res_affluents)) {
  print "<tr>\n";
  print "  <td>$affluent->name1</td>\n";
  $osm_id_lien = osm_link("relation", $affluent->id1);
  print "  <td>$osm_id_lien</td>\n";
  $osm_id_lien = osm_link("way", $affluent->way1);
  print "  <td>$osm_id_lien</td>\n";
  print "  <td>$affluent->waterway1</td>\n";

  $osm_id = $affluent->id2;
  print "  <td>$affluent->name2</td>\n";
  $osm_id_lien = osm_link("relation", $affluent->id2);
  print "  <td>$osm_id_lien</td>\n";
  $osm_id_lien = osm_link("way", $affluent->way2);
  print "  <td>$osm_id_lien</td>\n";
  print "  <td>$affluent->waterway2</td>\n";

  print "</tr>\n";
}
pg_free_result($res_affluents);
print "</table>";


print "<h2>Rivières qui ne sont pas affluents d'une autre rivière</h2>\n";

$query_affluents = "
SELECT rt.id AS id, rt.tags->'name' AS name,
       rt.tags->'ref:sandre' AS sandre, rt.tags->'waterway' AS waterway
FROM relations rt
LEFT JOIN rivers_tributary ON rt.id = ANY(rivers[2:100]) 
LEFT JOIN rivers_coastline_intersections inter ON rt.id = inter.id1
WHERE rt.tags->'type' = 'waterway' AND depth IS NULL AND
      NOT rt.tags->'waterway' = 'canal' AND NOT rt.tags->'waterway' = 'riverbank' AND
      inter.way2 IS NULL
ORDER BY rt.tags->'name';
";

$res_affluents=pg_query($query_affluents);

print "<table border='1'>
<tr>
  <th>Nom</th>
  <th>OSM</th>
  <th>Sandre</th>
  <th>waterway</th>
</tr>
";

while($affluent=pg_fetch_object($res_affluents)) {
  $osm_id = $affluent->id;
  $sandre = $affluent->sandre;
  
  print "<tr>\n";
  print "  <td>$affluent->name</td>\n";
  $osm_id_lien="<a href='http://www.openstreetmap.org/browse/relation/$osm_id'>$osm_id</a>&nbsp;<a href='http://localhost:8111/import?url=http://api.openstreetmap.org/api/0.6/relation/$osm_id/full' target='suivi-josm'>josm</a>";

  print "  <td>$osm_id_lien</td>\n";
  print "  <td>";
  print sandre_link($sandre);
  print "</td>\n";
  print "  <td>$affluent->waterway</td>\n";
  print "</tr>\n";
}
pg_free_result($res_affluents);
print "</table>";

print "</body>";
print "</html>";

