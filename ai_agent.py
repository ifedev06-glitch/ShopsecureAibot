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
            "name": "create_pin",
            "description": "Create a 4-digit transaction PIN for withdrawals",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {"type": "string", "description": "4-digit transaction PIN"},
                },
                "required": ["pin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_pin_status",
            "description": "Check if the vendor has a transaction PIN set",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_profile",
            "description": "Get the vendor's business profile details (name, description, phone, address)",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by name with pagination",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query (optional)"},
                    "page": {"type": "integer", "description": "Page number (0-based, optional)"},
                    "size": {"type": "integer", "description": "Results per page (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_sale",
            "description": "Delete a recorded sale and restore stock",
            "parameters": {
                "type": "object",
                "properties": {
                    "sale_id": {"type": "integer", "description": "The ID of the sale to delete"},
                },
                "required": ["sale_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_expense",
            "description": "Update an existing expense's details. Only send fields that need changing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {"type": "integer", "description": "The ID of the expense to update"},
                    "title": {"type": "string", "description": "New expense title (optional)"},
                    "amount": {"type": "number", "description": "New expense amount in NGN (optional)"},
                    "description": {"type": "string", "description": "New expense description (optional)"},
                    "category": {"type": "string", "description": "New expense category (optional)"},
                    "expense_date": {"type": "string", "description": "New date in YYYY-MM-DD format (optional)"},
                },
                "required": ["expense_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_expense",
            "description": "Delete an expense by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {"type": "integer", "description": "The ID of the expense to delete"},
                },
                "required": ["expense_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wallet",
            "description": "Get the vendor's wallet balance",
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
            "description": "Add a new product to the vendor's catalog with name, selling price, and cost price",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                    "price": {"type": "number", "description": "Selling price in NGN"},
                    "cost_price": {"type": "number", "description": "Cost price in NGN"},
                    "description": {"type": "string", "description": "Product description"},
                    "stock": {"type": "integer", "description": "Available stock quantity"},
                    "category_id": {"type": "integer", "description": "Category ID (optional)"},
                },
                "required": ["name", "price", "cost_price", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_product",
            "description": "Update an existing product's details (name, price, description, stock, category, or cost price). Only send fields that need changing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The ID of the product to update"},
                    "name": {"type": "string", "description": "New product name (optional)"},
                    "price": {"type": "number", "description": "New selling price in NGN (optional)"},
                    "description": {"type": "string", "description": "New product description (optional)"},
                    "stock": {"type": "integer", "description": "New stock quantity (optional)"},
                    "category_id": {"type": "integer", "description": "New category ID (optional)"},
                    "cost_price": {"type": "number", "description": "New cost price in NGN (optional)"},
                },
                "required": ["product_id"],
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
                    "discount": {"type": "number", "description": "Discount amount in NGN (optional)"},
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checkout_link_custom",
            "description": "Create a custom checkout link with a title and amount (not tied to existing products)",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the payment request"},
                    "amount": {"type": "number", "description": "Amount in NGN"},
                    "description": {"type": "string", "description": "Optional description"},
                    "discount": {"type": "number", "description": "Discount amount in NGN (optional)"},
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
            "name": "save_bank_account",
            "description": "Save or update the vendor's bank account details. The user must provide their transaction PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_number": {"type": "string", "description": "10-digit bank account number"},
                    "bank_code": {"type": "string", "description": "Bank code (e.g. '044' for Access Bank)"},
                    "pin": {"type": "string", "description": "4-digit transaction PIN"},
                },
                "required": ["account_number", "bank_code", "pin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_withdrawal",
            "description": "Initiate a withdrawal from the vendor's wallet to their saved bank account. The user must provide their transaction PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to withdraw in NGN"},
                    "bank_account_id": {"type": "integer", "description": "The ID of the saved bank account"},
                    "pin": {"type": "string", "description": "4-digit transaction PIN"},
                },
                "required": ["amount", "bank_account_id", "pin"],
            },
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
    {
        "type": "function",
        "function": {
            "name": "list_sales",
            "description": "List all recorded sales",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_sale",
            "description": "Record an offline sale (payment received outside the platform, e.g. bank transfer). Customers can optionally provide their name/phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of products and quantities sold",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productId": {"type": "integer", "description": "Product ID"},
                                "quantity": {"type": "integer", "description": "Quantity sold"},
                            },
                            "required": ["productId", "quantity"],
                        },
                    },
                    "customer_name": {"type": "string", "description": "Customer name (optional)"},
                    "customer_phone": {"type": "string", "description": "Customer phone (optional)"},
                    "notes": {"type": "string", "description": "Sale notes (optional)"},
                    "discount": {"type": "number", "description": "Discount amount in NGN (optional)"},
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_expenses",
            "description": "List all recorded expenses",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_expense",
            "description": "Record a business expense",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Expense title"},
                    "amount": {"type": "number", "description": "Expense amount in NGN"},
                    "description": {"type": "string", "description": "Expense description (optional)"},
                    "category": {"type": "string", "description": "Expense category (optional)"},
                    "expense_date": {"type": "string", "description": "Date of expense in YYYY-MM-DD format (optional)"},
                },
                "required": ["title", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get dashboard summary statistics (revenue, expenses, net profit, sales count, low stock items)",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_profit_loss_report",
            "description": "Get profit and loss report. Optionally specify a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_report",
            "description": "Get a detailed sales report. Optionally specify a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_report",
            "description": "Get a detailed expense report. Optionally specify a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_receipt",
            "description": "Get a receipt for a recorded sale by its sale ID. Returns a text receipt the vendor can share with the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sale_id": {"type": "integer", "description": "The ID of the sale to get the receipt for"},
                },
                "required": ["sale_id"],
            },
        },
    },
]

