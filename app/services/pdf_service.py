from decimal import Decimal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


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

    def generate_invoice_pdf(self, invoice, template_key: str, company_settings=None) -> bytes:
        template_file = TEMPLATE_FILES.get(template_key)
        if not template_file:
            raise ValueError("Invalid template key.")

        template = self.env.get_template(template_file)

        context = self._build_invoice_context(invoice, company_settings)

        html_content = template.render(**context)

        pdf_bytes = HTML(
            string=html_content,
            base_url=self.templates_dir,
        ).write_pdf()

        return pdf_bytes

    def _build_invoice_context(self, invoice, company_settings=None) -> dict:
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

        company_name = "SmartBiz"
        company_address = "Your Company Address"
        company_email = "billing@smartbiz.com"
        company_phone = "+1 000 000 0000"
        company_logo_url = None
        company_website = None
        company_tax_number = None
        company_registration_number = None

        if company_settings is not None:
            company_name = company_settings.company_name or company_name
            company_address = company_settings.address or company_address
            company_email = company_settings.email or company_email
            company_phone = company_settings.phone or company_phone
            company_logo_url = company_settings.logo_url
            company_website = company_settings.website
            company_tax_number = company_settings.tax_number
            company_registration_number = company_settings.registration_number

        return {
            "company": {
                "name": company_name,
                "address": company_address,
                "email": company_email,
                "phone": company_phone,
                "logo_url": company_logo_url,
                "website": company_website,
                "tax_number": company_tax_number,
                "registration_number": company_registration_number,
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
