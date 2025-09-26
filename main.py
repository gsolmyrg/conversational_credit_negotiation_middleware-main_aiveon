import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status

from models import DebtNegotiationRequestBody, WhatsappRequestBody
from services import MessageSubmissionService

load_dotenv()
app = FastAPI()
logger = logging.getLogger("uvicorn")


def verify_api_key(request: Request):
    auth_header = request.headers.get("Authorization")
    apikey = (
        auth_header.removeprefix("Bearer ").strip()
        if auth_header and auth_header.startswith("Bearer ")
        else None
    )
    expected_key = os.getenv("UVICORN_API_KEY")
    if apikey != expected_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid API key",
        )

    return apikey


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "ok"}


@app.post("/start-negotiation")
async def start_negotiation(
    body: DebtNegotiationRequestBody,
    api_key: str = Depends(verify_api_key),
):
    logger.info(f"Starting negotiation for request: {body.model_dump()}")

    try:
        message = MessageSubmissionService().kickoff_interaction(body)
        logger.info(
            f"Successfully completed negotiation kickoff. Message: {message.model_dump()}"
        )
    except Exception as e:
        logger.error(f"Error during negotiation kickoff: {str(e)}")
        raise


@app.post("/messages-upsert")
async def messages_upsert(
    body: WhatsappRequestBody,
    api_key: str = Depends(verify_api_key),
):
    logger.info(f"Handling WhatsApp interaction for request: {body.model_dump()}")

    try:
        message = MessageSubmissionService().handle_whatsapp_interaction(body)
        logger.info(
            f"Successfully completed WhatsApp interaction. Message: {message.model_dump()}"
        )
    except Exception as e:
        logger.error(f"Error during WhatsApp interaction: {str(e)}")
        raise


if __name__ == "__main__":
    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
