#!/usr/bin/env python3
"""
Compare the SCHEMA of your local PostgreSQL database with Neon, show the
differences, and (only if you approve) apply the missing parts to Neon.

  * Schema only. No table data is read or copied (one exception: it asks
    "does this table have any rows?" before adding a NOT NULL column).
  * Local is the source of truth. Neon is only ever changed by ADDING or
    MODIFYING objects. Anything that exists only on Neon is reported and left
    alone. Nothing is ever dropped (except an old constraint/index/trigger
    that is being replaced by the local definition, and only if you choose
    the "changes" option).
  * Changes that could lose data (column type changes, SET NOT NULL,
    enum label changes, primary-key changes) are listed as MANUAL and are
    never applied by this script.
  * Both databases are opened READ-ONLY for the comparison.
  * Passwords are never printed or saved. Neon's connection string is read
    from the NEON_DATABASE_URL environment variable or typed in hidden.

Usage (from the project folder, with the project's virtual environment):
    python sync_schema_to_neon.py              # compare, then ask
    python sync_schema_to_neon.py --dry-run    # compare only, never ask
"""
import argparse
import datetime
import getpass
import os
import re
import sys

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

# order in which statements are applied
ORD = {
    "extension": 10, "enum": 20, "sequence": 30, "table": 40, "column": 50,
    "column_change": 55, "constraint": 60, "fk": 62, "constraint_change": 64,
    "index": 70, "function": 80, "view": 85, "trigger": 90,
}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def qi(name):
    return '"' + str(name).replace('"', '""') + '"'


def qt(schema, name):
    return qi(schema) + "." + qi(name)


def norm(text):
    """Make definitions comparable: no schema prefix, one-space whitespace."""
    if text is None:
        return None
    s = re.sub(r'"?public"?\.', "", str(text))
    return re.sub(r"\s+", " ", s).strip().rstrip(";")


CAST_RE = re.compile(
    r"::\s*(?:character varying|varchar|text|integer|int4|bigint|smallint|boolean|numeric|regclass|"
    r"date|timestamp(?: with(?:out)? time zone)?)(?:\(\d+(?:,\d+)?\))?(?:\[\])?")


def loose(text):
    """Second-stage comparison that ignores how different PostgreSQL versions print
    the same definition: type casts, brackets and spacing. Values, column names and
    operators are still compared."""
    if text is None:
        return None
    s = CAST_RE.sub("", norm(text).lower())
    return re.sub(r"[()\s]+", "", s)


