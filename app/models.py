from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    TIMEOUT_FAILED = "TIMEOUT_FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class PaymentRequest(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    payment_method: str = "credit_card"
    customer_id: str


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: PaymentStatus
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


class RefundRequest(BaseModel):
    payment_id: str
    amount: Optional[float] = None
    reason: str
    currency: str = "USD"
    exchange_rate: Optional[float] = 1.0


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    refunded_amount: float
    currency: str
    status: str
    timestamp: str
