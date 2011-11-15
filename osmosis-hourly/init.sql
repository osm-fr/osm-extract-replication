CREATE OR REPLACE FUNCTION clean_bdd_ways_simple(zone text, l integer, opt integer)
RETURNS integer AS
$BODY$
DECLARE
  bbox geometry;
  num integer;
BEGIN
  SET ENABLE_SEQSCAN TO false;
  SELECT INTO bbox geom FROM bounding_box WHERE name = zone;

  DROP TABLE IF EXISTS ways_to_remove;

  IF opt = 0 THEN
    RAISE NOTICE 'opt 0';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    WHERE ST_Disjoint(bbox, ways.linestring)
    LIMIT l;

  ELSIF opt = 1 THEN
    RAISE NOTICE 'opt 1';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    WHERE ways.linestring IS NULL
    LIMIT l;

  ELSIF opt = 2 THEN
    RAISE NOTICE 'opt 2';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    WHERE st_numpoints(ways.linestring) < 2
    LIMIT l;

  ELSIF opt = 3 THEN
    RAISE NOTICE 'opt 3';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    where ways.bbox >> (select geom from bounding_box where name = 'france_metropole') AND
          ST_Disjoint(bbox, ways.linestring)
    LIMIT l;

  ELSIF opt = 4 THEN
    RAISE NOTICE 'opt 4';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    where ways.bbox << (select geom from bounding_box where name = 'france_metropole') AND
          ST_Disjoint(bbox, ways.linestring)
    LIMIT l;

  ELSIF opt = 10 THEN
    RAISE NOTICE 'opt 10';
    CREATE TABLE
    ways_to_remove
    AS
    SELECT id
    FROM ways
    where (ways.bbox << (select geom from bounding_box where name = 'france_metropole') OR
           ways.bbox >> (select geom from bounding_box where name = 'france_metropole') OR
           ways.bbox <<| (select geom from bounding_box where name = 'france_metropole') OR
           ways.bbox |>> (select geom from bounding_box where name = 'france_metropole')) AND
          ST_Disjoint(bbox, ways.linestring)
    LIMIT l;

  ELSE
    RAISE EXCEPTION 'unknown opt %', opt;
  END IF;

  CREATE INDEX idx_way_to_remove_id ON ways_to_remove USING btree(id); 

  RAISE NOTICE 'ways_to_remove created';

  DELETE
  FROM ways
  USING ways_to_remove
  WHERE ways_to_remove.id = ways.id;
  
  DELETE
  FROM way_nodes
  USING ways_to_remove
  WHERE ways_to_remove.id = way_nodes.way_id;

   -- relations
  DELETE
  FROM relation_members
  USING ways_to_remove
  WHERE relation_members.member_type = 'W' AND relation_members.member_id = ways_to_remove.id;
 
  SELECT INTO num count(*) FROM ways_to_remove;
  RETURN num;
END
$BODY$
LANGUAGE 'plpgsql' ;


CREATE OR REPLACE FUNCTION clean_bdd_ways(zone text, l integer) RETURNS integer AS
$BODY$
DECLARE
  bbox geometry;
  rel_removed integer;
  rel_removed2 integer;
