from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.constants.invoice_templates import APP_DIR, INVOICE_TEMPLATE_FILES


TEMPLATE_FILES = INVOICE_TEMPLATE_FILES

CURRENCY_PREFIXES = {
    "AED": "AED ",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "PKR": "PKR ",
    "SAR": "SAR ",
    "USD": "$",
}


class PdfService:
    def __init__(self, templates_dir: str | Path):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_invoice_pdf(
        self,
        invoice,
        template_key: str,
        company_settings=None,
    ) -> bytes:
        html_content = self.generate_invoice_html(
            invoice=invoice,
            template_key=template_key,
            company_settings=company_settings,
        )
        return HTML(
            string=html_content,
            base_url=str(self.templates_dir.resolve()),
        ).write_pdf()

    def generate_invoice_html(
        self,
        invoice,
        template_key: str,
        company_settings=None,
    ) -> str:
        template_file = TEMPLATE_FILES.get(template_key)
        if not template_file:
            raise ValueError("Invalid template key.")

        template = self.env.get_template(template_file)
        context = self._build_invoice_context(invoice, company_settings)
        return template.render(**context)

    def _build_invoice_context(self, invoice, company_settings=None) -> dict:
        company_name = "SmartBiz"
        company_address = "Your Company Address"
        company_email = "billing@smartbiz.com"
        company_phone = "+1 000 000 0000"
        company_logo_url = None
        company_website = None
        company_tax_number = None
        company_registration_number = None
        currency_code = "USD"

        if company_settings is not None:
            company_name = company_settings.company_name or company_name
            company_address = company_settings.address or company_address
            company_email = company_settings.email or company_email
            company_phone = company_settings.phone or company_phone
            company_logo_url = self._resolve_logo_url(company_settings.logo_url)
            company_website = company_settings.website
            company_tax_number = company_settings.tax_number
            company_registration_number = company_settings.registration_number
            currency_code = company_settings.default_currency or currency_code

        amount_paid = sum(
            (self._money_value(payment.amount) for payment in invoice.payments),
            start=Decimal("0.00"),
        )
        total = self._money_value(invoice.total)
        balance_due = max(total - amount_paid, Decimal("0.00"))

        items = [
            {
                "description": item.product_name,
                "details": item.description,
                "quantity": self._display_quantity(item.quantity),
                "unit": None,
                "unit_price": self._money_value(item.unit_price),
                "amount": self._money_value(item.line_total),
            }
            for item in invoice.items
        ]

        client_address = invoice.client_address or ""
        return {
            "company": {
                "name": company_name,
                "logo_url": company_logo_url,
                "address": company_address,
                "address_lines": self._address_lines(company_address),
                "email": company_email,
                "phone": company_phone,
                "website": company_website,
                "tax_id": company_tax_number or company_registration_number,
                "tax_number": company_tax_number,
                "registration_number": company_registration_number,
            },
            "client": {
                "name": invoice.client_name or "Client",
                "address": client_address,
                "address_lines": self._address_lines(client_address),
                "email": invoice.client_email,
                "phone": invoice.client_phone,
                "tax_id": None,
            },
            "invoice": {
                "number": invoice.invoice_number,
                "issue_date": self._format_date(invoice.issue_date),
                "due_date": self._format_date(invoice.due_date),
                "currency": self._currency_prefix(currency_code),
                "po_number": None,
                "status": (invoice.status or "").upper(),
                "notes": invoice.notes or "",
                "terms": None,
                "payment_details": None,
            },
            "items": items,
            "totals": {
                "subtotal": self._money_value(invoice.subtotal),
                "discount": self._money_value(invoice.discount),
                "discount_label": "Discount",
                "tax": self._money_value(invoice.tax),
                "tax_label": "Tax",
                "shipping": Decimal("0.00"),
                "total": total,
                "amount_paid": amount_paid,
                "balance_due": balance_due,
            },
        }

    @staticmethod
    def _money_value(value: Decimal | float | int | None) -> Decimal:
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _display_quantity(value: Decimal | float | int) -> int | Decimal:
        quantity = value if isinstance(value, Decimal) else Decimal(str(value))
        if quantity == quantity.to_integral_value():
            return int(quantity)
        return quantity.normalize()

    @staticmethod
    def _address_lines(value: str | None) -> list[str]:
        if not value:
            return []
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        return lines or [value.strip()]

    @staticmethod
    def _format_date(value: object) -> str:
        if not isinstance(value, date):
            return str(value)
        return f"{value.strftime('%B')} {value.day}, {value.year}"

    @staticmethod
    def _currency_prefix(currency_code: str | None) -> str:
        code = (currency_code or "USD").strip().upper()
        return CURRENCY_PREFIXES.get(code, f"{code} ")

    @staticmethod
    def _resolve_logo_url(logo_url: str | None) -> str | None:
        if not logo_url or not logo_url.startswith("/static/"):
            return logo_url

        logo_path = APP_DIR / "static" / logo_url.removeprefix("/static/")
        if logo_path.is_file():
            return logo_path.resolve().as_uri()
        return logo_url

    def _format_money(self, value: Decimal | float | int | None) -> str:
        return f"${self._money_value(value):,.2f}"
