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
