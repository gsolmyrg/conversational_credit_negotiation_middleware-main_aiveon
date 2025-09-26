# -*- coding: utf-8 -*-
import os
import json
import uuid
from uuid import uuid5, NAMESPACE_URL

from .clients.crewai_client import CrewaiClient
from .clients.whatsapp_client import WhatsappClient
from .models import Message, WhatsappRequestBody  # ajuste conforme seus modelos reais


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
        - (Envio ao WhatsApp, quando aplicável, deve usar o mesmo 'content')
        """
        # 1) Dispara o Flow
        kickoff_id = self._crewai_client.kickoff(body)

        # 2) Polling até obter o resultado
        result_raw = self._crewai_client.status(kickoff_id)

        # 3) Robustez: se vier string JSON, desserializa;
        #    se já vier dict, mantém; se vier outra coisa, tenta converter.
        if isinstance(result_raw, str):
            try:
                result_json = json.loads(result_raw)
            except json.JSONDecodeError:
                raise RuntimeError(f"Resultado do CrewAI não é JSON válido: {result_raw[:200]}...")
        elif isinstance(result_raw, dict):
            result_json = result_raw
        else:
            # Em caso muito raro
            raise RuntimeError(f"Formato inesperado de resultado do CrewAI: {type(result_raw)}")

        # 4) Extrai a última mensagem do histórico (contrato preservado)
        #    Esperamos: result_json["history"] = [ {role, content}, ... ]
        history = result_json.get("history")
        if not isinstance(history, list) or not history:
            raise RuntimeError("Resultado do CrewAI não contém 'history' com itens.")

        last_msg = history[-1]
        if not isinstance(last_msg, dict) or "role" not in last_msg or "content" not in last_msg:
            raise RuntimeError("Último item do 'history' não está no formato {role, content}.")

        assistant_message = Message(**last_msg)

        # 5) (Opcional) Disparo via WhatsApp — se você quiser enviar automaticamente aqui
        #    Ajuste conforme seu fluxo (algumas implantações só retornam a resposta HTTP).
        #
        # persona = body.get("persona") or {}
        # number = str(persona.get("cellphone", "")).strip()
        # if number:
        #     self._whatsapp_client.send_text(number=number, text=assistant_message.content)

        return assistant_message


# (opcional) outro serviço que acione via webhook do Evolution API
class WhatsappWebhookService:
    def __init__(self):
        self._crewai_client = CrewaiClient()
        self._whatsapp_client = WhatsappClient()

    def handle_inbound(self, body: WhatsappRequestBody) -> None:
        """
        Exemplo de como tratar inbound:
        - Ignorar mensagens sem 'conversation' (texto do usuário)
        - Ignorar fromMe:true, statuses etc. (já deve estar no seu handler)
        - Montar payload mínimo e acionar kickoff/status como acima
        """
        # este método é ilustrativo; adapte ao seu main.py do middleware se desejar
        pass