# ----------------------------------------------------------------------------
# reading a database (SELECT only)
# ----------------------------------------------------------------------------
def take_snapshot(conn, schema, include_alembic=False):
    cur = conn.cursor()

    def q(sql, params=()):
        cur.execute(sql, params)
        return cur.fetchall()

    snap = {
        "extensions": {}, "enums": {}, "sequences": {}, "tables": {},
        "indexes": {}, "functions": {}, "views": {}, "triggers": {},
    }

    for name, version in q("SELECT extname, extversion FROM pg_extension"):
        snap["extensions"][name] = version

    for typname, labels in q(
        """SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder)
           FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
           JOIN pg_namespace n ON n.oid = t.typnamespace
           WHERE n.nspname = %s GROUP BY t.typname""", (schema,)):
        snap["enums"][typname] = list(labels)

    for row in q(
        """SELECT s.sequencename, s.data_type::text, s.start_value, s.min_value,
                  s.max_value, s.increment_by, s.cycle, s.cache_size
           FROM pg_sequences s
           WHERE s.schemaname = %s AND NOT EXISTS (
               SELECT 1 FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               JOIN pg_depend d ON d.objid = c.oid
               WHERE c.relname = s.sequencename AND n.nspname = s.schemaname
                 AND d.deptype = 'i')""", (schema,)):
        snap["sequences"][row[0]] = {
            "type": row[1], "start": row[2], "min": row[3], "max": row[4],
            "inc": row[5], "cycle": bool(row[6]), "cache": row[7],
        }

    for (relname,) in q(
        """SELECT c.relname FROM pg_class c
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = %s AND c.relkind IN ('r','p')
             AND NOT c.relispartition ORDER BY c.relname""", (schema,)):
        if relname == "alembic_version" and not include_alembic:
            continue
        snap["tables"][relname] = {"columns": [], "constraints": {}}

    for (rel, attname, typ, notnull, default, identity, generated) in q(
        """SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod),
                  a.attnotnull, pg_get_expr(d.adbin, d.adrelid),
                  a.attidentity, a.attgenerated
           FROM pg_attribute a
           JOIN pg_class c ON c.oid = a.attrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
           LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
           WHERE n.nspname = %s AND c.relkind IN ('r','p')
             AND a.attnum > 0 AND NOT a.attisdropped
           ORDER BY c.relname, a.attnum""", (schema,)):
        if rel in snap["tables"]:
            snap["tables"][rel]["columns"].append({
                "name": attname, "type": typ, "notnull": bool(notnull),
                "default": default, "identity": (identity or "").strip(),
                "generated": (generated or "").strip(),
            })

    for (rel, conname, contype, condef) in q(
        """SELECT c.relname, con.conname, con.contype, pg_get_constraintdef(con.oid)
           FROM pg_constraint con
           JOIN pg_class c ON c.oid = con.conrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = %s AND con.contype IN ('p','u','c','f')
             AND c.relkind IN ('r','p')""", (schema,)):
        if rel in snap["tables"]:
            snap["tables"][rel]["constraints"][conname] = {"type": contype, "def": condef}

    for (iname, tname, idef) in q(
        """SELECT i.indexname, i.tablename, i.indexdef FROM pg_indexes i
           WHERE i.schemaname = %s AND NOT EXISTS (
               SELECT 1 FROM pg_constraint con
               JOIN pg_class ic ON ic.oid = con.conindid
               JOIN pg_namespace n2 ON n2.oid = ic.relnamespace
               WHERE ic.relname = i.indexname AND n2.nspname = i.schemaname)""",
        (schema,)):
        if tname in snap["tables"]:
            snap["indexes"][iname] = {"table": tname, "def": idef}

    for (fname, args, fdef) in q(
        """SELECT p.proname, pg_get_function_identity_arguments(p.oid),
                  pg_get_functiondef(p.oid)
           FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = %s AND p.prokind IN ('f','p')
             AND NOT EXISTS (SELECT 1 FROM pg_depend d
                             WHERE d.objid = p.oid AND d.deptype = 'e')""", (schema,)):
        snap["functions"]["%s(%s)" % (fname, args)] = fdef

    for (vname, vdef) in q(
        """SELECT c.relname, pg_get_viewdef(c.oid, true) FROM pg_class c
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = %s AND c.relkind = 'v'""", (schema,)):
        snap["views"][vname] = vdef

    for (tgname, rel, tgdef) in q(
        """SELECT t.tgname, c.relname, pg_get_triggerdef(t.oid)
           FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = %s AND NOT t.tgisinternal""", (schema,)):
        snap["triggers"][rel + "." + tgname] = {"table": rel, "name": tgname, "def": tgdef}

    cur.close()
    return snap


# ----------------------------------------------------------------------------
# turning differences into SQL
# ----------------------------------------------------------------------------
def column_ddl(c, force_nullable=False):
    parts = [qi(c["name"]), c["type"]]
    if c["generated"] == "s":
        parts.append("GENERATED ALWAYS AS (%s) STORED" % c["default"])
    elif c["identity"] == "a":
        parts.append("GENERATED ALWAYS AS IDENTITY")
    elif c["identity"] == "d":
        parts.append("GENERATED BY DEFAULT AS IDENTITY")
    elif c["default"] is not None:
        parts.append("DEFAULT %s" % c["default"])
    if c["notnull"] and not force_nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def sequence_ddl(schema, name, s):
    return ("CREATE SEQUENCE %s AS %s INCREMENT BY %s MINVALUE %s MAXVALUE %s "
            "START WITH %s CACHE %s %s" % (
                qt(schema, name), s["type"], s["inc"], s["min"], s["max"],
                s["start"], s["cache"], "CYCLE" if s["cycle"] else "NO CYCLE"))


