import pytest
from ingestion.client import build_count_query, build_query
from ingestion.demo_seed import demo_hits


def test_query_default():
    q = build_query(10)
    assert q["size"] == 10
    assert q["query"] == {"match_all": {}}


def test_query_filtered():
    q = build_query(20, [123, 456], [42])
    assert q["query"]["bool"]["filter"] == [{"terms": {"classe.codigo": [123, 456]}}]
    assert q["search_after"] == [42]


def test_nenhum_filtro_de_data_na_fonte():
    """Regressão: a data do DataJud não é confiável para filtrar (ver README)."""
    import json
    assert "dataAjuizamento" not in json.dumps(build_query(10, [280]))
    assert "dataAjuizamento" not in json.dumps(build_count_query([280]))


def test_invalid_page_size():
    with pytest.raises(ValueError):
        build_query(0)


def test_synthetic_ids_unique():
    hits = demo_hits()
    assert len({h["_id"] for h in hits}) == len(hits)
    assert all(h["_id"].startswith("DEMO_") for h in hits)  # nada que pareça dado real
