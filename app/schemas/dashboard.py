from decimal import Decimal

from pydantic import BaseModel

from app.schemas.api_response import ApiResponse
from app.schemas.invoice import InvoiceOut
from app.schemas.payment_record import PaymentRecordOut


class DashboardSummaryOut(BaseModel):
    clients_count: int
    invoices_count: int
    draft_invoices_count: int
    sent_invoices_count: int
    partially_paid_invoices_count: int
    paid_invoices_count: int
    overdue_invoices_count: int
    total_sales: Decimal
    total_paid: Decimal
    total_due: Decimal
    recent_invoices: list[InvoiceOut]
    recent_payments: list[PaymentRecordOut]


DashboardSummaryResponse = ApiResponse[DashboardSummaryOut]