BEGIN
  SET ENABLE_SEQSCAN TO false;
  SELECT INTO bbox geom FROM bounding_box WHERE name = zone;

  DROP TABLE IF EXISTS ways_to_remove;
  CREATE TABLE
  ways_to_remove
  AS
  SELECT id
  FROM ways
  where (ways.bbox << bbox OR
         ways.bbox >> bbox OR
         ways.bbox <<| bbox OR
         ways.bbox |>> bbox) AND
        ST_Disjoint(bbox, ways.linestring)
  LIMIT l;
  
  DELETE
  FROM ways
  USING ways_to_remove
  WHERE ways_to_remove.id = ways.id;
  
  DELETE
  FROM way_nodes
  USING ways_to_remove
  WHERE ways_to_remove.id = way_nodes.way_id;
  
  
  DROP TABLE IF EXISTS ways_to_remove2;
  CREATE TABLE
  ways_to_remove2
  AS
  SELECT DISTINCT ON (ways.id) ways.id
  FROM ways
  LEFT JOIN way_nodes ON ways.id = way_nodes.way_id
  LEFT JOIN nodes ON nodes.id = way_nodes.node_id
  WHERE nodes.id IS NULL
  LIMIT l;
  
  DELETE
  FROM ways
  USING ways_to_remove2
  WHERE ways_to_remove2.id = ways.id;
  
  DELETE
  FROM way_nodes
  USING ways_to_remove2
  WHERE ways_to_remove2.id = way_nodes.way_id;
  
  -- relations
  DELETE
  FROM relation_members
  USING ways_to_remove
  WHERE relation_members.member_type = 'W' AND relation_members.member_id = ways_to_remove.id;
  
  DELETE
  FROM relation_members
  USING ways_to_remove2
  WHERE relation_members.member_type = 'W' AND relation_members.member_id = ways_to_remove2.id;
  
  rel_removed := 1;
  rel_removed2 := 1;
  WHILE rel_removed > 0 OR rel_removed2 > 0 LOOP
    RAISE NOTICE 'cleaning relation';
  
    DROP TABLE IF EXISTS relations_to_remove;
    CREATE TABLE
    relations_to_remove
    AS
    SELECT id
    FROM relations
    LEFT JOIN relation_members rm ON rm.relation_id = id
    WHERE rm.relation_id IS NULL;

    DELETE
    FROM relations
    USING relations_to_remove
    WHERE relations_to_remove.id = relations.id;
  
    -- remove relations without valid nodes or ways or relations
    DROP TABLE IF EXISTS relation_members_clean;
    CREATE TABLE
    relation_members_clean
    AS
    SELECT relation_members.relation_id, relation_members.member_id, relation_members.member_type
    FROM relation_members
    LEFT JOIN nodes ON relation_members.member_type = 'N' AND relation_members.member_id = nodes.id
    LEFT JOIN ways ON relation_members.member_type = 'W' AND relation_members.member_id = ways.id
    LEFT JOIN relations ON relation_members.member_type = 'R' AND relation_members.member_id = relations.id
    WHERE nodes.id IS NULL AND ways.id IS NULL AND relations.id IS NULL;
  
    DELETE
    FROM relation_members
    USING relation_members_clean
    WHERE relation_members_clean.relation_id = relation_members.relation_id AND
          relation_members_clean.member_id   = relation_members.member_id AND
          relation_members_clean.member_type = relation_members.member_type;
  
    SELECT INTO rel_removed  count(*) FROM relations_to_remove LIMIT 1;
    SELECT INTO rel_removed2 count(*) FROM relation_members_clean LIMIT 1;
  END LOOP;
  RETURN 1;
END
$BODY$
LANGUAGE 'plpgsql' ;


CREATE OR REPLACE FUNCTION clean_bdd_nodes(zone text, l integer) RETURNS integer AS
$BODY$
DECLARE
  bbox geometry;
  bbox_metro geometry;
  num integer;
BEGIN

  SET ENABLE_SEQSCAN TO false;
  SELECT INTO bbox geom FROM bounding_box WHERE name = zone;
  SELECT INTO bbox_metro geom FROM bounding_box WHERE name = 'france_metropole';

  -- nodes
  DROP TABLE IF EXISTS nodes_to_remove;
  CREATE TABLE
  nodes_to_remove
  AS
  SELECT id
  FROM nodes
  WHERE (nodes.geom << bbox_metro OR
         nodes.geom >> bbox_metro OR
         nodes.geom <<| bbox_metro OR
         nodes.geom |>> bbox_metro) AND
        ST_Disjoint(bbox, nodes.geom)
  LIMIT l;
  
  CREATE INDEX idx_nodes_to_remove_id ON nodes_to_remove USING btree(id); 

  RAISE NOTICE 'nodes_to_remove created';

  DELETE
  FROM nodes
  USING nodes_to_remove
  WHERE nodes.id = nodes_to_remove.id;
  
  -- ways
  DELETE
  FROM way_nodes
  USING nodes_to_remove
  WHERE node_id = nodes_to_remove.id;

  -- relations
  DELETE
  FROM relation_members
  USING nodes_to_remove
  WHERE relation_members.member_type = 'N' AND relation_members.member_id = nodes_to_remove.id;
  
  SELECT INTO num count(*) FROM nodes_to_remove;
  RETURN num;
END
$BODY$
LANGUAGE 'plpgsql' ;

CREATE OR REPLACE FUNCTION way_geom(way_id bigint) RETURNS geometry AS
$BODY$
  SELECT linestring
  FROM ways
  WHERE id = $1;
$BODY$
LANGUAGE 'SQL' ;

