from __future__ import annotations

import json
import os
from typing import Any, Callable

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_FUNCTION_DECLARATIONS: list[types.FunctionDeclaration] = [
    types.FunctionDeclaration(
        name="get_wallet",
        description="Get the vendor's wallet balance (available & processing)",
    ),
    types.FunctionDeclaration(
        name="list_products",
        description="List all products in the vendor's catalog",
    ),
    types.FunctionDeclaration(
        name="create_product",
        description="Add a new product to the vendor's catalog",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "name": types.Schema(type=types.Type.STRING, description="Product name"),
                "price": types.Schema(type=types.Type.NUMBER, description="Product price in NGN"),
                "description": types.Schema(type=types.Type.STRING, description="Product description"),
                "stock": types.Schema(type=types.Type.INTEGER, description="Available stock quantity"),
            },
            required=["name", "price"],
        ),
    ),
    types.FunctionDeclaration(
        name="delete_product",
        description="Delete a product from the vendor's catalog by its ID",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "product_id": types.Schema(type=types.Type.INTEGER, description="The ID of the product to delete"),
            },
            required=["product_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_categories",
        description="List all store categories",
    ),
    types.FunctionDeclaration(
        name="create_category",
        description="Create a new category",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "name": types.Schema(type=types.Type.STRING, description="Category name"),
                "description": types.Schema(type=types.Type.STRING, description="Category description"),
            },
            required=["name"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_pending_orders",
        description="List all pending orders",
    ),
    types.FunctionDeclaration(
        name="list_order_history",
        description="List past order history",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "page": types.Schema(type=types.Type.INTEGER, description="Page number (0-based)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="create_checkout_link_with_products",
        description="Create a checkout link using existing products from the vendor's catalog. The link can be shared with a customer to complete payment.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "items": types.Schema(
                    type=types.Type.ARRAY,
                    description="List of products and quantities",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "productId": types.Schema(type=types.Type.INTEGER, description="Product ID"),
                            "quantity": types.Schema(type=types.Type.INTEGER, description="Quantity"),
                        },
                        required=["productId", "quantity"],
                    ),
                ),
            },
            required=["items"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_checkout_link_custom",
        description="Create a custom checkout link with a title and amount (not tied to existing products). Use this when the user wants a payment link for a custom item or amount.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title": types.Schema(type=types.Type.STRING, description="Title of the payment request"),
                "amount": types.Schema(type=types.Type.NUMBER, description="Amount in NGN"),
                "description": types.Schema(type=types.Type.STRING, description="Optional description"),
            },
            required=["title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_bank_account",
        description="Get the vendor's saved bank account details",
    ),
    types.FunctionDeclaration(
        name="list_withdrawals",
        description="List withdrawal history",
    ),
    types.FunctionDeclaration(
        name="list_transactions",
        description="List payment transactions history",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "page": types.Schema(type=types.Type.INTEGER, description="Page number (0-based)"),
            },
        ),
    ),
]

_TOOL = types.Tool(function_declarations=_FUNCTION_DECLARATIONS)

_SYSTEM_INSTRUCTION = (
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

MODEL = "gemini-2.0-flash"


def _to_gemini_contents(session: list[dict[str, str]]) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in session:
        role = msg.get("role", "user")
        role = "model" if role == "assistant" else "user" if role == "user" else role
        parts = [types.Part(text=msg.get("content", ""))]
        contents.append(types.Content(role=role, parts=parts))
    return contents


async def run_agent(
    session: list[dict[str, str]],
    api_call_fn: Callable,
    max_turns: int = 5,
) -> str:
    for _ in range(max_turns):
        contents = _to_gemini_contents(session)

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                tools=[_TOOL],
            ),
        )

        candidate = response.candidates[0]
        reply_content = candidate.content

        has_function_call = any(part.function_call for part in reply_content.parts)

        if not has_function_call:
            text = "".join(part.text or "" for part in reply_content.parts)
            session.append({"role": "assistant", "content": text})
            return text

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": ""}
        tool_responses: list[dict[str, Any]] = []

        for part in reply_content.parts:
            if part.text:
                assistant_msg["content"] += part.text

            fc = part.function_call
            if fc is None:
                continue

            fn_name = fc.name
            args = {k: v for k, v in fc.args.items()}

            fn = getattr(api_call_fn, fn_name, None)
            if fn is None:
                result = {"error": f"Unknown function: {fn_name}"}
            else:
                try:
                    result = await fn(**args)
                except Exception as e:
                    result = {"error": str(e)}

            result_str = json.dumps(result, default=str) if not isinstance(result, str) else result

            tool_responses.append({
                "role": "function",
                "name": fn_name,
                "content": result_str,
            })

        session.append(assistant_msg)
        session.extend(tool_responses)

    return "I'm sorry, I couldn't complete that request. Please try again."
