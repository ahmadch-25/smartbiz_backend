from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.core.config import settings


TEMPLATE_FILES = {
    "modern_1": "modern_1.html",
    "minimal_1": "minimal_1.html",
    "corporate_1": "corporate_1.html",
}


class PdfService:
    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_invoice_pdf(self, invoice, template_key: str) -> bytes:
        template_file = TEMPLATE_FILES.get(template_key)
        if not template_file:
            raise ValueError("Invalid template key.")

        template = self.env.get_template(template_file)

        context = self._build_invoice_context(invoice)

        html_content = template.render(**context)

        pdf_bytes = HTML(
            string=html_content,
            base_url=self.templates_dir,
        ).write_pdf()

        return pdf_bytes

    def _build_invoice_context(self, invoice) -> dict:
        items = []
        for item in invoice.items:
            items.append(
                {
                    "name": item.product_name,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": self._format_money(item.unit_price),
                    "total": self._format_money(item.line_total),
                }
            )

        return {
            "company": {
                "name": "SmartBiz",
                "address": "Your Company Address",
                "email": "billing@smartbiz.com",
                "phone": "+1 000 000 0000",
            },
            "client": {
                "name": invoice.client_name,
                "address": invoice.client_address,
                "email": invoice.client_email,
                "phone": invoice.client_phone,
            },
            "invoice": {
                "number": invoice.invoice_number,
                "issue_date": str(invoice.issue_date),
                "due_date": str(invoice.due_date),
                "status": invoice.status,
                "notes": invoice.notes or "",
            },
            "items": items,
            "totals": {
                "subtotal": self._format_money(invoice.subtotal),
                "tax": self._format_money(invoice.tax),
                "discount": self._format_money(invoice.discount),
                "grand_total": self._format_money(invoice.total),
            },
            "payment": {
                "bank_name": "",
                "account_name": "",
                "account_number": "",
                "terms": "",
            },
        }

    def _format_money(self, value: Decimal | float | int | None) -> str:
        if value is None:
            value = Decimal("0.00")
        return f"${Decimal(value):,.2f}"