from __future__ import annotations

from typing import Any

from shopsecure_api import ShopSecureClient


class AgentAdapter:
    """Maps AI function names to ShopSecure API calls.

    Each method name matches the "name" field in the AI tool definitions.
    """

    def __init__(self, api: ShopSecureClient) -> None:
        self._api = api

    # ── Wallet ──

    async def get_wallet(self) -> str:
        data = await self._api.get_wallet()
        avail = data.get("availableBalance", "0")
        proc = data.get("processingBalance", "0")
        return f"Wallet: available ₦{avail}, processing ₦{proc}"

    # ── Products ──

    async def list_products(self) -> str:
        products = await self._api.list_products()
        if not products:
            return "No products in your catalog yet."
        lines = [f"{p['id']}. {p['name']} - ₦{p['price']} (stock: {p.get('stock', 0)})" for p in products]
        return "Your products:\n" + "\n".join(lines)

    async def create_product(self, name: str, price: float, description: str = "", stock: int = 0) -> str:
        data = await self._api.create_product(name, price, description, stock)
        return f"✅ Product '{name}' added at ₦{price}."

    async def delete_product(self, product_id: int) -> str:
        await self._api.delete_product(product_id)
        return f"🗑️ Product {product_id} deleted."

    # ── Categories ──

    async def list_categories(self) -> str:
        cats = await self._api.list_categories()
        if not cats:
            return "No categories yet."
        lines = [f"{c['id']}. {c['name']}" for c in cats]
        return "Categories:\n" + "\n".join(lines)

    async def create_category(self, name: str, description: str = "") -> str:
        data = await self._api.create_category(name, description)
        return f"✅ Category '{name}' created."

    # ── Orders ──

    async def list_pending_orders(self) -> str:
        orders = await self._api.list_pending_orders()
        if not orders:
            return "No pending orders."
        lines = []
        for o in orders:
            lines.append(f"Order #{o.get('orderId', o.get('id'))} - ₦{o.get('totalAmount', 0)}")
        return "Pending orders:\n" + "\n".join(lines)

    async def list_order_history(self, page: int = 0) -> str:
        data = await self._api.list_order_history(page)
        orders = data.get("content", [])
        if not orders:
            return "No order history."
        lines = []
        for o in orders:
            status = o.get("status", "N/A")
            lines.append(f"Order #{o.get('orderId', o.get('id'))} - {status} - ₦{o.get('totalAmount', 0)}")
        return "Order history:\n" + "\n".join(lines)

    # ── Checkout Links ──

    async def create_checkout_link_with_products(self, items: list[dict]) -> str:
        data = await self._api.create_checkout_link_with_products(items)
        url = data.get("checkoutUrl", data.get("checkout_url", ""))
        total = data.get("totalAmount", data.get("total_amount", ""))
        return f"✅ Order link created! Share with your customer:\n{url}\nTotal: ₦{total}"

    async def create_checkout_link_custom(self, title: str, amount: float, description: str = "") -> str:
        data = await self._api.create_checkout_link_custom(title, amount, description)
        url = data.get("checkoutUrl", data.get("checkout_url", ""))
        total = data.get("totalAmount", data.get("total_amount", ""))
        return f"✅ Custom payment link created!\n{url}\n{title}: ₦{total}"

    # ── Bank / Withdrawals / Transactions ──

    async def get_bank_account(self) -> str:
        data = await self._api.get_bank_account()
        if not data or not data.get("accountNumber"):
            return "No bank account saved yet."
        return (f"Bank: {data.get('bankName', 'N/A')} - "
                f"{data.get('accountNumber', 'N/A')} ({data.get('accountName', 'N/A')})")

    async def list_withdrawals(self) -> str:
        withdrawals = await self._api.list_withdrawals()
        if not withdrawals:
            return "No withdrawals yet."
        lines = [f"₦{w['amount']} - {w.get('status', 'N/A')} - {w.get('createdAt', '')[:10]}"
                 for w in withdrawals]
        return "Withdrawals:\n" + "\n".join(lines)

    async def list_transactions(self, page: int = 0) -> str:
        data = await self._api.list_transactions(page)
        txns = data.get("content", [])
        if not txns:
            return "No transactions yet."
        lines = []
        for t in txns:
            lines.append(f"₦{t.get('amount', 0)} - {t.get('status', 'N/A')} - {t.get('createdAt', '')[:10]}")
        return "Transactions:\n" + "\n".join(lines)
