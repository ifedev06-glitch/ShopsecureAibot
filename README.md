# ShopSecure WhatsApp Bot

AI-powered WhatsApp bot that lets ShopSecure vendors manage their store via chat.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your .env values
```

## Run

```bash
python main.py
```

Bot runs at `http://localhost:8000`.

## Webhook Setup (Meta)

1. Deploy this app to a public URL (Render, Railway, Fly.io, etc.)
2. In Meta Developers > WhatsApp > Configuration, set:
   - **Callback URL**: `https://your-domain.com/webhook`
   - **Verify Token**: same as `META_WEBHOOK_VERIFY_TOKEN` in your `.env`
3. Subscribe to `messages` webhook field.

## How users log in

Users send `LOGIN <their_shopsecure_token>` on WhatsApp. The bot verifies the token with the ShopSecure API and stores it for future messages.

## Architecture

```
WhatsApp → Meta Cloud API → Webhook → FastAPI → OpenAI → ShopSecure API → Response
```

## Available commands (via AI)

- Wallet: "Show my balance"
- Products: "List products", "Add iPhone for 500k", "Delete product 3"
- Categories: "List categories", "Add category Electronics"
- Orders: "Show pending orders", "Order history"
- Create order: "Create order for John with iPhone 16" (uses products), "Create custom order for 5000"
- Bank: "Show my bank account"
- Withdrawals: "Show withdrawals"
- Transactions: "Show transactions"
