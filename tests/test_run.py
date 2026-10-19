import asyncio

import httpx
import pytest

import ingestion.client as client_mod
from ingestion.client import DataJudClient
from ingestion.run import job_key


def test_job_key_independe_da_ordem():
    assert job_key([283, 280]) == job_key([280, 283])


def _cliente_com_respostas(monkeypatch, codigos):
    """Cliente cuja API devolve os status em `codigos`, em ordem; registra as esperas."""
    respostas, esperas = list(codigos), []

    def handler(request):
        code = respostas.pop(0)
        body = {"hits": {"hits": []}} if code == 200 else {}
        return httpx.Response(code, json=body)

    original = httpx.AsyncClient
    monkeypatch.setattr(client_mod.httpx, "AsyncClient",
                        lambda **kw: original(transport=httpx.MockTransport(handler), **kw))

    async def fake_sleep(s):
        esperas.append(s)
    monkeypatch.setattr(client_mod.asyncio, "sleep", fake_sleep)
    return DataJudClient("x"), esperas


def test_504_espera_crescente_e_recupera(monkeypatch):
    cli, esperas = _cliente_com_respostas(monkeypatch, [504, 504, 200])
    asyncio.run(cli.search({"size": 1}))
    assert len(esperas) == 2 and 10 <= esperas[0] < 13 and 20 <= esperas[1] < 23


def test_429_espera_longa(monkeypatch):
    cli, esperas = _cliente_com_respostas(monkeypatch, [429, 200])
    asyncio.run(cli.search({"size": 1}))
    assert esperas == [30.0]


def test_desiste_depois_das_tentativas(monkeypatch):
    cli, esperas = _cliente_com_respostas(monkeypatch, [504] * 7)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(cli.search({"size": 1}))
    assert len(esperas) == 6


def test_resposta_parcial_de_shard_e_repetida(monkeypatch):
    respostas = [{"timed_out": False, "_shards": {"failed": 1}, "hits": {"hits": []}},
                 {"timed_out": False, "_shards": {"failed": 0}, "hits": {"hits": [{"_id": "ok"}]}}]
    esperas = []
    original = httpx.AsyncClient
    monkeypatch.setattr(client_mod.httpx, "AsyncClient",
                        lambda **kw: original(transport=httpx.MockTransport(
                            lambda req: httpx.Response(200, json=respostas.pop(0))), **kw))

    async def fake_sleep(s):
        esperas.append(s)
    monkeypatch.setattr(client_mod.asyncio, "sleep", fake_sleep)
    resultado = asyncio.run(DataJudClient("x").search({"size": 1}))
    assert resultado["hits"]["hits"] == [{"_id": "ok"}] and len(esperas) == 1