_SYSTEM = (
    "You are ShopSecure AI, an AI assistant for ShopSecure — a business management platform for Nigerian merchants.\n\n"
    "You help vendors manage their entire business via WhatsApp. You can do EVERYTHING the dashboard can do:\n\n"
    "Products:\n"
    "- Check wallet balance\n"
    "- List, add, update, delete, and search products (including cost price and stock)\n"
    "- List and create categories\n\n"
    "Sales:\n"
    "- View pending orders and order history\n"
    "- Create checkout links (with products or custom amounts, with optional discounts)\n"
    "- Record offline sales (bank transfers)\n"
    "- List and delete recorded sales\n"
    "- Get a text receipt or PDF receipt for any sale\n\n"
    "Expenses:\n"
    "- List, add, update, and delete expenses\n\n"
    "Reports & Analytics:\n"
    "- Dashboard summary (revenue, expenses, profit, sales count, low stock)\n"
    "- Profit & Loss report\n"
    "- Sales report (top products, by payment method)\n"
    "- Expense report (by category)\n\n"
    "Finance:\n"
    "- View and save bank account details\n"
    "- Create and check transaction PIN status\n"
    "- Initiate withdrawals (requires transaction PIN)\n"
    "- List withdrawal history\n"
    "- View transaction history\n\n"
    "Business Profile:\n"
    "- View business profile details (name, description, phone, address)\n\n"
    "Behaviours:\n"
    "- Respond in a friendly, concise way. Use simple emojis occasionally.\n"
    "- When creating orders with products, FIRST call list_products or search_products to find the right product IDs.\n"
    "- When listing products, if the list is long show a summary and ask which one.\n"
    "- Return checkout URLs to the user after creating a link.\n"
    "- For sensitive actions (withdrawal, save bank account, PIN creation), ask the user for their 4-digit transaction PIN.\n"
    "- Do NOT make up information. If you need more details, ask.\n"
    "- When recording a sale, look up the product's listed price first. If the customer paid less than the listed price, calculate the difference as a discount and pass it to create_sale. For example if a product costs ₦500,000 and the user says they sold it for ₦490,000, then discount = 10,000.\n"
    "- When the user asks about 'today', 'this week', 'this month', or anything date-related, use today's date provided above to calculate the correct date range.\n"
)


async def run_agent(
    session: list[dict[str, str]],
    api_call_fn: Callable,
    max_turns: int = 5,
) -> str:
    from datetime import date
    today = date.today()
    system_with_date = f"Today's date is {today.isoformat()} ({today.strftime('%A')}).\n\n{_SYSTEM}"
    session.append({"role": "system", "content": system_with_date})

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
