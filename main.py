from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from agent_adapter import AgentAdapter
from ai_agent import run_agent
from shopsecure_api import BASE_URL, ShopSecureClient

load_dotenv()

META_TOKEN = os.getenv("META_USER_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_WA_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")

# phone_number -> shopsecure_token  (in-memory cache; use Redis for production)
auth_cache: dict[str, str] = {}
# phone_number -> conversation history
sessions: dict[str, list[dict[str, str]]] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="ShopSecure WhatsApp Bot", lifespan=lifespan)


# ── Webhook verification (Meta requires this) ──

@app.get("/webhook")
async def webhook_verify(request: Request) -> PlainTextResponse:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)


# ── Incoming WhatsApp messages ──

@app.post("/webhook")
async def webhook_handler(body: dict[str, Any]) -> PlainTextResponse:
    entry = body.get("entry", [])
    for ent in entry:
        changes = ent.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                if msg.get("type") == "text":
                    from_number = msg["from"]
                    text = msg["text"]["body"]
                    await handle_message(from_number, text)
    return PlainTextResponse("OK")


async def resolve_vendor_token(phone: str) -> str | None:
    token = auth_cache.get(phone)
    if token:
        return token

    url = f"{BASE_URL}/api/public/whatsapp-link/{phone}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.is_success:
                data = resp.json()
                token = data.get("token")
                if token:
                    auth_cache[phone] = token
                    return token
        except Exception:
            pass
    return None


async def handle_message(phone: str, text: str) -> None:
    token = await resolve_vendor_token(phone)

    if not token:
        await send_whatsapp(
            phone,
            "👋 Welcome to ShopSecure!\n\n"
            "Your WhatsApp number isn't linked yet.\n\n"
            "Go to your ShopSecure dashboard → Link WhatsApp and enter this number:\n"
            f"{phone}\n\n"
            "Once linked, message me again and I'll help you manage your store!",
        )
        return

    if phone not in sessions:
        sessions[phone] = []

    session = sessions[phone]
    session.append({"role": "user", "content": text})

    client = ShopSecureClient(token)
    adapter = AgentAdapter(client, phone, send_document)

    try:
        reply = await run_agent(session, adapter)
        await send_whatsapp(phone, reply)
    except Exception as e:
        await send_whatsapp(phone, f"Sorry, something went wrong: {e}")
    finally:
        await client.close()


# ── WhatsApp send helper ──

async def send_whatsapp(to: str, text: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)


# ── WhatsApp document send helper ──

async def send_document(to: str, pdf_bytes: bytes, filename: str) -> None:
    print(f"send_document: uploading {len(pdf_bytes)} bytes to Meta...")
    upload_url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {META_TOKEN}"}
    async with httpx.AsyncClient() as client:
        upload_resp = await client.post(
            upload_url, headers=headers,
            files=[
                ("messaging_product", "whatsapp"),
                ("file", (filename, pdf_bytes, "application/pdf")),
            ],
        )
        body = upload_resp.json()
        print(f"send_document: upload status={upload_resp.status_code}, body={body}")
        if not upload_resp.is_success or "id" not in body:
            raise RuntimeError(f"Upload failed ({upload_resp.status_code}): {body}")
        media_id = body["id"]
        print(f"send_document: upload OK, media_id={media_id}")

    print("send_document: sending document message...")
    msg_url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {"id": media_id, "filename": filename},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(msg_url, json=payload, headers=headers)
        body = resp.json()
        print(f"send_document: send status={resp.status_code}, body={body}")
        if not resp.is_success:
            raise RuntimeError(f"Send failed ({resp.status_code}): {body}")
    print("send_document: DONE")


# ── Send welcome message (called by backend after linking) ──

@app.post("/send-welcome")
async def send_welcome(payload: dict[str, str]) -> dict[str, str]:
    phone = payload.get("phone_number", "")
    business_name = payload.get("business_name", "")
    if not phone:
        return {"status": "error", "message": "phone_number is required"}
    message = (
        f"Hey {business_name}, I am ShopSecure AI, your AI-powered assistant. "
        f"Kindly save me!"
    )
    await send_whatsapp(phone, message)
    return {"status": "ok"}


# ── Health check ──

@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "app": "ShopSecure WhatsApp Bot"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
