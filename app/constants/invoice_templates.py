from dataclasses import dataclass
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
INVOICE_TEMPLATE_DIR = APP_DIR / "templates" / "invoices"
TEMPLATE_PREVIEW_DIR = APP_DIR / "static" / "template_previews"


@dataclass(frozen=True, slots=True)
class InvoiceTemplateDefinition:
    key: str
    filename: str
    name: str
    description: str

    @property
    def preview_filename(self) -> str:
        return f"{self.key}.png"

    @property
    def preview_url(self) -> str:
        return f"/static/template_previews/{self.preview_filename}"


INVOICE_TEMPLATE_DEFINITIONS = (
    InvoiceTemplateDefinition(
        key="modern_1",
        filename="modern_1.html",
        name="Modern",
        description=(
            "Clean blue business invoice with clear totals and payment details."
        ),
    ),
    InvoiceTemplateDefinition(
        key="minimal_1",
        filename="minimal_1.html",
        name="Minimal",
        description=(
            "Plain, spacious invoice layout for simple professional documents."
        ),
    ),
    InvoiceTemplateDefinition(
        key="corporate_1",
        filename="corporate_1.html",
        name="Corporate",
        description=(
            "Structured corporate invoice with a strong header and summary blocks."
        ),
    ),
    InvoiceTemplateDefinition(
        key="01_classic_ledger",
        filename="01_classic_ledger.html",
        name="Classic Ledger",
        description="Timeless serif invoice with black-and-white double rules.",
    ),
    InvoiceTemplateDefinition(
        key="02_swiss_minimal",
        filename="02_swiss_minimal.html",
        name="Swiss Minimal",
        description="Clean, spacious invoice with a restrained teal accent.",
    ),
    InvoiceTemplateDefinition(
        key="03_bold_band",
        filename="03_bold_band.html",
        name="Bold Band",
        description="Bold indigo header with focused invoice summary cards.",
    ),
    InvoiceTemplateDefinition(
        key="04_sidebar_slate",
        filename="04_sidebar_slate.html",
        name="Sidebar Slate",
        description="Dark slate sidebar layout with a structured content area.",
    ),
    InvoiceTemplateDefinition(
        key="05_compact_pro",
        filename="05_compact_pro.html",
        name="Compact Pro",
        description="Dense professional layout suited to invoices with many items.",
    ),
    InvoiceTemplateDefinition(
        key="06_warm_studio",
        filename="06_warm_studio.html",
        name="Warm Studio",
        description="Friendly rounded layout with a warm sage-green palette.",
    ),
    InvoiceTemplateDefinition(
        key="07_contractor_grid",
        filename="07_contractor_grid.html",
        name="Contractor Grid",
        description="Heavy ruled grid with work details and signature lines.",
    ),
    InvoiceTemplateDefinition(
        key="08_executive_noir",
        filename="08_executive_noir.html",
        name="Executive Noir",
        description="Executive charcoal invoice with champagne-gold accents.",
    ),
    InvoiceTemplateDefinition(
        key="09_aurora_edge",
        filename="09_aurora_edge.html",
        name="Aurora Edge",
        description="Modern gradient invoice with a prominent status badge.",
    ),
    InvoiceTemplateDefinition(
        key="10_monogram_fine",
        filename="10_monogram_fine.html",
        name="Monogram Fine",
        description="Refined centered stationery with a monogram and hairline rules.",
    ),
)

INVOICE_TEMPLATES_BY_KEY = {
    definition.key: definition for definition in INVOICE_TEMPLATE_DEFINITIONS
}
INVOICE_TEMPLATE_FILES = {
    definition.key: definition.filename for definition in INVOICE_TEMPLATE_DEFINITIONS
}


def get_invoice_template_definition(
    template_key: str,
) -> InvoiceTemplateDefinition | None:
    return INVOICE_TEMPLATES_BY_KEY.get(template_key)
