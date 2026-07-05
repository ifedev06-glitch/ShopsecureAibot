from __future__ import annotations

from typing import Any

from shopsecure_api import ShopSecureClient


class AgentAdapter:
    """Maps AI function names to ShopSecure API calls."""

    def __init__(self, api: ShopSecureClient, phone: str = "",
                 send_document_fn: Any | None = None) -> None:
        self._api = api
        self._phone = phone
        self._send_document = send_document_fn

    # ── Wallet ──

    async def get_wallet(self) -> str:
        data = await self._api.get_wallet()
        balance = data.get("balance", "0")
        return f"Wallet balance: ₦{balance}"

    # ── Products ──

    async def list_products(self) -> str:
        products = await self._api.list_products()
        if not products:
            return "No products in your catalog yet."
        lines = [f"{p['id']}. {p['name']} - ₦{p['price']} (stock: {p.get('stock', 0)})" for p in products]
        return "Your products:\n" + "\n".join(lines)

    async def create_product(self, name: str, price: float, description: str = "",
                             stock: int = 0, category_id: int | None = None,
                             cost_price: float | None = None) -> str:
        data = await self._api.create_product(name, price, description, stock,
                                               category_id, cost_price)
        return f"✅ Product '{name}' added at ₦{price}."

    async def update_product(self, product_id: int, name: str | None = None,
                              price: float | None = None, description: str | None = None,
                              stock: int | None = None, category_id: int | None = None,
                              cost_price: float | None = None) -> str:
        data = await self._api.update_product(product_id, name, price, description,
                                                stock, category_id, cost_price)
        updated = []
        if name is not None:
            updated.append(f"name={name}")
        if price is not None:
            updated.append(f"price=₦{price}")
        if description is not None:
            updated.append("description updated")
        if stock is not None:
            updated.append(f"stock={stock}")
        if cost_price is not None:
            updated.append(f"cost_price=₦{cost_price}")
        return f"✅ Product {product_id} updated ({', '.join(updated)})."

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

    async def create_checkout_link_with_products(self, items: list[dict],
                                                  discount: float | None = None) -> str:
        data = await self._api.create_checkout_link_with_products(items, discount)
        url = data.get("checkoutUrl", data.get("checkout_url", ""))
        total = data.get("totalAmount", data.get("total_amount", ""))
        return f"✅ Order link created! Share with your customer:\n{url}\nTotal: ₦{total}"

    async def create_checkout_link_custom(self, title: str, amount: float,
                                           description: str = "",
                                           discount: float | None = None) -> str:
        data = await self._api.create_checkout_link_custom(title, amount, description, discount)
        url = data.get("checkoutUrl", data.get("checkout_url", ""))
        total = data.get("totalAmount", data.get("total_amount", ""))
        return f"✅ Custom payment link created!\n{url}\n{title}: ₦{total}"

    # ── Bank Account ──

    async def get_bank_account(self) -> str:
        data = await self._api.get_bank_account()
        if not data or not data.get("accountNumber"):
            return "No bank account saved yet."
        return (f"Bank: {data.get('bankName', 'N/A')} - "
                f"{data.get('accountNumber', 'N/A')} ({data.get('accountName', 'N/A')})")

    async def save_bank_account(self, account_number: str, bank_code: str, pin: str) -> str:
        data = await self._api.save_bank_account(account_number, bank_code, pin)
        return (f"✅ Bank account saved: {data.get('bankName', 'N/A')} - "
                f"{data.get('accountNumber', 'N/A')} ({data.get('accountName', 'N/A')})")

    # ── PIN ──

    async def create_pin(self, pin: str) -> str:
        data = await self._api.create_pin(pin)
        return "✅ Transaction PIN created successfully."

    async def check_pin_status(self) -> str:
        data = await self._api.check_pin_status()
        has_pin = data.get("hasPin", False)
        return f"PIN status: {'✅ Set' if has_pin else '❌ Not set'}. You need a PIN to withdraw funds."

    # ── Business Profile ──

    async def get_business_profile(self) -> str:
        data = await self._api.get_business_profile()
        return (
            f"🏪 {data.get('businessName', 'N/A')}\n"
            f"{data.get('description', 'No description')}\n"
            f"📞 {data.get('phoneNumber', 'Not set')} | 📍 {data.get('address', 'Not set')}"
        )

    # ── Sales (additional) ──

    async def delete_sale(self, sale_id: int) -> str:
        await self._api.delete_sale(sale_id)
        return f"🗑️ Sale {sale_id} deleted. Stock restored."

    # ── Products (additional) ──

    async def search_products(self, q: str = "", page: int = 0, size: int = 10) -> str:
        data = await self._api.search_products(q, page, size)
        products = data.get("content", [])
        total = data.get("totalElements", 0)
        if not products:
            return "No products found."
        lines = [f"{p['id']}. {p['name']} - ₦{p['price']} (stock: {p.get('stock', 0)})" for p in products]
        return f"Found {total} products:\n" + "\n".join(lines)

    # ── Expenses (additional) ──

    async def update_expense(self, expense_id: int, title: str | None = None,
                              amount: float | None = None, description: str | None = None,
                              category: str | None = None,
                              expense_date: str | None = None) -> str:
        data = await self._api.update_expense(expense_id, title, amount, description,
                                               category, expense_date)
        updated = []
        if title is not None:
            updated.append(f"title={title}")
        if amount is not None:
            updated.append(f"amount=₦{amount}")
        if description is not None:
            updated.append("description updated")
        if category is not None:
            updated.append(f"category={category}")
        if expense_date is not None:
            updated.append(f"date={expense_date}")
        return f"✅ Expense {expense_id} updated ({', '.join(updated)})."

    async def delete_expense(self, expense_id: int) -> str:
        await self._api.delete_expense(expense_id)
        return f"🗑️ Expense {expense_id} deleted."

    # ── Withdrawals ──

    async def create_withdrawal(self, amount: float, bank_account_id: int, pin: str) -> str:
        data = await self._api.create_withdrawal(amount, bank_account_id, pin)
        return f"✅ Withdrawal of ₦{amount} initiated successfully."

    async def list_withdrawals(self) -> str:
        withdrawals = await self._api.list_withdrawals()
        if not withdrawals:
            return "No withdrawals yet."
        lines = [f"₦{w['amount']} - {w.get('status', 'N/A')} - {w.get('createdAt', '')[:10]}"
                 for w in withdrawals]
        return "Withdrawals:\n" + "\n".join(lines)

    # ── Transactions ──

    async def list_transactions(self, page: int = 0) -> str:
        data = await self._api.list_transactions(page)
        txns = data.get("content", [])
        if not txns:
            return "No transactions yet."
        lines = []
        for t in txns:
            lines.append(f"₦{t.get('amount', 0)} - {t.get('status', 'N/A')} - {t.get('createdAt', '')[:10]}")
        return "Transactions:\n" + "\n".join(lines)

    # ── Sales ──

    async def list_sales(self) -> str:
        sales = await self._api.list_sales()
        if not sales:
            return "No sales recorded yet."
        lines = []
        for s in sales:
            items_info = ", ".join(
                f"{i.get('productName', '?')} ×{i.get('quantity', 0)}"
                for i in s.get("items", [])
            )
            lines.append(
                f"{s['saleNumber']} - ₦{s['totalAmount']} - {s.get('paymentMethod', 'N/A')}"
                f"{' - ' + items_info if items_info else ''}"
            )
        return "Recent sales:\n" + "\n".join(lines)

    async def create_sale(self, items: list[dict], customer_name: str = "",
                          customer_phone: str = "", notes: str = "",
                          discount: float | None = None) -> str:
        print("=== create_sale START ===")
        data = await self._api.create_sale(items, customer_name, customer_phone,
                                            notes, discount)
        sale_id = data.get("id")
        total = data.get("totalAmount", 0)
        number = data.get("saleNumber", "")
        print(f"create_sale: sale_id={sale_id}, number={number}, total={total}")

        # Build text receipt from general receipt data
        print(f"create_sale: fetching receipt for sale_id={sale_id}")
        try:
            receipt = await self._api.get_receipt(sale_id)
            print(f"create_sale: receipt received")
        except Exception as e:
            print(f"create_sale: get_receipt FAILED: {e}")
            return f"✅ Sale {number} recorded for ₦{total}. Stock updated.\n\n⚠️ Could not generate receipt: {e}"

        receipt_lines = [
            f"🧾 RECEIPT {receipt['receiptNumber']}",
            f"🏪 {receipt['businessName']}",
            f"📅 {receipt['createdAt'][:10]}",
        ]
        if receipt.get("customerName"):
            receipt_lines.append(f"👤 {receipt['customerName']}")
        receipt_lines.append("")
        for item in receipt.get("items", []):
            receipt_lines.append(f"  {item['productName']} ×{item['quantity']}")
            receipt_lines.append(f"  ₦{float(item['unitPrice']):,.2f} ea → ₦{float(item['total']):,.2f}")
        receipt_lines.append("")
        receipt_lines.append(f"  Subtotal          ₦{float(receipt['subtotal']):,.2f}")
        if receipt.get("discount") and float(receipt["discount"]) > 0:
            receipt_lines.append(f"  Discount         -₦{float(receipt['discount']):,.2f}")
        receipt_lines.append(f"  TOTAL             ₦{float(receipt['total']):,.2f}")
        receipt_lines.append(f"  {receipt['paymentMethod']}")
        text_receipt = "\n".join(receipt_lines)

        # Try sending PDF receipt via backend-generated PDF
        if self._send_document and self._phone:
            try:
                print("create_sale: downloading PDF from backend...")
                pdf_bytes = await self._api.get_receipt_pdf(sale_id)
                print(f"create_sale: PDF downloaded, size={len(pdf_bytes)} bytes")
                print(f"create_sale: sending document to {self._phone}")
                await self._send_document(self._phone, pdf_bytes, f"receipt-{number}.pdf")
                print("create_sale: document sent successfully")
                return f"✅ Sale {number} recorded for ₦{total}. Stock updated.\n📎 PDF receipt sent!"
            except Exception as e:
                print(f"create_sale: PDF send FAILED: {e}")
                return f"✅ Sale {number} recorded for ₦{total}. Stock updated.\n\n⚠️ PDF send failed: {e}\n\n{text_receipt}"

        print("create_sale: no send_document function, returning text receipt")
        return f"✅ Sale {number} recorded for ₦{total}. Stock updated.\n\n{text_receipt}"

    # ── Expenses ──

    async def list_expenses(self) -> str:
        expenses = await self._api.list_expenses()
        if not expenses:
            return "No expenses recorded yet."
        lines = [f"₦{e['amount']} - {e.get('title', '')} - {e.get('category', 'N/A')} - {e.get('createdAt', '')[:10]}"
                 for e in expenses]
        return "Expenses:\n" + "\n".join(lines)

    async def create_expense(self, title: str, amount: float, description: str = "",
                             category: str = "", expense_date: str = "") -> str:
        data = await self._api.create_expense(title, amount, description, category, expense_date)
        return f"✅ Expense '{title}' of ₦{amount} recorded."

    # ── Reports ──

    async def get_dashboard_summary(self) -> str:
        data = await self._api.get_dashboard_summary()
        return (
            f"📊 Dashboard Summary\n"
            f"Revenue: ₦{data.get('totalRevenue', 0)}\n"
            f"Expenses: ₦{data.get('totalExpenses', 0)}\n"
            f"Net Profit: ₦{data.get('netProfit', 0)}\n"
            f"Sales Count: {data.get('totalSalesCount', 0)}\n"
            f"Low Stock Items: {data.get('lowStockCount', 0)}"
        )

    async def get_profit_loss_report(self, start_date: str = "", end_date: str = "") -> str:
        data = await self._api.get_profit_loss_report(start_date, end_date)
        period = f"{data.get('startDate', 'start')} to {data.get('endDate', 'end')}"
        return (
            f"📈 Profit & Loss ({period})\n"
            f"Revenue: ₦{data.get('totalRevenue', 0)}\n"
            f"COGS: ₦{data.get('totalCostOfGoodsSold', 0)}\n"
            f"Gross Profit: ₦{data.get('grossProfit', 0)}\n"
            f"Expenses: ₦{data.get('totalExpenses', 0)}\n"
            f"Net Profit: ₦{data.get('netProfit', 0)}"
        )

    async def get_sales_report(self, start_date: str = "", end_date: str = "") -> str:
        data = await self._api.get_sales_report(start_date, end_date)
        lines = [f"📦 Sales Report ({data.get('startDate', 'start')} to {data.get('endDate', 'end')})"]
        lines.append(f"Total Sales: {data.get('totalSales', 0)}")
        lines.append(f"Total Revenue: ₦{data.get('totalRevenue', 0)}")
        top = data.get("topProducts", [])
        if top:
            lines.append("\nTop Products:")
            for p in top[:5]:
                lines.append(f"  {p.get('productName', '?')} - {p.get('quantitySold', 0)} sold - ₦{p.get('revenue', 0)}")
        pm = data.get("salesByPaymentMethod", {})
        if pm:
            lines.append("\nBy Payment Method:")
            for method, count in pm.items():
                lines.append(f"  {method}: {count}")
        return "\n".join(lines)

    async def get_expense_report(self, start_date: str = "", end_date: str = "") -> str:
        data = await self._api.get_expense_report(start_date, end_date)
        lines = [f"📉 Expense Report ({data.get('startDate', 'start')} to {data.get('endDate', 'end')})"]
        lines.append(f"Total Entries: {data.get('totalExpenses', 0)}")
        lines.append(f"Total Amount: ₦{data.get('totalAmount', 0)}")
        cats = data.get("byCategory", {})
        if cats:
            lines.append("\nBy Category:")
            for cat, info in sorted(cats.items(), key=lambda x: x[1]["total"], reverse=True):
                lines.append(f"  {cat}: ₦{info['total']} ({info['count']} entries)")
        return "\n".join(lines)

    # ── Receipts ──

    async def get_receipt(self, sale_id: int) -> str:
        data = await self._api.get_receipt(sale_id)
        lines = [f"🧾 Receipt: {data.get('saleNumber', 'N/A')}"]
        lines.append(f"Date: {data.get('createdAt', '')[:10]}")
        if data.get("customerName"):
            lines.append(f"Customer: {data['customerName']}")
        lines.append("")
        for item in data.get("items", []):
            lines.append(f"{item.get('productName', '?')} ×{item.get('quantity', 0)}  "
                         f"₦{item.get('sellingPrice', 0)}  =  ₦{item.get('subtotal', 0)}")
        lines.append("")
        lines.append(f"Subtotal: ₦{data.get('totalAmount', 0) + data.get('discount', 0)}")
        if data.get("discount", 0) > 0:
            lines.append(f"Discount: -₦{data['discount']}")
        lines.append(f"Total: ₦{data.get('totalAmount', 0)}")
        lines.append(f"Payment: {data.get('paymentMethod', 'N/A')}")
        return "\n".join(lines)
