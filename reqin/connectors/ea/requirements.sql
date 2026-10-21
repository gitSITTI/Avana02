-- Sparx Enterprise Architect repository (a DBMS repository): one row per Requirement element.
-- Used with the vendor-agnostic `sql` adapter:  --opt query_file=connectors/ea/requirements.sql --opt id_column=guid --opt parent_column=parent_guid
--
-- THE COLUMN NAMES BELOW ARE FROM MEMORY OF THE REPOSITORY SCHEMA, NOT CHECKED AGAINST A REAL REPOSITORY. Vendor documentation confirms that a DBMS
-- repository has the same logical structure as the file one and that the element class maps to the table t_object; it does not list the columns.
-- Before trusting anything, run this on your repository (it reads nothing):
--     SELECT * FROM t_object WHERE 1 = 0     and     SELECT * FROM t_connector WHERE 1 = 0     and     SELECT * FROM t_package WHERE 1 = 0
-- and change a name here if yours differs. `reqin discover` then lists the columns this query returned and warns if id_column or parent_column is not one.
--
-- Plain joins and COALESCE/NULLIF only, so it runs on SQL Server, MySQL, PostgreSQL and Oracle alike. No ORDER BY on purpose: order is not meaning.
SELECT
    o.ea_guid                 AS guid,            -- stable across repositories and XMI exports: the record's native id
    o.Object_ID               AS object_id,       -- the repository's own number
    o.Name                    AS name,
    o.Alias                   AS alias,           -- many projects keep the human requirement id here; others keep it in the name: see profiles/ea_sql.yaml
    o.Note                    AS note,            -- the statement text (EA calls it Notes)
    o.Stereotype              AS stereotype,
    o.Status                  AS status,
    o.Phase                   AS phase,
    o.Version                 AS version,
    o.Author                  AS author,
    o.ModifiedDate            AS modified,
    p.Name                    AS package,         -- the package it sits in (its immediate package only, not the whole path)
    par.ea_guid               AS parent_guid      -- the element it is nested under; empty for a top-level one (ParentID is 0 there, so no row joins)
FROM t_object o
LEFT JOIN t_package p   ON p.Package_ID = o.Package_ID
LEFT JOIN t_object  par ON par.Object_ID = o.ParentID AND o.ParentID <> 0
WHERE o.Object_Type = 'Requirement'
