from __future__ import annotations

import io
from typing import Any

from fpdf import FPDF

from shopsecure_api import ShopSecureClient


def generate_receipt_pdf(receipt: dict[str, Any]) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format=(80, 200))
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=8)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, receipt.get("businessName", "Store"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4, f"{receipt['receiptNumber']}  |  {receipt['createdAt'][:10]}", align="C", new_x="LMARGIN", new_y="NEXT")

    if receipt.get("customerName"):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 4, f"Customer: {receipt['customerName']}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(4, pdf.get_y(), 76, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 7)
    col_w = [32, 10, 16, 18]
    headers = ["Item", "Qty", "Price", "Total"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 5, h, align="C" if i > 0 else "L")
    pdf.ln()

    pdf.set_draw_color(200, 200, 200)
    pdf.line(4, pdf.get_y(), 76, pdf.get_y())
    pdf.ln(1)

    pdf.set_font("Helvetica", "", 7)
    for item in receipt.get("items", []):
        pdf.cell(col_w[0], 5, item["productName"][:18], align="L")
        pdf.cell(col_w[1], 5, str(item["quantity"]), align="C")
        pdf.cell(col_w[2], 5, f"N{float(item['unitPrice']):,.0f}", align="C")
        pdf.cell(col_w[3], 5, f"N{float(item['total']):,.0f}", align="C")
        pdf.ln()

    pdf.ln(1)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(4, pdf.get_y(), 76, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Subtotal          N{float(receipt['subtotal']):,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    if receipt.get("discount") and float(receipt["discount"]) > 0:
        pdf.set_text_color(220, 38, 38)
        pdf.cell(0, 5, f"Discount         -N{float(receipt['discount']):,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"TOTAL            N{float(receipt['total']):,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(0, 4, receipt.get("paymentMethod", ""), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(4, pdf.get_y(), 76, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 6)
    pdf.cell(0, 4, "Powered by ShopSecure", align="C", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


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
        data = await self._api.create_sale(items, customer_name, customer_phone,
                                            notes, discount)
        sale_id = data.get("id")
        total = data.get("totalAmount", 0)
        number = data.get("saleNumber", "")

        receipt = await self._api.get_receipt(sale_id)

        # Send PDF receipt via WhatsApp document
        if self._send_document and self._phone:
            pdf_bytes = generate_receipt_pdf(receipt)
            try:
                await self._send_document(self._phone, pdf_bytes, f"receipt-{number}.pdf")
            except Exception:
                pass

        lines = [
            f"✅ Sale {number} recorded for ₦{total}. Stock updated.",
            "📎 PDF receipt sent to this chat.",
        ]
        return "\n".join(lines)

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
