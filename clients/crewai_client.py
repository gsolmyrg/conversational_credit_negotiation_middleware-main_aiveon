# -*- coding: utf-8 -*-
import os
import json
from time import sleep

import requests


class CrewaiClient:
    """
    Cliente fino para orquestrar o Flow no servidor CrewAI Enterprise.
    - /kickoff  -> envia o payload e recebe um ID de execução
    - /status/{id} -> faz polling até SUCCESS/FAILED e retorna o resultado

    CONTRATOS EXTERNOS: preservados.
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
        # Ex.: https://<host>/kickoff
        return f"{self._url}{self.KICKOFF_ENDPOINT}"

    @property
    def status_url(self) -> str:
        # Ex.: https://<host>/status/
        # (nota: concatenamos o kickoff_id na chamada)
        return f"{self._url}{self.STATUS_ENDPOINT}/"

    # -----------------------
    # Headers
    # -----------------------
    @property
    def headers(self) -> dict:
        # Alguns servidores CrewAI usam 'apikey'; outros aceitam 'Authorization: Bearer'
        # Mantemos 'apikey' pois era o formato original do seu projeto.
        return {
            "apikey": self._token,
            "Content-Type": "application/json",
        }

    # -----------------------
    # APIs
    # -----------------------
    def kickoff(self, payload: dict) -> str:
        """
        Dispara a execução no servidor do CrewAI.
        Retorna o ID para polling no /status/{id}.
        """
        response = requests.post(self.kickoff_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Tolerante a variações de nome de ID do servidor
        kickoff_id = (
            data.get("id")
            or data.get("kickoff_id")
            or data.get("task_id")
            or data.get("run_id")
        )
        if not kickoff_id:
            # Em alguns servidores, o id vem aninhado
            kickoff_id = (
                data.get("data", {}).get("id")
                or data.get("data", {}).get("kickoff_id")
                or data.get("result", {}).get("id")
            )

        if not kickoff_id:
            raise RuntimeError(f"Kickoff sem ID reconhecível: {data}")

        return kickoff_id

    def status(self, kickoff_id: str):
        """
        Faz polling até SUCCESS/FAILED.
        - Se SUCCESS: retorna preferencialmente 'result_json' (objeto). Caso não exista,
          tenta desserializar 'result' (string JSON). Se não for JSON válido, retorna como veio.
        - Se FAILED: levanta Exception com o JSON completo para log.
        """
        attempts = 0
        max_attempts = 240  # ~48s @ 0.2s
        while attempts < max_attempts:
            resp = requests.get(self.status_url + kickoff_id, headers=self.headers)
            resp.raise_for_status()
            response_json = resp.json()

            state = response_json.get("state")
            if state == "SUCCESS":
                # Preferir objeto já desserializado, se existir
                if "result_json" in response_json and response_json["result_json"] is not None:
                    return response_json["result_json"]

                # Fallback: muitos servidores colocam o payload em 'result' como STRING JSON
                res = response_json.get("result")
                if isinstance(res, str):
                    try:
                        return json.loads(res)
                    except json.JSONDecodeError:
                        # Se não for um JSON parseável, devolve a string como está
                        return res
                # Por via das dúvidas, retorna o que tiver
                return res

            elif state == "FAILED":
                # Propaga erro com payload completo para troubleshooting
                raise Exception(f"Request failed with status: {response_json}")

            # Aguardar próximo ciclo
            sleep(0.2)
            attempts += 1

        raise Exception(f"Request timed out after {max_attempts} attempts")
