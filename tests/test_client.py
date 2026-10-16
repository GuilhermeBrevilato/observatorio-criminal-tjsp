import pytest
from ingestion.client import build_query
from ingestion.demo_seed import demo_hits


def test_query_default():
    q = build_query(10)
    assert q["size"] == 10
    assert q["query"] == {"match_all": {}}


def test_query_filtered():
    q = build_query(20, [123, 456], "2025-01-01", "2026-01-01", [42])
    assert q["query"]["bool"]["filter"][0] == {"terms": {"classe.codigo": [123, 456]}}
    assert q["search_after"] == [42]


def test_invalid_page_size():
    with pytest.raises(ValueError):
        build_query(0)


def test_synthetic_ids_unique():
    hits = demo_hits()
    assert len({h["_id"] for h in hits}) == 30
