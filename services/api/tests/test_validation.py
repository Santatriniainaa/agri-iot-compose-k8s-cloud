"""Validation des entrées interpolées dans les requêtes Flux (anti-injection)."""
import pytest
from fastapi import HTTPException

from core.validation import safe_metric, safe_parcel, safe_range


def test_safe_parcel_accepts_valid():
    assert safe_parcel("zoneA") == "zoneA"
    assert safe_parcel("farm_01-A") == "farm_01-A"


@pytest.mark.parametrize("bad", ["bad name", "a;b", "zone\"A", "x" * 65, ""])
def test_safe_parcel_rejects_invalid(bad):
    with pytest.raises(HTTPException) as exc:
        safe_parcel(bad)
    assert exc.value.status_code == 400


def test_safe_metric_whitelist():
    assert safe_metric("soil_moisture_avg") == "soil_moisture_avg"
    with pytest.raises(HTTPException):
        safe_metric("DROP TABLE")


@pytest.mark.parametrize("ok", ["-1h", "-30m", "-7d", "-15s", "-2w"])
def test_safe_range_accepts(ok):
    assert safe_range(ok) == ok


@pytest.mark.parametrize("bad", ["1h", "-1y", "-h", "now()", "-99999999h"])
def test_safe_range_rejects(bad):
    with pytest.raises(HTTPException):
        safe_range(bad)
