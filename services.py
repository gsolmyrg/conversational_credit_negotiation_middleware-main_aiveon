# -*- coding: utf-8 -*-
import os
import json
import uuid
from uuid import uuid5, NAMESPACE_URL

# IMPORTS ABSOLUTOS (sem ponto) para funcionar com `python main.py`
from clients.crewai_client import CrewaiClient
from clients.whatsapp_client import WhatsappClient
from models import Message  # ajuste se tiver WhatsappRequestBody etc.


class MessageSubmissionService:
    def __init__(self):
        self._crewai_client = CrewaiClient()
        self._whatsapp_client = WhatsappClient()

    def kickoff_interaction(self, body: dict) -> Message:
        """
        Orquestra:
        - Dispara o kickoff no CrewAI
        - Faz polling no /status/{id}
        - Extrai a última mensagem do histórico
        - Retorna Message(role, content) para o controlador HTTP responder
        """
        # 1) Dispara o Flow
        kickoff_id = self._crewai_client.kickoff(body)

        # 2) Polling até obter o resultado
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

        return assistant_message


# Exemplo de outro serviço (se usar webhook do WhatsApp), mantenha/ou remova conforme seu projeto.
# from models import WhatsappRequestBody
# class WhatsappWebhookService:
#     def __init__(self):
#         self._crewai_client = CrewaiClient()
#         self._whatsapp_client = WhatsappClient()
#     def handle_inbound(self, body: WhatsappRequestBody) -> None:
#         pass
