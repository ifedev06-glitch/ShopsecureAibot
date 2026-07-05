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


async def send_typing_indicator(to: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "sender_action": "typing_on",
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, headers=headers)
        except Exception:
            pass


async def handle_message(phone: str, text: str) -> None:
    await send_typing_indicator(phone)
    token = await resolve_vendor_token(phone)

    if not token:
        await send_whatsapp(
            phone,
            "👋 Welcome to ShopSecure!\n\n"
            "Your WhatsApp isn't linked yet. Here's how to get started:\n\n"
            "1. Go to your ShopSecure dashboard\n"
            "2. Click *Connect your AI Assistant*\n"
            "3. Enter this phone number:\n\n"
            f"   {phone}\n\n"
            "Once linked, send me a message and I'll be ready to help!",
        )
        return

    QUICK_REPLIES = {
        "hello": "Hey there! 👋 How can I help you with your business today?",
        "hi": "Hey! What can I help you with?",
        "hey": "Hey! What can I help you with?",
        "good morning": "Good morning! ☀️ Ready to take care of business today?",
        "good evening": "Good evening! 🌆 What can I help you with?",
        "what can you do": "I'm your all-in-one business assistant. Here's what I can do for you:\n\n"
                          "📦 *Products* — Add, edit, search, and track stock levels\n"
                          "💰 *Wallet* — Check balance, withdraw to your bank\n"
                          "🧾 *Sales* — Record sales, send PDF receipts via WhatsApp\n"
                          "💸 *Expenses* — Log and categorise every expense\n"
                          "📊 *Reports* — Dashboard summary, P&L, sales & expense reports\n"
                          "🏦 *Bank* — Save and view your bank account details\n\n"
                          "Go ahead, tell me what you need — I'm ready!",
        "help": "Here's everything I can help you with:\n\n"
                "📦 *Products*\n"
                "  → Add, update, delete, search products\n\n"
                "🧾 *Sales*\n"
                "  → Record sales, view history, delete sales, get PDF receipts\n\n"
                "💸 *Expenses*\n"
                "  → Log, update, and delete business expenses\n\n"
                "📊 *Reports*\n"
                "  → Dashboard summary, P&L, sales report, expense report\n\n"
                "💰 *Finance*\n"
                "  → Check wallet, save bank account, withdraw, view transactions\n\n"
                "Just say something like \"add a product\" or \"show me my sales\" and I'll take care of it!",
    }

    if text.strip().lower() in QUICK_REPLIES:
        reply = QUICK_REPLIES[text.strip().lower()]
        session = sessions.get(phone, [])
        session.append({"role": "user", "content": text})
        session.append({"role": "assistant", "content": reply})
        sessions[phone] = session
        await send_whatsapp(phone, reply)
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
            data={"messaging_product": "whatsapp"},
            files={"file": (filename, pdf_bytes, "application/pdf")},
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
        f"Hello {business_name} 👋\n\n"
        f"I'm ShopSecure AI, your business assistant. I can help you manage products, "
        f"track sales, record expenses, run reports, and more — right here on WhatsApp.\n\n"
        f"Try saying \"what can you do\" or just tell me what you need help with."
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