def create_table_ddl(schema, name, t):
    lines = [column_ddl(c) for c in t["columns"]]
    for cname, con in t["constraints"].items():
        if con["type"] in ("p", "u", "c"):
            lines.append("CONSTRAINT %s %s" % (qi(cname), con["def"]))
    return "CREATE TABLE %s (\n  %s\n)" % (qt(schema, name), ",\n  ".join(lines))


def index_if_not_exists(idef):
    return re.sub(r"^CREATE (UNIQUE )?INDEX ", r"CREATE \1INDEX IF NOT EXISTS ", idef, count=1)


def build_plan(L, R, schema, table_has_rows):
    """L = local snapshot (source of truth), R = Neon snapshot.
    Returns a list of items: {group, kind, title, sql: [..]}.
    group: 'add' (safe additions), 'change' (modifies existing),
           'manual' (never applied), 'extra' (only on Neon, left alone)."""
    items = []

    def add(group, kind, title, sql=None):
        items.append({"group": group, "kind": kind, "title": title, "sql": sql or []})

    for name in L["extensions"]:
        if name not in R["extensions"]:
            add("add", "extension", "extension %s" % name,
                ["CREATE EXTENSION IF NOT EXISTS %s" % qi(name)])

    for name, labels in L["enums"].items():
        if name not in R["enums"]:
            lit = ", ".join("'" + l.replace("'", "''") + "'" for l in labels)
            add("add", "enum", "enum type %s" % name,
                ["CREATE TYPE %s AS ENUM (%s)" % (qt(schema, name), lit)])
        else:
            missing = [l for l in labels if l not in R["enums"][name]]
            if missing:
                add("manual", "enum", "enum %s is missing labels on Neon: %s "
                    "(run ALTER TYPE ... ADD VALUE yourself, outside a transaction)"
                    % (name, ", ".join(missing)))

    for name, s in L["sequences"].items():
        if name not in R["sequences"]:
            add("add", "sequence", "sequence %s (created at its starting value; "
                "the current counter value is data and is NOT copied)" % name,
                [sequence_ddl(schema, name, s)])
        else:
            r = R["sequences"][name]
            if any(s[k] != r[k] for k in ("type", "inc", "min", "max", "cycle")):
                add("manual", "sequence", "sequence %s has different settings on Neon" % name)

    # ---- tables and columns
    for tname, t in L["tables"].items():
        if tname not in R["tables"]:
            add("add", "table", "table %s (%d columns)" % (tname, len(t["columns"])),
                [create_table_ddl(schema, tname, t)])
            for cname, con in t["constraints"].items():
                if con["type"] == "f":
                    add("add", "fk", "foreign key %s on new table %s" % (cname, tname),
                        ["ALTER TABLE %s ADD CONSTRAINT %s %s" % (qt(schema, tname), qi(cname), con["def"])])
            continue

        rt = R["tables"][tname]
        rcols = {c["name"]: c for c in rt["columns"]}
        for c in t["columns"]:
            if c["name"] not in rcols:
                needs_backfill = (c["notnull"] and c["default"] is None
                                  and not c["identity"] and not c["generated"])
                if needs_backfill and table_has_rows(tname):
                    add("add", "column", "column %s.%s (added as NULLABLE: Neon table has rows)" % (tname, c["name"]),
                        ["ALTER TABLE %s ADD COLUMN %s" % (qt(schema, tname), column_ddl(c, force_nullable=True))])
                    add("manual", "column", "set %s.%s NOT NULL after filling existing rows: "
                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL" % (tname, c["name"], qt(schema, tname), qi(c["name"])))
                else:
                    add("add", "column", "column %s.%s (%s)" % (tname, c["name"], c["type"]),
                        ["ALTER TABLE %s ADD COLUMN %s" % (qt(schema, tname), column_ddl(c))])
                continue
            r = rcols[c["name"]]
            if c["type"] != r["type"]:
                add("manual", "column", "type of %s.%s differs: local %s, Neon %s" % (tname, c["name"], c["type"], r["type"]))
            if c["identity"] != r["identity"] or c["generated"] != r["generated"]:
                add("manual", "column", "identity/generated setting of %s.%s differs" % (tname, c["name"]))
            elif norm(c["default"]) != norm(r["default"]) and loose(c["default"]) == loose(r["default"]):
                add("noise", "column_change", "default of %s.%s prints differently but means the same" % (tname, c["name"]))
            elif norm(c["default"]) != norm(r["default"]):
                if c["default"] is None:
                    sql = "ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT" % (qt(schema, tname), qi(c["name"]))
                else:
                    sql = "ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s" % (qt(schema, tname), qi(c["name"]), c["default"])
                add("change", "column_change", "default of %s.%s: Neon '%s' -> local '%s'" % (tname, c["name"], r["default"], c["default"]), [sql])
            if c["notnull"] != r["notnull"]:
                if r["notnull"] and not c["notnull"]:
                    add("change", "column_change", "%s.%s: allow NULL (local allows it)" % (tname, c["name"]),
                        ["ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL" % (qt(schema, tname), qi(c["name"]))])
                else:
                    add("manual", "column", "%s.%s is NOT NULL locally but nullable on Neon: "
                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL (check existing rows first)"
                        % (tname, c["name"], qt(schema, tname), qi(c["name"])))
        lnames = {c["name"] for c in t["columns"]}
        for c in rt["columns"]:
            if c["name"] not in lnames:
                add("extra", "column", "column %s.%s exists only on Neon" % (tname, c["name"]))

        # ---- constraints
        for cname, con in t["constraints"].items():
            kind = "fk" if con["type"] == "f" else "constraint"
            if cname not in rt["constraints"]:
                add("add", kind, "%s constraint %s on %s" % ({"p": "primary key", "u": "unique", "c": "check", "f": "foreign key"}[con["type"]], cname, tname),
                    ["ALTER TABLE %s ADD CONSTRAINT %s %s" % (qt(schema, tname), qi(cname), con["def"])])
            else:
                rc = rt["constraints"][cname]
                if (norm(con["def"]) != norm(rc["def"]) and con["type"] == rc["type"]
                        and loose(con["def"]) == loose(rc["def"])):
                    add("noise", "constraint", "constraint %s on %s prints differently but means the same" % (cname, tname))
                elif norm(con["def"]) != norm(rc["def"]) or con["type"] != rc["type"]:
                    if con["type"] in ("c", "f") and rc["type"] == con["type"]:
                        add("change", "constraint_change",
                            "constraint %s on %s differs.\n        Neon : %s\n        local: %s" % (cname, tname, rc["def"], con["def"]),
                            ["ALTER TABLE %s DROP CONSTRAINT %s" % (qt(schema, tname), qi(cname)),
                             "ALTER TABLE %s ADD CONSTRAINT %s %s" % (qt(schema, tname), qi(cname), con["def"])])
                    else:
                        add("manual", "constraint", "constraint %s on %s differs (primary key / unique: change by hand)" % (cname, tname))
        for cname in rt["constraints"]:
            if cname not in t["constraints"]:
                add("extra", "constraint", "constraint %s on %s exists only on Neon" % (cname, tname))

    for tname in R["tables"]:
        if tname not in L["tables"]:
            add("extra", "table", "table %s exists only on Neon" % tname)

    # ---- indexes
    for iname, ix in L["indexes"].items():
        if iname not in R["indexes"]:
            add("add", "index", "index %s on %s" % (iname, ix["table"]), [index_if_not_exists(ix["def"])])
        elif norm(ix["def"]) != norm(R["indexes"][iname]["def"]):
            add("change", "index", "index %s differs.\n        Neon : %s\n        local: %s" % (iname, R["indexes"][iname]["def"], ix["def"]),
                ["DROP INDEX %s" % qt(schema, iname), ix["def"]])
    for iname in R["indexes"]:
        if iname not in L["indexes"]:
            add("extra", "index", "index %s exists only on Neon" % iname)

    # ---- functions, views, triggers
    for sig, fdef in L["functions"].items():
        if sig not in R["functions"]:
            add("add", "function", "function %s" % sig, [fdef])
        elif norm(fdef) != norm(R["functions"][sig]):
            add("change", "function", "function %s has a different body on Neon" % sig, [fdef])
    for sig in R["functions"]:
        if sig not in L["functions"]:
            add("extra", "function", "function %s exists only on Neon" % sig)

    for vname, vdef in L["views"].items():
        sql = "CREATE OR REPLACE VIEW %s AS %s" % (qt(schema, vname), vdef.strip().rstrip(";"))
        if vname not in R["views"]:
            add("add", "view", "view %s" % vname, [sql])
        elif norm(vdef) != norm(R["views"][vname]) and loose(vdef) == loose(R["views"][vname]):
            add("noise", "view", "view %s prints differently but means the same" % vname)
        elif norm(vdef) != norm(R["views"][vname]):
            add("change", "view", "view %s differs on Neon" % vname, [sql])
    for vname in R["views"]:
        if vname not in L["views"]:
            add("extra", "view", "view %s exists only on Neon" % vname)

    for key, tg in L["triggers"].items():
        if key not in R["triggers"]:
            add("add", "trigger", "trigger %s on %s" % (tg["name"], tg["table"]), [tg["def"]])
        elif norm(tg["def"]) != norm(R["triggers"][key]["def"]):
            add("change", "trigger", "trigger %s on %s differs" % (tg["name"], tg["table"]),
                ["DROP TRIGGER %s ON %s" % (qi(tg["name"]), qt(schema, tg["table"])), tg["def"]])
    for key, tg in R["triggers"].items():
        if key not in L["triggers"]:
            add("extra", "trigger", "trigger %s on %s exists only on Neon" % (tg["name"], tg["table"]))

    return items


def statements_for(items, groups):
    chosen = [i for i in items if i["group"] in groups and i["sql"]]
    chosen.sort(key=lambda i: ORD.get(i["kind"], 99))
    out = []
    for i in chosen:
        out.extend(i["sql"])
    return out


# ----------------------------------------------------------------------------
# connecting
# ----------------------------------------------------------------------------
def describe(conn):
    p = conn.get_dsn_parameters()
    return "%s:%s / %s" % (p.get("host", "?"), p.get("port", "?"), p.get("dbname", "?"))


def target_key(conn):
    p = conn.get_dsn_parameters()
    return (str(p.get("host", "")).lower(), str(p.get("port", "")), str(p.get("dbname", "")).lower())


def connect_local():
    dsn = os.environ.get("LOCAL_DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    try:
        sys.path.insert(0, os.getcwd())
        from library_api.app.database import get_connection  # the project's own settings
        return get_connection()
    except Exception as exc:
        print("Could not open the local database through the project settings (%s)." % type(exc).__name__)
        dsn = getpass.getpass("Paste the LOCAL connection string (input hidden): ").strip()
        return psycopg2.connect(dsn)


def connect_neon():
    dsn = os.environ.get("NEON_DATABASE_URL") or getpass.getpass(
        "Paste the NEON connection string (input hidden, never saved): ").strip()
    if not dsn:
        sys.exit("No Neon connection string given.")
    return psycopg2.connect(dsn)


def make_readonly(conn):
    try:
        conn.rollback()
        conn.set_session(readonly=True, autocommit=False)
    except Exception:
        pass


def server_version(conn):
    cur = conn.cursor()
    cur.execute("SELECT current_setting('server_version')")
    v = cur.fetchone()[0]
    cur.close()
    return v


# ----------------------------------------------------------------------------
# user interface
# ----------------------------------------------------------------------------
TITLES = {
    "add": "A. MISSING ON NEON - safe additions (nothing existing is touched)",
    "change": "B. DIFFERENT ON NEON - existing objects that would be modified",
    "manual": "C. NEEDS YOUR ATTENTION - never applied by this script",
    "extra": "D. ONLY ON NEON - left alone, never dropped",
    "noise": "E. PRINTED DIFFERENTLY BUT EQUIVALENT - ignored (PostgreSQL version differences)",
}


def print_plan(items):
    for group in ("add", "change", "manual", "extra", "noise"):
        rows = [i for i in items if i["group"] == group]
        if not rows:
            continue
        print("\n" + TITLES[group] + "  [%d]" % len(rows))
        print("-" * 78)
        for n, i in enumerate(rows, 1):
            print("  %2d. %s" % (n, i["title"]))


def write_plan_file(items, path, local_desc, neon_desc):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("-- Schema sync plan generated %s\n-- local: %s\n-- neon : %s\n" % (
            datetime.datetime.now().isoformat(timespec="seconds"), local_desc, neon_desc))
        fh.write("-- Review before running anything by hand.\n\n")
        for group in ("add", "change"):
            fh.write("-- ===== %s =====\n" % TITLES[group])
            for i in sorted([x for x in items if x["group"] == group and x["sql"]], key=lambda x: ORD.get(x["kind"], 99)):
                fh.write("-- %s\n" % i["title"].replace("\n", "\n-- "))
                for s in i["sql"]:
                    fh.write(s.rstrip().rstrip(";") + ";\n")
                fh.write("\n")
        fh.write("-- ===== %s =====\n" % TITLES["manual"])
        for i in [x for x in items if x["group"] == "manual"]:
            fh.write("-- %s\n" % i["title"].replace("\n", "\n-- "))


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def main():
    ap = argparse.ArgumentParser(description="Compare local schema with Neon and optionally sync (schema only).")
    ap.add_argument("--schema", default="public")
    ap.add_argument("--dry-run", action="store_true", help="compare and write the plan file, never ask to apply")
    ap.add_argument("--include-alembic", action="store_true", help="also compare the alembic_version table")
    ap.add_argument("--allow-non-neon", action="store_true", help="allow a target host that is not *.neon.tech")
    args = ap.parse_args()

    if psycopg2 is None:
        sys.exit("psycopg2 is not installed. Run this inside the project's virtual environment.")

    print("Connecting (read-only for the comparison)...")
    local = connect_local()
    neon = connect_neon()
    make_readonly(local)
    make_readonly(neon)

    print("  local: %s  (PostgreSQL %s)" % (describe(local), server_version(local)))
    print("  neon : %s  (PostgreSQL %s)" % (describe(neon), server_version(neon)))
    if target_key(local) == target_key(neon):
        sys.exit("STOP: both connections point to the same database.")
    host = target_key(neon)[0]
    if "neon.tech" not in host and not args.allow_non_neon:
        sys.exit("STOP: the target host '%s' does not look like Neon. Use --allow-non-neon if it is intended." % host)
    lv, nv = server_version(local).split(".")[0], server_version(neon).split(".")[0]
    if lv != nv:
        print("  note: major versions differ (%s vs %s). Differences in how defaults or views are printed may show up as false changes." % (lv, nv))

    print("\nReading schemas (SELECT only)...")
    L = take_snapshot(local, args.schema, args.include_alembic)
    R = take_snapshot(neon, args.schema, args.include_alembic)
    for label, s in (("local", L), ("neon ", R)):
        print("  %s: %d tables, %d indexes, %d sequences, %d functions, %d views, %d triggers" % (
            label, len(s["tables"]), len(s["indexes"]), len(s["sequences"]), len(s["functions"]), len(s["views"]), len(s["triggers"])))

    def table_has_rows(tname):
        cur = neon.cursor()
        cur.execute("SELECT EXISTS (SELECT 1 FROM %s)" % qt(args.schema, tname))
        found = bool(cur.fetchone()[0])
        cur.close()
        return found

    items = build_plan(L, R, args.schema, table_has_rows)
    neon.rollback()
    actionable = [i for i in items if i["group"] in ("add", "change")]

    if not [i for i in items if i["group"] != "noise"]:
        print("\nThe schemas match. Nothing to do.")
        if items:
            print_plan(items)
        return
    print_plan(items)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_file = "schema_sync_plan_%s.sql" % stamp
    write_plan_file(items, plan_file, describe(local), describe(neon))
    print("\nFull SQL for sections A and B saved to: %s (read it before applying)" % plan_file)

    if not actionable:
        print("\nNothing this script can apply. Sections C and D need a human decision.")
        return
    if args.dry_run:
        print("\n--dry-run: nothing was changed.")
        return

    n_add = len([i for i in items if i["group"] == "add"])
    n_chg = len([i for i in items if i["group"] == "change"])
    print("\nWhat do you want to do?")
    print("  1 = apply section A only  (%d additions)" % n_add)
    if n_chg:
        print("  2 = apply sections A and B (%d additions + %d modifications)" % (n_add, n_chg))
    print("  n = stop, change nothing")
    choice = ask("Your choice [n]: ").lower()
    if choice == "1" and n_add:
        groups = {"add"}
    elif choice == "2" and n_chg:
        groups = {"add", "change"}
    else:
        print("Stopped. Nothing was changed.")
        return

    statements = statements_for(items, groups)
    print("\nTarget: NEON  %s" % describe(neon))
    print("%d SQL statements will run in ONE transaction. If any fails, all are rolled back." % len(statements))
    if ask("Is there a fresh Neon backup (a Neon branch or pg_dump)? [y/N]: ").lower() != "y":
        print("Make a backup first. Nothing was changed.")
        return
    if ask("Type APPLY (capital letters) to run it on Neon: ") != "APPLY":
        print("Not confirmed. Nothing was changed.")
        return

    neon.rollback()
    neon.set_session(readonly=False, autocommit=False)
    cur = neon.cursor()
    try:
        cur.execute("SET LOCAL lock_timeout = '15s'")
        for n, sql in enumerate(statements, 1):
            first = sql.strip().splitlines()[0][:100]
            print("  [%d/%d] %s" % (n, len(statements), first))
            cur.execute(sql)
        neon.commit()
        print("\nCommitted. Neon schema updated.")
    except Exception as exc:
        neon.rollback()
        print("\nFAILED - everything was rolled back, Neon is unchanged.")
        print("  statement: %s" % sql.strip().splitlines()[0][:140])
        print("  error    : %s" % str(exc).strip().splitlines()[0])
        sys.exit(1)

    make_readonly(neon)
    R2 = take_snapshot(neon, args.schema, args.include_alembic)
    left = [i for i in build_plan(L, R2, args.schema, lambda t: True) if i["group"] in ("add", "change")]
    neon.rollback()
    if left:
        print("\nStill different after the sync (%d):" % len(left))
        for i in left:
            print("  - %s" % i["title"].splitlines()[0])
    else:
        print("Re-check: no additions or modifications left to make.")
    new_seq = [i["title"].split(" ")[1] for i in items if i["kind"] == "sequence" and i["group"] == "add" and "add" in groups]
    if new_seq:
        print("\nREMINDER: these sequences were created fresh on Neon: %s" % ", ".join(new_seq))
        print("Their counters start at the beginning. Set each one above the highest existing id on Neon")
        print("with SELECT setval('public.<name>', <highest id>, true); before relying on them.")


if __name__ == "__main__":
    main()