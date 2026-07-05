from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = os.getenv("SHOPSECURE_API_URL", "https://shopsecure-latest.onrender.com")


class ShopSecureError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        self.status = status
        super().__init__(message)


class ShopSecureClient:
    def __init__(self, token: str) -> None:
        self._token = token
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = await self._client.request(method, path, headers=self._headers(), **kwargs)
        if not resp.is_success:
            try:
                detail = resp.json().get("message") or resp.json().get("error") or resp.text
            except Exception:
                detail = resp.text
            raise ShopSecureError(str(detail), status=resp.status_code)
        if resp.status_code == 204:
            return None
        return resp.json()

    # ── Wallet ──
    async def get_wallet(self) -> dict[str, Any]:
        return await self._request("GET", "/api/wallet")

    # ── Products ──
    async def list_products(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/vendor/products")

    async def create_product(self, name: str, price: float, description: str = "",
                             stock: int = 0, category_id: int | None = None,
                             cost_price: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "price": price, "description": description, "stock": stock}
        if category_id is not None:
            body["categoryId"] = category_id
        if cost_price is not None:
            body["costPrice"] = cost_price
        return await self._request("POST", "/api/vendor/products", json=body)

    async def delete_product(self, product_id: int) -> None:
        await self._request("DELETE", f"/api/vendor/products/{product_id}")

    # ── Categories ──
    async def list_categories(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/categories")

    async def create_category(self, name: str, description: str = "") -> dict[str, Any]:
        return await self._request("POST", "/api/categories", json={"name": name, "description": description})

    # ── Orders ──
    async def list_pending_orders(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/vendor/business/businesses/orders/pending")

    async def list_order_history(self, page: int = 0) -> dict[str, Any]:
        return await self._request("GET", f"/orders/history?page={page}")

    # ── Checkout Links ──
    async def create_checkout_link_with_products(self, items: list[dict[str, int]],
                                                  discount: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"items": items}
        if discount is not None:
            body["discount"] = discount
        return await self._request("POST", "/api/vendor/checkout-links", json=body)

    async def create_checkout_link_custom(self, title: str, amount: float,
                                          description: str = "",
                                          discount: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"title": title, "amount": amount}
        if description:
            body["description"] = description
        if discount is not None:
            body["discount"] = discount
        return await self._request("POST", "/api/vendor/checkout-links", json=body)

    # ── Bank Account ──
    async def get_bank_account(self) -> dict[str, Any]:
        return await self._request("GET", "/api/vendor/bank-account")

    async def save_bank_account(self, account_number: str, bank_code: str, pin: str) -> dict[str, Any]:
        return await self._request("POST", "/api/vendor/bank-account", json={
            "accountNumber": account_number,
            "bankCode": bank_code,
            "pin": pin,
        })

    # ── Withdrawals ──
    async def create_withdrawal(self, amount: float, bank_account_id: int, pin: str) -> dict[str, Any]:
        return await self._request("POST", "/api/vendor/withdrawals", json={
            "amount": amount,
            "bankAccountId": bank_account_id,
            "pin": pin,
        })

    async def list_withdrawals(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/vendor/withdrawals")

    # ── Transactions ──
    async def list_transactions(self, page: int = 0) -> dict[str, Any]:
        return await self._request("GET", f"/api/payments/transactions?page={page}")

    # ── Sales ──
    async def list_sales(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/vendor/sales")

    async def create_sale(self, items: list[dict[str, int]], customer_name: str = "",
                          customer_phone: str = "", notes: str = "",
                          discount: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "items": items,
            "paymentMethod": "EXTERNAL_BANK",
        }
        if customer_name:
            body["customerName"] = customer_name
        if customer_phone:
            body["customerPhone"] = customer_phone
        if notes:
            body["notes"] = notes
        if discount is not None:
            body["discount"] = discount
        return await self._request("POST", "/api/vendor/sales", json=body)

    # ── Expenses ──
    async def list_expenses(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/vendor/expenses")

    async def create_expense(self, title: str, amount: float, description: str = "",
                             category: str = "", expense_date: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"title": title, "amount": amount}
        if description:
            body["description"] = description
        if category:
            body["category"] = category
        if expense_date:
            body["expenseDate"] = expense_date
        return await self._request("POST", "/api/vendor/expenses", json=body)

    # ── Reports ──
    async def get_dashboard_summary(self) -> dict[str, Any]:
        return await self._request("GET", "/api/vendor/reports/dashboard")

    async def get_profit_loss_report(self, start_date: str = "", end_date: str = "") -> dict[str, Any]:
        params = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._request("GET", "/api/vendor/reports/profit-loss", params=params)

    async def get_sales_report(self, start_date: str = "", end_date: str = "") -> dict[str, Any]:
        params = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._request("GET", "/api/vendor/reports/sales", params=params)

    async def get_expense_report(self, start_date: str = "", end_date: str = "") -> dict[str, Any]:
        params = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._request("GET", "/api/vendor/reports/expenses", params=params)

    # ── Receipts ──
    async def get_receipt(self, sale_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/api/vendor/receipts/{sale_id}")

    async def close(self) -> None:
        await self._client.aclose()
