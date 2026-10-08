"""
Payment Service - Primary payment authorization and capture workflow.
Contains intentional defects for AI RCA agent testing.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models import PaymentRequest, PaymentResponse, PaymentStatus
from app.gateway.client import PaymentGatewayClient, GatewayTimeoutException, GatewayDeclinedException

logger = logging.getLogger(__name__)

# In-memory transaction database
_PAYMENT_DB: Dict[str, dict] = {}


class PaymentService:
    def __init__(self, gateway_client: Optional[PaymentGatewayClient] = None):
        self.gateway = gateway_client or PaymentGatewayClient()

    def process_payment(self, req: PaymentRequest) -> Optional[PaymentResponse]:
        """
        Process a payment transaction.
        Creates an initial PENDING record, delegates to the gateway, and updates state.
        """
        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Step 1: Record payment in PENDING state
        _PAYMENT_DB[payment_id] = {
            "payment_id": payment_id,
            "order_id": req.order_id,
            "amount": req.amount,
            "currency": req.currency,
            "status": PaymentStatus.PENDING,
            "customer_id": req.customer_id,
            "created_at": now_str,
            "updated_at": now_str,
        }

        try:
            # Step 2: Attempt gateway authorization
            gw_resp = self.gateway.charge(req.amount, req.currency, req.payment_method)

            # Step 3: Transition to CAPTURED upon success
            _PAYMENT_DB[payment_id]["status"] = PaymentStatus.CAPTURED
            _PAYMENT_DB[payment_id]["transaction_id"] = gw_resp["gateway_ref"]
            _PAYMENT_DB[payment_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

            return PaymentResponse(
                payment_id=payment_id,
                order_id=req.order_id,
                amount=req.amount,
                currency=req.currency,
                status=PaymentStatus.CAPTURED,
                transaction_id=gw_resp["gateway_ref"],
                created_at=now_str,
            )

        except GatewayDeclinedException as de:
            logger.warning(f"Payment {payment_id} declined: {de}")
            _PAYMENT_DB[payment_id]["status"] = PaymentStatus.FAILED
            _PAYMENT_DB[payment_id]["error_message"] = str(de)
            return PaymentResponse(
                payment_id=payment_id,
                order_id=req.order_id,
                amount=req.amount,
                currency=req.currency,
                status=PaymentStatus.FAILED,
                error_message=str(de),
                created_at=now_str,
            )

        except GatewayTimeoutException as te:
            # =========================================================================
            # BUG-PAY-001: Gateway timeout exception handling defect
            # When the gateway times out, this catch block logs the error and returns None,
            # but fails to update the transaction status in _PAYMENT_DB to FAILED or TIMEOUT_FAILED.
            # The transaction remains in 'PENDING' status indefinitely in the database,
            # causing the caller/order service to wait forever and freeze downstream orders.
            #
            # The correct implementation must update:
            # _PAYMENT_DB[payment_id]["status"] = PaymentStatus.TIMEOUT_FAILED
            # and return a structured PaymentResponse with status FAILED.
            # =========================================================================
            logger.error(f"Gateway read timeout for payment {payment_id}: {te}")
            return None

    def get_payment(self, payment_id: str) -> Optional[dict]:
        return _PAYMENT_DB.get(payment_id)
