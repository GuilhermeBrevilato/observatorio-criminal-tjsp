"""Primeira exploração: até 10 registros, sem exibir identificadores processuais."""
import asyncio
import json
import os
from dotenv import load_dotenv
from ingestion.client import DataJudClient, build_query

async def main():
    load_dotenv()
    client = DataJudClient(os.getenv("DATAJUD_API_KEY", ""))
    response = await client.search(build_query(size=10))
    hits = response["hits"]["hits"]
    print("Registros recebidos:", len(hits))
    if hits:
        print("Campos do primeiro _source:", sorted(hits[0]["_source"].keys()))
        print("Classe (exemplo):", hits[0]["_source"].get("classe"))

if __name__ == "__main__":
    asyncio.run(main())
