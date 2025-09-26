# -*- coding: utf-8 -*-
import json
from typing import Any

# IMPORTS ABSOLUTOS para funcionar com `python main.py`
from clients.crewai_client import CrewaiClient, _to_jsonable
from clients.whatsapp_client import WhatsappClient
from models import Message  # seu models.py tem Message(role, content)


class MessageSubmissionService:
    def __init__(self):
        self._crewai_client = CrewaiClient()
        self._whatsapp_client = WhatsappClient()

    def kickoff_interaction(self, body: Any) -> Message:
        """
        Fluxo:
        - Dispara o kickoff no CrewAI (Flow)
        - Faz polling no /status/{id}
        - Garante que o resultado seja dict (não string)
        - Pega a última mensagem do 'history'
        - Envia via WhatsApp para a persona (se houver número)
        - Retorna Message(role, content) para o controller HTTP responder

        Aceita 'body' como dict OU objeto Pydantic. Converte para JSON-serializable.
        """
        # 0) Normaliza o body (aceita Pydantic v1/v2)
        body_json = _to_jsonable(body)

        # 1) Dispara o Flow
        kickoff_id = self._crewai_client.kickoff(body_json)

        # 2) Polling até obter o resultado final
        result_raw = self._crewai_client.status(kickoff_id)

        # 3) Se vier string JSON, desserializa; se já vier dict, mantém
        if isinstance(result_raw, str):
            try:
                result_json = json.loads(result_raw)
            except json.JSONDecodeError:
                raise RuntimeError(f"Resultado do CrewAI não é JSON válido: {result_raw[:200]}...")
        elif isinstance(result_raw, dict):
            result_json = result_raw
        else:
            raise RuntimeError(f"Formato inesperado de resultado do CrewAI: {type(result_raw)}")

        # 4) Extrai a última mensagem do histórico
        history = result_json.get("history")
        if not isinstance(history, list) or not history:
            raise RuntimeError("Resultado do CrewAI não contém 'history' com itens.")

        last_msg = history[-1]
        if not isinstance(last_msg, dict) or "role" not in last_msg or "content" not in last_msg:
            raise RuntimeError("Último item do 'history' não está no formato {role, content}.")

        assistant_message = Message(**last_msg)

        # 5) Dispara WhatsApp (Evolution API)
        persona = None
        # tenta pegar do body original; se for Pydantic, já foi convertido para dict em body_json
        if isinstance(body_json, dict):
            persona = body_json.get("persona")
            # também suportar envelope {"inputs": {...}}
            if persona is None:
                inputs = body_json.get("inputs")
                if isinstance(inputs, dict):
                    persona = inputs.get("persona")

        number = ""
        if isinstance(persona, dict):
            number = str(persona.get("cellphone", "")).strip()

        if number:
            self._whatsapp_client.send_text(number=number, text=assistant_message.content)

        return assistant_message
