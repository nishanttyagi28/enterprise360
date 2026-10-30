import re

import pytest
import yaml

pytestmark = pytest.mark.unit

@pytest.fixture(scope="module")
def gov(repo_root):
    d = repo_root / "governance" / "kpi_dictionary"
    return {n: yaml.safe_load((d / f"{n}.yaml").read_text()) for n in ("schema", "kpis", "not_supported")}

def test_all_required_fields(gov):
    req = gov["schema"]["required_fields"]
    for k in gov["kpis"]["kpis"]:
        missing = [f for f in req if f not in k]
        assert not missing, (k["id"], missing)

def test_ids_unique_and_pattern(gov):
    ids = [k["id"] for k in gov["kpis"]["kpis"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"KPI_[A-Z0-9_]+", i) for i in ids)

def test_status_values(gov):
    assert {k["status"] for k in gov["kpis"]["kpis"]} <= {"SUPPORTED", "PARTIAL"}

def test_semver(gov):
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", k["version"]) for k in gov["kpis"]["kpis"])

def test_no_invented_targets(gov):
    for k in gov["kpis"]["kpis"]:
        assert k["target"] == "to be set by owner" and k["benchmark"] == "to be set by owner", k["id"]

def test_gmv_is_not_revenue(gov):
    gmv = next(k for k in gov["kpis"]["kpis"] if k["id"] == "KPI_GMV")
    assert "NOT recognized revenue" in gmv["definition"]
    assert any("Revenue" in r for r in gmv["validation_rules"])
    for k in gov["kpis"]["kpis"]:
        assert "revenue" not in k["name"].lower(), k["id"]

def test_payment_vs_items_rule(gov):
    pv = next(k for k in gov["kpis"]["kpis"] if k["id"] == "KPI_PAYMENT_VALUE")
    assert any("item_price+freight_value" in r for r in pv["validation_rules"])

def test_not_supported_has_reasons(gov):
    assert all(x["reason"] and x["handling"] for x in gov["not_supported"]["not_supported"])


def test_catalog_up_to_date(repo_root):
    import subprocess, sys
    r = subprocess.run([sys.executable, str(repo_root / "governance/kpi_dictionary/generate_catalog.py"), "--check"])
    assert r.returncode == 0, "docs/kpi-catalog.md stale: run governance/kpi_dictionary/generate_catalog.py"


def test_domains_separate(gov):
    for k in gov["kpis"]["kpis"]:
        assert k["domain"] in {"olist", "uci"}
        assert k["id"].startswith("KPI_UCI_") == (k["domain"] == "uci"), k["id"]
        deps = " ".join(k["fact_dependencies"] + k["dimension_dependencies"])
        if k["domain"] == "uci":
            assert "fct_order" not in deps and "fct_payments" not in deps, k["id"]
        else:
            assert "uci_" not in deps, k["id"]


def test_supporting_measure_kinds(gov):
    for k in gov["kpis"]["kpis"]:
        for m in k.get("supporting_measures", []):
            assert m["kind"] in {"breakdown", "dq_exclusion", "formatting"} and m["measure"] and m["purpose"]


def test_dq_score_strict(gov):
    k = next(k for k in gov["kpis"]["kpis"] if k["id"] == "KPI_DQ_SCORE")
    assert k["version"] == "1.2.0" and "core.dq_run_summary" in k["implementations"]["dbt"]


def test_funnel_and_forecast_kpis(gov):
    ks = {k["id"]: k for k in gov["kpis"]["kpis"]}
    areas = set(gov["schema"]["fields"]["area"]["values"])
    for i in ("KPI_FUNNEL_MQLS", "KPI_FUNNEL_CLOSED_DEALS", "KPI_FUNNEL_CONVERSION_RATE",
              "KPI_FUNNEL_MEDIAN_DAYS_TO_CLOSE", "KPI_GMV_FORECAST", "KPI_GMV_ANOMALY_FLAG"):
        k = ks[i]
        assert k["domain"] == "olist" and k["area"] in areas and k["caveats"], i
    assert ks["KPI_FUNNEL_CONVERSION_RATE"]["status"] == "PARTIAL"
    assert "cohort" in ks["KPI_FUNNEL_CONVERSION_RATE"]["definition"].lower()
    for i in ("KPI_GMV_FORECAST", "KPI_GMV_ANOMALY_FLAG"):
        assert ks[i]["status"] == "PARTIAL" and "exploratory" in ks[i]["name"].lower()
    assert "Backtest" in ks["KPI_GMV_FORECAST"]["definition"]  # only stored backtest values cited
    assert gov["kpis"]["dictionary_version"] == "2.1.0"
