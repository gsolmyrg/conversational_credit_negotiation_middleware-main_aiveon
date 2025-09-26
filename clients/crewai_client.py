# -*- coding: utf-8 -*-
import os
import json
from time import sleep
from typing import Any

import requests


def _to_jsonable(obj: Any):
    """
    Converte objetos Pydantic/BaseModel/estruturas aninhadas em algo serializável em JSON.
    - Pydantic v2: usa model_dump()
    - Pydantic v1: usa dict()
    - dict/list/tuple: processa recursivamente
    - outros tipos: retorna como está (desde que json-serializable)
    """
    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass
    # Pydantic v1
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass

    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]

    return obj


class CrewaiClient:
    """
    Cliente para o servidor do CrewAI (Flow).
    - POST /kickoff -> retorna ID
    - GET  /status/{id} -> faz polling até SUCCESS/FAILED
    """
    KICKOFF_ENDPOINT = "/kickoff"
    STATUS_ENDPOINT = "/status"

    def __init__(self):
        self._url = os.getenv("CREWAI_URL")
        self._token = os.getenv("CREWAI_TOKEN")

    # -----------------------
    # URLs base
    # -----------------------
    @property
    def kickoff_url(self) -> str:
        return f"{self._url}{self.KICKOFF_ENDPOINT}"

    @property
    def status_url(self) -> str:
        return f"{self._url}{self.STATUS_ENDPOINT}/"

    # -----------------------
    # Headers
    # -----------------------
    @property
    def headers(self) -> dict:
        return {
            "apikey": self._token,
            "Content-Type": "application/json",
        }

    # -----------------------
    # APIs
    # -----------------------
    def kickoff(self, payload: Any) -> str:
        """
        Dispara a execução do Flow. Retorna o ID para polling.
        Aceita payload como dict ou objeto Pydantic; converte para JSON-serializable.
        """
        json_payload = _to_jsonable(payload)

        response = requests.post(self.kickoff_url, headers=self.headers, json=json_payload)
        response.raise_for_status()
        data = response.json()

        kickoff_id = (
            data.get("id")
            or data.get("kickoff_id")
            or data.get("task_id")
            or data.get("run_id")
            or data.get("data", {}).get("id")
            or data.get("data", {}).get("kickoff_id")
            or data.get("result", {}).get("id")
        )
        if not kickoff_id:
            raise RuntimeError(f"Kickoff sem ID reconhecível: {data}")

        return kickoff_id

    def status(self, kickoff_id: str):
        """
        Faz polling até SUCCESS/FAILED.
        - Se SUCCESS: retorna preferencialmente 'result_json' (objeto).
          Se não houver, tenta desserializar 'result' (string JSON).
        - Se FAILED: lança Exception com o payload inteiro para log.
        """
        attempts = 0
        max_attempts = 240  # ~48s com sleep(0.2)
        while attempts < max_attempts:
            response = requests.get(self.status_url + kickoff_id, headers=self.headers)
            response.raise_for_status()
            response_json = response.json()

            state = response_json.get("state")
            if state == "SUCCESS":
                # Preferir objeto já desserializado
                if "result_json" in response_json and response_json["result_json"] is not None:
                    return response_json["result_json"]

                # Fallback: 'result' frequentemente vem como STRING JSON
                res = response_json.get("result")
                if isinstance(res, str):
                    try:
                        return json.loads(res)
                    except json.JSONDecodeError:
                        return res  # não é JSON -> devolve bruto
                return res

            if state == "FAILED":
                raise Exception(f"Request failed with status: {response_json}")

            sleep(0.2)
            attempts += 1

        raise Exception(f"Request timed out after {max_attempts} attempts")
