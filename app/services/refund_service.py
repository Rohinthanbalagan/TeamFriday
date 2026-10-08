"""
Refund Service - Handles customer refund calculations and execution.
Contains intentional defects BUG-PAY-002 and BUG-PAY-003.
"""
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models import RefundRequest, RefundResponse, PaymentStatus
from app.services.payment_service import _PAYMENT_DB
from app.gateway.client import PaymentGatewayClient

logger = logging.getLogger(__name__)

_REFUND_DB: Dict[str, dict] = {}


class RefundService:
    def __init__(self, gateway_client: Optional[PaymentGatewayClient] = None):
        self.gateway = gateway_client or PaymentGatewayClient()

    def calculate_refund_amount(
        self, original_amount: float, refund_ratio: float, exchange_rate: float = 1.0
    ) -> float:
        """
        Calculates refund amount with exchange rate conversion.
        """
        # =========================================================================
        # BUG-PAY-002: Floating point precision defect
        # Uses standard Python IEEE-754 binary floating-point multiplication.
        # Accumulates rounding errors (e.g., 19.99 * 0.33 * 1.07 -> 7.058793000000001)
        # leading to accounting reconciliation discrepancies with the general ledger.
        #
        # Correct implementation should use decimal.Decimal:
        # from decimal import Decimal, ROUND_HALF_EVEN
        # amount_dec = Decimal(str(original_amount)) * Decimal(str(refund_ratio)) * Decimal(str(exchange_rate))
        # return float(amount_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN))
        # =========================================================================
        unrounded_amount = original_amount * refund_ratio * exchange_rate
        return round(unrounded_amount, 2)

    def execute_refund(self, req: RefundRequest) -> RefundResponse:
        """
        Executes refund against an existing payment record.
        """
        payment = _PAYMENT_DB.get(req.payment_id)
        if not payment:
            raise ValueError(f"Payment record {req.payment_id} not found")

        # =========================================================================
        # BUG-PAY-003: Non-atomic race condition on duplicate refunds
        # Checks eligibility without row-level lock or distributed lock (Redis/Mutex).
        # Two simultaneous refund requests both pass this check, resulting in double refunds.
        #
        # Correct approach:
        # Use an atomic conditional write or lock:
        # with transaction_lock(req.payment_id):
        #     if payment["status"] == PaymentStatus.REFUNDED:
        #         raise ValueError("Payment has already been refunded")
        # =========================================================================
        if payment.get("status") == PaymentStatus.REFUNDED:
            raise ValueError(f"Payment {req.payment_id} has already been fully refunded")

        # Simulate small delay during processing which widens race condition window
        time.sleep(0.05)

        refund_amount = req.amount if req.amount is not None else payment["amount"]
        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"

        # Upstream gateway call
        self.gateway.refund(payment.get("transaction_id", "MOCK-TX"), refund_amount, req.currency)

        # Mark payment as refunded
        payment["status"] = PaymentStatus.REFUNDED
        payment["refund_id"] = refund_id
        payment["refunded_amount"] = refund_amount

        _REFUND_DB[refund_id] = {
            "refund_id": refund_id,
            "payment_id": req.payment_id,
            "amount": refund_amount,
            "reason": req.reason,
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return RefundResponse(
            refund_id=refund_id,
            payment_id=req.payment_id,
            refunded_amount=refund_amount,
            currency=req.currency,
            status="COMPLETED",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
