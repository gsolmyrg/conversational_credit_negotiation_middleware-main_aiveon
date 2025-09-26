# -*- coding: utf-8 -*-
import json

# IMPORTS ABSOLUTOS para funcionar com `python main.py`
from clients.crewai_client import CrewaiClient
from clients.whatsapp_client import WhatsappClient
from models import Message  # seu models.py tem Message(role, content)


class MessageSubmissionService:
    def __init__(self):
        self._crewai_client = CrewaiClient()
        self._whatsapp_client = WhatsappClient()

    def kickoff_interaction(self, body: dict) -> Message:
        """
        Fluxo:
        - Dispara o kickoff no CrewAI (Flow)
        - Faz polling no /status/{id}
        - Garante que o resultado seja dict (não string)
        - Pega a última mensagem do 'history'
        - Envia via WhatsApp para a persona (se houver número)
        - Retorna Message(role, content) para o controller HTTP responder
        """
        # 1) Dispara o Flow
        kickoff_id = self._crewai_client.kickoff(body)

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

        # 5) Dispara WhatsApp (Evolution API) — usa o client existente
        persona = body.get("persona") or {}
        number = str(persona.get("cellphone", "")).strip()
        if number:
            self._whatsapp_client.send_text(number=number, text=assistant_message.content)

        return assistant_message
