from __future__ import annotations

import json
import os
from typing import Any, Callable

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_wallet",
            "description": "Get the vendor's wallet balance (available & processing)",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List all products in the vendor's catalog",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": "Add a new product to the vendor's catalog",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                    "price": {"type": "number", "description": "Product price in NGN"},
                    "description": {"type": "string", "description": "Product description"},
                    "stock": {"type": "integer", "description": "Available stock quantity"},
                },
                "required": ["name", "price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_product",
            "description": "Delete a product from the vendor's catalog by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "The ID of the product to delete",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "List all store categories",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_category",
            "description": "Create a new category",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Category name"},
                    "description": {"type": "string", "description": "Category description"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_orders",
            "description": "List all pending orders",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_order_history",
            "description": "List past order history",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number (0-based)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checkout_link_with_products",
            "description": "Create a checkout link using existing products from the vendor's catalog. The link can be shared with a customer to complete payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of products and quantities",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productId": {"type": "integer", "description": "Product ID"},
                                "quantity": {"type": "integer", "description": "Quantity"},
                            },
                            "required": ["productId", "quantity"],
                        },
                    },
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checkout_link_custom",
            "description": "Create a custom checkout link with a title and amount (not tied to existing products). Use this when the user wants a payment link for a custom item or amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the payment request"},
                    "amount": {"type": "number", "description": "Amount in NGN"},
                    "description": {"type": "string", "description": "Optional description"},
                },
                "required": ["title", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bank_account",
            "description": "Get the vendor's saved bank account details",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_withdrawals",
            "description": "List withdrawal history",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_transactions",
            "description": "List payment transactions history",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number (0-based)"},
                },
            },
        },
    },
]

_SYSTEM = (
    "You are an AI assistant for ShopSecure, a Nigerian e-commerce platform.\n\n"
    "You help vendors manage their store via WhatsApp. You can:\n"
    "- Check wallet balance\n"
    "- List, add, and delete products\n"
    "- List and create categories\n"
    "- View pending orders and order history\n"
    "- Create checkout links (with existing products or custom amounts)\n"
    "- View bank account, withdrawals, and transactions\n\n"
    "Behaviours:\n"
    "- Respond in a friendly, concise way.\n"
    "- When creating orders with products, FIRST call list_products to find the right product IDs, then call the create function.\n"
    "- If listing products and the list is long, show a summary and ask which one.\n"
    "- Return the checkout URL to the user after creating an order link.\n"
    "- Use simple emojis occasionally to keep it conversational.\n"
    "- Do NOT make up information. If you need more details from the user, ask.\n"
    "- Do NOT handle sensitive actions like withdrawals or PIN creation via the bot - redirect those to the dashboard.\n"
)


async def run_agent(
    session: list[dict[str, str]],
    api_call_fn: Callable,
    max_turns: int = 5,
) -> str:
    session.append({"role": "system", "content": _SYSTEM})

    for _ in range(max_turns):
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=session,
            tools=_TOOLS,
            tool_choice="auto",
        )

        msg = completion.choices[0].message

        if not msg.tool_calls:
            session.append({"role": "assistant", "content": msg.content or ""})
            return msg.content or ""

        session.append(msg.model_dump(exclude={"function_call"}))

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            fn = getattr(api_call_fn, fn_name, None)
            if fn is None:
                result = {"error": f"Unknown function: {fn_name}"}
            else:
                try:
                    result = await fn(**args)
                except Exception as e:
                    result = {"error": str(e)}

            result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
            session.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    return "I'm sorry, I couldn't complete that request. Please try again."
