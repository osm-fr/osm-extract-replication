CREATE OR REPLACE FUNCTION delete_way(deleted_way_id bigint) RETURNS void AS $$
BEGIN
  DELETE FROM relation_members WHERE member_type = 'W' AND member_id = deleted_way_id;
  DELETE FROM ways WHERE id = deleted_way_id;
  DELETE FROM nodes USING way_nodes WHERE nodes.id = way_nodes.node_id AND
                                          way_nodes.way_id = deleted_way_id;
  DELETE FROM actions USING way_nodes WHERE actions.id = way_nodes.node_id AND
                                            actions.data_type = 'N' AND
                                            way_nodes.way_id = deleted_way_id;
  DELETE FROM way_nodes WHERE way_nodes.way_id = deleted_way_id;

  DELETE from actions WHERE data_type = 'W' AND id = deleted_way_id AND action != 'D';
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION osmosisUpdate_way() RETURNS void AS $$
DECLARE
  to_keep geometry;
  r RECORD;
BEGIN
  SET enable_seqscan TO FALSE;

  SELECT INTO to_keep geom
  FROM bounding_box
  WHERE bounding_box.name = 'all';

  FOR r IN SELECT actions.id AS id, ways.linestring
              FROM actions
              JOIN ways ON ways.id = actions.id
              WHERE data_type = 'W'
  LOOP
    BEGIN
      IF r.linestring IS NULL
      THEN
        PERFORM delete_way(r.id);

      ELSIF st_npoints(r.linestring) = 1 AND
            ST_Disjoint(ST_StartPoint(r.linestring), to_keep)
      THEN
        PERFORM delete_way(r.id);

      ELSIF st_npoints(r.linestring) > 1 AND
            ST_Disjoint(r.linestring, to_keep)
      THEN
        PERFORM delete_way(r.id);

      ELSE
        DELETE from actions WHERE data_type = 'W' AND id = r.id AND action != 'D';
      END IF;
    EXCEPTION
      WHEN query_canceled THEN
        RAISE NOTICE 'canceled';
        RETURN;
    END;

  END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION delete_node(deleted_node_id bigint) RETURNS void AS $$
BEGIN
  DELETE FROM relation_members WHERE member_type = 'N' AND member_id = deleted_node_id;
  DELETE FROM nodes WHERE id = deleted_node_id;

  DELETE from actions WHERE data_type = 'N' AND id = deleted_node_id AND action != 'D';
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION osmosisUpdate_node() RETURNS void AS $$
DECLARE
  line RECORD;
BEGIN
  SET enable_seqscan TO FALSE;
--  FOR line IN SELECT actions.id AS id
--              FROM actions
--              INNER JOIN relation_members ON  member_type = 'N' AND member_id = actions.id
--              LEFT JOIN nodes ON nodes.id = actions.id
--              WHERE data_type = 'N' AND
--                    nodes.id IS NULL
--  LOOP
--    RAISE NOTICE 'node1 - %', line.id;
--    PERFORM delete_node(line.id);
--  END LOOP;

  FOR line IN SELECT actions.id AS id
              FROM actions
              JOIN nodes ON nodes.id = actions.id
              JOIN bounding_box ON bounding_box.name = 'all' AND
                                   ST_Disjoint(nodes.geom, bounding_box.geom)
              LEFT JOIN way_nodes ON way_nodes.node_id = nodes.id
              WHERE data_type = 'N' AND
                    way_nodes.way_id IS NULL
  LOOP
--    RAISE NOTICE 'node2 - %', line.id;
    PERFORM delete_node(line.id);
  END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION osmosisUpdate() RETURNS void AS $$
DECLARE
BEGIN
  DROP TABLE IF EXISTS actions_bak;
  CREATE TABLE actions_bak AS SELECT * FROM actions;

END;
$$ LANGUAGE plpgsql;



-- exécution après osmosis

--insert into actions select * from actions_bak;

--SELECT * FROM osmosisUpdate_way();
--SELECT * FROM osmosisUpdate_node();
