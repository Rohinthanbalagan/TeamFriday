"""
Payment Service - FastAPI Entry Point
"""
import logging
from fastapi import FastAPI, HTTPException
from app.models import PaymentRequest, PaymentResponse, RefundRequest, RefundResponse
from app.services.payment_service import PaymentService
from app.services.refund_service import RefundService
from app.services.webhook_service import WebhookService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Payment Service",
    description="Microservice responsible for payment processing, refunds, and gateway webhooks.",
    version="1.0.0",
)

payment_svc = PaymentService()
refund_svc = RefundService()
webhook_svc = WebhookService()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "Payment Service"}


@app.post("/api/payments", response_model=PaymentResponse)
def create_payment(req: PaymentRequest):
    result = payment_svc.process_payment(req)
    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Payment gateway communication timed out. Transaction status unresolved.",
        )
    return result


@app.get("/api/payments/{payment_id}")
def get_payment(payment_id: str):
    tx = payment_svc.get_payment(payment_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Payment not found")
    return tx


@app.post("/api/refunds", response_model=RefundResponse)
def create_refund(req: RefundRequest):
    try:
        return refund_svc.execute_refund(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/webhooks/gateway")
def handle_webhook(event_type: str, event_id: str, payload: dict):
    return webhook_svc.handle_gateway_webhook(event_type, event_id, payload)
