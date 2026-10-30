"""Validate the PBIP: JSON files against their $schema, and report/model cross-references.

Usage: python tools/validate_pbip.py [--schemas <local clone of microsoft/json-schemas>] [--model-json <TOM json>]
Without --schemas, schemas are downloaded from developer.microsoft.com / GitHub.
TMDL syntax is validated separately with the TOM TmdlSerializer (see README).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
MS_PREFIX = "https://developer.microsoft.com/json-schemas/"


def make_retriever(local: Path | None):
    cache: dict[str, dict] = {}

    def retrieve(uri: str):
        if uri not in cache:
            if local and uri.startswith(MS_PREFIX):
                cache[uri] = json.loads((local / uri[len(MS_PREFIX):]).read_text(encoding="utf-8"))
            else:
                with urllib.request.urlopen(uri, timeout=60) as r:
                    cache[uri] = json.loads(r.read().decode("utf-8"))
        return Resource.from_contents(cache[uri], default_specification=__import__("referencing.jsonschema").jsonschema.DRAFT7)

    return retrieve


def validate_json(local: Path | None) -> int:
    retrieve = make_retriever(local)
    registry = Registry(retrieve=retrieve)
    errors = 0
    files = sorted(list(ROOT.rglob("*.json")) + list(ROOT.rglob("*.pbir")) + list(ROOT.rglob("*.pbism")) + list(ROOT.glob("*.pbip")))
    for f in files:
        if ".pbi" in f.parts or "tools" in f.parts:
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        uri = doc.get("$schema")
        if not uri:
            print(f"FAIL {f.relative_to(ROOT)}: no $schema"); errors += 1; continue
        schema = retrieve(uri).contents
        v = Draft7Validator(schema, registry=registry)
        errs = sorted(v.iter_errors(doc), key=lambda e: list(e.path))
        status = "OK  " if not errs else "FAIL"
        print(f"{status} {f.relative_to(ROOT)}  [{uri.rsplit('/', 3)[-3]}/{uri.rsplit('/', 2)[-2]}]")
        for e in errs[:10]:
            print("      ", list(e.path), e.message[:300])
        errors += len(errs)
    return errors


def walk_fields(obj, out):
    if isinstance(obj, dict):
        for k in ("Measure", "Column"):
            if k in obj and isinstance(obj[k], dict) and "Property" in obj[k]:
                sref = obj[k]["Expression"]["SourceRef"]
                if "Entity" in sref:  # alias refs (SourceRef.Source) inside filter Where clauses resolve via From
                    out.append((k, sref["Entity"], obj[k]["Property"]))
        for v in obj.values():
            walk_fields(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_fields(v, out)


def cross_refs(model_json: Path) -> int:
    m = json.loads(model_json.read_text(encoding="utf-8"))["model"]
    cols = {(t["name"], c["name"]) for t in m["tables"] for c in t.get("columns", [])}
    meas = {(t["name"], x["name"]) for t in m["tables"] for x in t.get("measures", [])}
    hidden = {(t["name"], c["name"]) for t in m["tables"] for c in t.get("columns", []) if c.get("isHidden")}
    errors = 0
    for r in m.get("relationships", []):
        for side in ("from", "to"):
            if (r[f"{side}Table"], r[f"{side}Column"]) not in cols:
                print(f"FAIL relationship {r['name']}: missing {r[side + 'Table']}[{r[side + 'Column']}]"); errors += 1
    for t in m["tables"]:
        for c in t.get("columns", []):
            if c.get("sortByColumn") and (t["name"], c["sortByColumn"]) not in cols:
                print(f"FAIL sortByColumn {t['name']}[{c['name']}]"); errors += 1
    names = {n for _, n in meas}
    colnames = {f"'{t}'[{c}]" for t, c in cols}
    for t, n in sorted(meas):
        expr = next(x["expression"] for tt in m["tables"] if tt["name"] == t for x in tt["measures"] if x["name"] == n)
        expr = expr if isinstance(expr, str) else "\n".join(expr)
        for ref in re.findall(r"'([^']+)'\[([^\]]+)\]", expr):
            if ref not in cols:
                print(f"FAIL measure [{n}] references missing column '{ref[0]}'[{ref[1]}]"); errors += 1
        for ref in re.findall(r"(?<!')\[([^\]]+)\]", re.sub(r"'[^']+'\[[^\]]+\]", "", expr)):
            if ref not in names:
                print(f"FAIL measure [{n}] references missing measure [{ref}]"); errors += 1
    tables = {t["name"] for t in m["tables"]}
    for r in m.get("roles", []):
        for tp in r.get("tablePermissions", []):
            if tp["name"] not in tables:
                print(f"FAIL role {r['name']}: table {tp['name']} missing"); errors += 1
            for col in re.findall(r"\[([^\]]+)\]", tp.get("filterExpression", "")):
                if (tp["name"], col) not in cols:
                    print(f"FAIL role {r['name']}: column {tp['name']}[{col}] missing"); errors += 1
    print(f"roles: {[r['name'] for r in m.get('roles', [])]}")
    errors += report_refs()
    errors += rls_safety(m)
    errors += domain_separation(m)
    errors += query_consistency(m)
    errors += forecast_rules(m)
    n_vis = 0
    for vf in sorted((ROOT / "Enterprise360.Report").rglob("visual.json")):
        n_vis += 1
        refs: list = []
        walk_fields(json.loads(vf.read_text(encoding="utf-8")), refs)
        for kind, ent, prop in refs:
            ok = (ent, prop) in (meas if kind == "Measure" else cols)
            if not ok:
                print(f"FAIL {vf.parent.name}: {kind} {ent}.{prop} not in model"); errors += 1
            elif kind == "Column" and (ent, prop) in hidden:
                print(f"WARN {vf.parent.name}: hidden column {ent}.{prop} used")
    print(f"cross-reference: {len(m['relationships'])} relationships, {len(meas)} measures, {n_vis} visuals checked, {errors} errors")
    return errors


def forecast_rules(m: dict) -> int:
    """KPI_GMV_FORECAST / KPI_GMV_ANOMALY_FLAG guards: never plot in-sample (train) forecast_gmv; never use is_anomaly."""
    errors = n = 0
    for t in m["tables"]:
        for ms in t.get("measures", []):
            expr = ms["expression"] if isinstance(ms["expression"], str) else "\n".join(ms["expression"])
            if "[forecast_gmv]" in expr:
                n += 1
                if "[is_forecast] = TRUE ()" not in expr and not re.search(r'\[Split\] IN \{\s*"validation",\s*"test"\s*\}', expr):
                    print(f"FAIL measure {ms['name']}: forecast_gmv without is_forecast / validation+test filter (train rows = in-sample fit)"); errors += 1
            if re.search(r"\[(is_anomaly|is_any_anomaly)\]", expr):
                print(f"FAIL measure {ms['name']}: uses the combined GMV-or-orders flag; use is_gmv_anomaly"); errors += 1
    for t in m["tables"]:
        for c in t.get("columns", []):
            if c.get("sourceColumn") in ("is_anomaly", "is_any_anomaly", "fitted_gmv"):
                print(f"FAIL {t['name']}[{c['name']}]: {c['sourceColumn']} must not be loaded"); errors += 1
    print(f"forecast-rules: {n} forecast_gmv measures checked, {errors} violations")
    return errors


def query_consistency(m: dict) -> int:
    """Guards against Desktop's 'pending changes in your queries' banner: the Power Query document Desktop
    rebuilds from the model must match the model exactly (query list, result types, annotations)."""
    errors = 0
    ann = {a["name"]: a["value"] for a in m.get("annotations", [])}
    order = json.loads(ann.get("PBI_QueryOrder", "[]"))
    m_tables = [t for t in m["tables"] if any(p_.get("source", {}).get("type") == "m" for p_ in t.get("partitions", []))]
    expected = [e["name"] for e in m.get("expressions", [])] + [t["name"] for t in m_tables]
    if len(order) != len(set(order)):
        print("FAIL PBI_QueryOrder has duplicates"); errors += 1
    for q_ in set(expected) - set(order):
        print(f"FAIL PBI_QueryOrder missing query {q_}"); errors += 1
    for q_ in set(order) - set(expected):
        print(f"FAIL PBI_QueryOrder lists unknown query {q_}"); errors += 1
    for t in m_tables:
        tann = {a["name"]: a["value"] for a in t.get("annotations", [])}
        src = "\n".join(p_["source"]["expression"] if isinstance(p_["source"]["expression"], str) else "\n".join(p_["source"]["expression"])
                        for p_ in t["partitions"])
        if tann.get("PBI_ResultType") != "Table":
            print(f"FAIL table {t['name']}: missing annotation PBI_ResultType = Table"); errors += 1
        if "Item =" in src and tann.get("PBI_NavigationStepName") != "Navigation":
            print(f"FAIL table {t['name']}: missing annotation PBI_NavigationStepName = Navigation"); errors += 1
        for c in t.get("columns", []):
            if c.get("type") == "calculated" or "sourceColumn" not in c:
                continue
            sc = re.escape(c["sourceColumn"])
            is_cur = re.search(r'\{\s*"' + sc + r'"\s*,\s*Currency\.Type\s*\}', src) is not None
            if c.get("dataType") == "decimal" and not is_cur:
                print(f"FAIL {t['name']}[{c['name']}]: dataType decimal but M does not type it Currency.Type"); errors += 1
            if is_cur and c.get("dataType") != "decimal":
                print(f"FAIL {t['name']}[{c['name']}]: M types it Currency.Type but dataType is {c.get('dataType')}"); errors += 1
    for e in m.get("expressions", []):
        if (e.get("kind") or "m") == "m" and "IsParameterQuery" in str(e.get("expression")):
            if not any(a["name"] == "PBI_ResultType" for a in e.get("annotations", [])) or not e.get("lineageTag"):
                print(f"FAIL parameter {e['name']}: missing PBI_ResultType annotation or lineageTag"); errors += 1
    for stale in ("unappliedChanges.json", "cache.abf"):
        for f in ROOT.rglob(f".pbi/{stale}"):
            print(f"FAIL {f.relative_to(ROOT)} present: remove it (stale Desktop state)"); errors += 1
    print(f"query-consistency: {len(order)} queries in PBI_QueryOrder, {len(m_tables)} M tables, {errors} errors")
    return errors


UCI_MEASURES_TABLE = "_Measures UCI"
UCI_PAGE_SUBTITLE = "not comparable with Olist"
UCI_RLS_ROLE = "State Manager (demo)"


def is_uci(table: str) -> bool:
    return table.startswith("UCI ") or table == UCI_MEASURES_TABLE


def domain_separation(m: dict) -> int:
    """UCI Online Retail II (GBP) and Olist (BRL) must never be joined or mixed."""
    errors = 0
    tables = {t["name"] for t in m["tables"]}
    uci = {t for t in tables if is_uci(t)}
    for r in m.get("relationships", []):
        if is_uci(r["fromTable"]) != is_uci(r["toTable"]):
            print(f"FAIL relationship connects UCI and Olist: {r['fromTable']}[{r['fromColumn']}] -> {r['toTable']}[{r['toColumn']}]"); errors += 1
    mdomain = {ms["name"]: is_uci(t["name"]) for t in m["tables"] for ms in t.get("measures", [])}
    for t in m["tables"]:
        for ms in t.get("measures", []):
            expr = ms["expression"] if isinstance(ms["expression"], str) else "\n".join(ms["expression"])
            refs = set(re.findall(r"'([^']+)'", expr)) & tables
            refs |= {x for x in re.findall(r"(?<![\w'\]])([A-Za-z_][A-Za-z0-9_ ]*)\[", expr) if x in tables}
            mrefs = {x for x in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", expr) if x in mdomain}
            mine = is_uci(t["name"])
            bad = [x for x in refs if is_uci(x) != mine] + [x for x in mrefs if mdomain[x] != mine]
            if bad:
                print(f"FAIL measure {t['name']}[{ms['name']}] mixes UCI and Olist references: {bad}"); errors += 1
    role = next((r for r in m.get("roles", []) if r["name"] == UCI_RLS_ROLE), None)
    if role is not None:
        perms = {tp["name"]: tp.get("filterExpression", "").replace(" ", "").upper() for tp in role.get("tablePermissions", [])}
        for t in sorted(uci - {UCI_MEASURES_TABLE}):
            if perms.get(t) != "FALSE()":
                print(f"FAIL role {UCI_RLS_ROLE}: UCI table {t} not hidden (expected FALSE())"); errors += 1
    n_vis = n_uci_vis = 0
    uci_pages: dict = {}
    for vf in sorted((ROOT / "Enterprise360.Report").rglob("visual.json")):
        n_vis += 1
        refs: list = []
        v = json.loads(vf.read_text(encoding="utf-8"))
        walk_fields(v, refs)
        ents = {ent for _, ent, _ in refs}
        page = vf.parent.parent.parent.name
        if ents and all(is_uci(e) for e in ents):
            n_uci_vis += 1
            uci_pages.setdefault(page, False)
        if any(is_uci(e) for e in ents) and any(not is_uci(e) for e in ents):
            print(f"FAIL visual {vf.parent.name} mixes UCI and Olist fields: {sorted(ents)}"); errors += 1
        if UCI_PAGE_SUBTITLE in json.dumps(v):
            uci_pages[page] = True
    for page, ok in uci_pages.items():
        if not ok:
            print(f"FAIL UCI page {page}: no '{UCI_PAGE_SUBTITLE}' subtitle"); errors += 1
    print(f"domain-separation: {len(uci)} UCI tables, {len(m.get('relationships', []))} relationships checked, "
          f"{n_vis} visuals ({n_uci_vis} UCI) on {len(uci_pages)} UCI pages, {errors} violations")
    return errors


FORBIDDEN = [
    (re.compile(r"CROSSFILTER\s*\([^)]*,\s*NONE\s*\)", re.I), "CROSSFILTER(..., NONE) breaks RLS/slicer propagation"),
    (re.compile(r"\b(ALL|ALLEXCEPT|ALLNOBLANKROW|ALLSELECTED|REMOVEFILTERS)\s*\(\s*'?(Geography|Customer|Order)'?\s*[\)\[,]", re.I),
     "ALL/REMOVEFILTERS on Geography/Customer/Order removes RLS-propagating filters"),
]


def rls_safety(m: dict) -> int:
    """No measure, calc item or calculated column may cut the Geography -> Customer -> Order path."""
    errors = 0
    exprs = []
    for t in m["tables"]:
        for x in t.get("measures", []):
            exprs.append((f"measure [{x['name']}]", x["expression"]))
        for c in t.get("columns", []):
            if c.get("type") == "calculated":
                exprs.append((f"column {t['name']}[{c['name']}]", c["expression"]))
        for ci in t.get("calculationGroup", {}).get("calculationItems", []):
            exprs.append((f"calc item {ci['name']}", ci["expression"]))
    for where, e in exprs:
        e = e if isinstance(e, str) else "\n".join(e)
        for rx, why in FORBIDDEN:
            if rx.search(e):
                print(f"FAIL {where}: {why}"); errors += 1
    print(f"rls-safety: {len(exprs)} expressions scanned, {errors} violations")
    return errors


def report_refs() -> int:
    """Pages, drill-through bindings, tooltip assignments, bookmark targets and button links."""
    errors = 0
    rdef = ROOT / "Enterprise360.Report" / "definition"
    pages = {}
    for pj in (rdef / "pages").glob("*/page.json"):
        pg = json.loads(pj.read_text(encoding="utf-8"))
        vis = {}
        for vf in (pj.parent / "visuals").glob("*/visual.json"):
            v = json.loads(vf.read_text(encoding="utf-8"))
            if v["name"] != vf.parent.name:
                print(f"FAIL visual folder/name mismatch {vf}"); errors += 1
            vis[v["name"]] = v
        if pg["name"] != pj.parent.name:
            print(f"FAIL page folder/name mismatch {pj}"); errors += 1
        pages[pg["name"]] = (pg, vis)
    meta = json.loads((rdef / "pages" / "pages.json").read_text(encoding="utf-8"))
    if set(meta["pageOrder"]) != set(pages):
        print("FAIL pages.json pageOrder does not match page folders"); errors += 1
    bm_names = set()
    bdir = rdef / "bookmarks"
    if bdir.exists():
        bmeta = json.loads((bdir / "bookmarks.json").read_text(encoding="utf-8"))
        for bf in bdir.glob("*.bookmark.json"):
            b = json.loads(bf.read_text(encoding="utf-8"))
            bm_names.add(b["name"])
            if bf.name != f"{b['name']}.bookmark.json":
                print(f"FAIL bookmark file name {bf.name}"); errors += 1
            es = b["explorationState"]
            if es["activeSection"] not in pages:
                print(f"FAIL bookmark {b['name']}: activeSection missing"); errors += 1
            for sec, st in es["sections"].items():
                for vn, vs in st["visualContainers"].items():
                    if sec not in pages or vn not in pages[sec][1]:
                        print(f"FAIL bookmark {b['name']}: visual {vn} missing"); errors += 1
                    elif vs["singleVisual"]["visualType"] != pages[sec][1][vn]["visual"]["visualType"]:
                        print(f"FAIL bookmark {b['name']}: visualType mismatch {vn}"); errors += 1
            for vn in b.get("options", {}).get("targetVisualNames", []):
                if not any(vn in p[1] for p in pages.values()):
                    print(f"FAIL bookmark {b['name']}: target {vn} missing"); errors += 1
        listed = {i["name"] for i in bmeta["items"]} | {c for i in bmeta["items"] for c in i.get("children", [])}
        if listed != bm_names:
            print("FAIL bookmarks.json items do not match bookmark files"); errors += 1
    lit = lambda o: o["expr"]["Literal"]["Value"].strip("'")
    n_tt = n_dt = n_links = 0
    for pname, (pg, vis) in pages.items():
        pb = pg.get("pageBinding")
        if pg.get("type") == "Drillthrough":
            n_dt += 1
            fnames = {f["name"] for f in pg.get("filterConfig", {}).get("filters", [])}
            for prm in (pb or {}).get("parameters", []):
                if prm.get("boundFilter") not in fnames:
                    print(f"FAIL drillthrough {pname}: boundFilter missing"); errors += 1
            if not pb or pb.get("type") != "Drillthrough":
                print(f"FAIL drillthrough {pname}: pageBinding"); errors += 1
        if pg.get("type") == "Tooltip" and (not pb or pb.get("type") != "Tooltip"):
            print(f"FAIL tooltip {pname}: pageBinding"); errors += 1
        for vn, v in vis.items():
            vco = v.get("visual", {}).get("visualContainerObjects", {})
            for tt in vco.get("visualTooltip", []):
                sec = lit(tt["properties"]["section"]); n_tt += 1
                if sec not in pages or pages[sec][0].get("type") != "Tooltip":
                    print(f"FAIL {vn}: tooltip page {sec} missing / not a Tooltip page"); errors += 1
            for vl in vco.get("visualLink", []):
                pr = vl["properties"]; n_links += 1
                if lit(pr["type"]) == "Bookmark" and lit(pr["bookmark"]) not in bm_names:
                    print(f"FAIL {vn}: bookmark link target missing"); errors += 1
    # drill-through usable: every drill field must appear in at least one visual on a non-drill page
    for pname, (pg, vis) in pages.items():
        if pg.get("type") != "Drillthrough":
            continue
        f = pg["filterConfig"]["filters"][0]["field"]["Column"]
        key = (f["Expression"]["SourceRef"]["Entity"], f["Property"])
        sources = []
        for on, (opg, ovis) in pages.items():
            if on == pname or opg.get("type") == "Tooltip":
                continue
            for vn, v in ovis.items():
                refs: list = []
                walk_fields(v.get("visual", {}).get("query", {}), refs)
                if ("Column",) + key in refs:
                    sources.append(f"{opg['displayName']}/{vn}")
        if not sources:
            print(f"FAIL drillthrough {pg['displayName']}: no source visual uses {key}"); errors += 1
        else:
            print(f"drill-through {pg['displayName']} on {key[0]}[{key[1]}]: {len(sources)} source visual(s)")
    print(f"report: {len(pages)} pages, {n_dt} drill-through, {len(bm_names)} bookmarks, {n_tt} tooltip assignments, {n_links} button links")
    return errors


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", type=Path)
    ap.add_argument("--model-json", type=Path)
    a = ap.parse_args()
    e = validate_json(a.schemas)
    if a.model_json:
        e += cross_refs(a.model_json)
    print("TOTAL ERRORS:", e)
    sys.exit(1 if e else 0)
