# Sparx Enterprise Architect: a query pack for the `sql` adapter

Enterprise Architect has no HTTP API. Its documented routes are the Windows automation object model (COM, which can also change the model), CSV export of
elements, XMI, and the repository itself. When the repository is a database server (SQL Server, MySQL, PostgreSQL or Oracle, which Sparx documents as sharing the
logical structure of the file repository), the safest read is a `SELECT` through a read-only login. This pack is that `SELECT`, for the vendor-agnostic `sql`
adapter. There is no EA-specific code in `reqin`.

| File | What it is |
|---|---|
| `requirements.sql` | one row per Requirement element: GUID, number, name, alias, notes, stereotype, status, phase, version, author, modified date, package, parent GUID |
| `links.sql` | one row per connector with a Requirement at either end: source and target GUID, kind (stereotype, else connector type), connector GUID |
| `../../profiles/ea_sql.yaml` | the profile: id from the alias, statement from the notes (markup removed) |

## Run it

```
reqin discover 'postgresql+psycopg://reader@host/ea' \
    --opt query_file=connectors/ea/requirements.sql --opt links_query_file=connectors/ea/links.sql \
    --opt id_column=guid --opt parent_column=parent_guid
reqin sample   ...the same source and options...     # the first rows exactly as the database returned them
reqin import   ...the same source and options... --profile profiles/ea_sql.yaml --out-dir out/ea
```

`reqin discover` lists the columns the query returned and prints a WARNING if `id_column` or `parent_column` is not one of them. Read it before trusting anything.

## What is NOT proven (read this first)

- **The table and column names are from memory.** Vendor documentation confirms the DBMS repository shares the file repository's structure and that the element
  class maps to `t_object`. It does not list the columns, and `t_connector`'s names (`Start_Object_ID`, `End_Object_ID`) are recalled, not read. Before the first
  run, ask your database for the real columns (`SELECT * FROM t_object WHERE 1 = 0`, the same for `t_connector` and `t_package`) and change a name in the `.sql`
  files if yours differs. The tests run these files against a small made-up SQLite database built to match the recalled names, so they prove the files and the
  adapter agree with each other and nothing more.
- **Nobody has run this against a real Enterprise Architect repository.**
- **Link direction is a convention.** The pack reads the connector's start end as the source and the end as the target. For satisfy, refine, derive, verify and
  trace connectors drawn the usual way (design to requirement) that is the direction reqin uses. A project that draws them the other way round gets reversed
  links. `reqin sample` shows a few; look.
- **Where the requirement id lives is a project convention.** The profile reads it from the alias. If yours is in the name, change one line in the profile.
- **File repositories are not covered.** The `.eap` and `.feap` file repositories need their own database drivers, which `reqin` does not bundle. Copy the repository
  into one of the supported database servers with whatever route Sparx documents (not checked here), or run the same `SELECT`s with your own driver and export
  CSV for the `tabular` adapter. A repository file in SQLite format, if your version has one, may work as `sqlite:///path` if its tables are named the same
  (not checked).
- **Package is the immediate package only**, not the whole path. A recursive query would give the path, but it differs between databases; add one if you need it.
- Tagged values (`t_objectproperties`) are not read. Add a join if the attributes you need are kept there.

## Safety

Use a database login that can only `SELECT` from `t_object`, `t_connector` and `t_package`. The adapter refuses anything but one `SELECT` or `WITH` statement
(comments are removed first, so a comment cannot hide a second statement), and opens SQLite with `query_only` on. That is defence in depth: the database
permission is the real control.
