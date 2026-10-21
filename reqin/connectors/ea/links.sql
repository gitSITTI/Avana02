-- Sparx Enterprise Architect repository: one row per connector that has a Requirement at either end.
-- Used with:  --opt links_query_file=connectors/ea/links.sql      (the same caveat as requirements.sql: column names are from memory, check them.)
--
-- Direction. The vendor's automation documentation names the two ends ClientID (source) and SupplierID (target). In the tables they are, from memory,
-- Start_Object_ID and End_Object_ID. For the usual satisfy / refine / derive / verify / trace connectors the CLIENT is the design, derived or test
-- element and the SUPPLIER is the requirement it points at, which is the direction reqin uses (source = the one that satisfies, target = the requirement).
-- A project that draws them the other way round gets the links reversed: look at `reqin sample` before relying on the direction.
--
-- Both ends are written as the element's ea_guid, which is what requirements.sql gives as the record id. An end that is not a Requirement (a block, a
-- test case) is not in the import: it stays in the link under its GUID and reqin counts it as "points outside this import".
SELECT
    s.ea_guid                                              AS source,
    t.ea_guid                                              AS target,
    COALESCE(NULLIF(c.Stereotype, ''), c.Connector_Type)   AS kind,      -- the stereotype (satisfy, verify ...) when there is one, else EA's connector type
    c.ea_guid                                              AS ref        -- the connector's own GUID: where to look it up in EA
FROM t_connector c
JOIN t_object s ON s.Object_ID = c.Start_Object_ID
JOIN t_object t ON t.Object_ID = c.End_Object_ID
WHERE s.Object_Type = 'Requirement' OR t.Object_Type = 'Requirement'
