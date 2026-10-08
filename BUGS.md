# Intentionally Introduced Defects — Payment Service

This document catalogs the deliberate production bugs introduced into the Payment Service for AI Agent root cause analysis evaluation.

---

## BUG-PAY-001: Payment Gateway Timeout Leaves Transactions in Indefinite PENDING State

- **File:** `app/services/payment_service.py`
- **Function:** `process_payment(order_id, amount, currency, payment_method)`
- **Severity:** P1 (Critical Outage)
- **Symptom:** Orders experiencing network or gateway timeouts remain in `PENDING` indefinitely. Neither customer nor merchant receives a terminal resolution (`CONFIRMED` or `FAILED`).
- **Root Cause:** When `gateway_client.charge()` raises a `GatewayTimeoutException`, the `except` block logs the exception but returns `None` instead of creating/updating the transaction record with status `TIMEOUT_FAILED`. The calling service assumes absence of response means the request is still in-flight.
- **Related Historical AYS:** `AYS-1002`

---

## BUG-PAY-002: Floating Point Precision Loss in Currency Conversion During Partial Refunds

- **File:** `app/services/refund_service.py`
- **Function:** `calculate_refund_amount(original_amount, refund_ratio, exchange_rate)`
- **Severity:** P2 (High)
- **Symptom:** Multi-currency refunds accumulate small discrepancies (cents/fractions of pennies) between the payment gateway charge and the ledger settlement, failing automated end-of-day bank reconciliation.
- **Root Cause:** Calculations use native Python IEEE-754 `float` multiplication instead of `decimal.Decimal` with explicit `ROUND_HALF_EVEN` bankers rounding.
- **Related Historical AYS:** `AYS-1005`

---

## BUG-PAY-003: Race Condition Permitting Duplicate Simultaneous Refunds

- **File:** `app/services/refund_service.py`
- **Function:** `execute_refund(payment_id, amount)`
- **Severity:** P1 (Financial Loss)
- **Symptom:** When a customer double-clicks "Request Refund" or automated retry clients send concurrent requests, multiple refund records are executed against the same payment, exceeding the original charge.
- **Root Cause:** `execute_refund` reads transaction state (`if tx.status == "REFUNDED"`) without acquiring an atomic distributed or row-level lock. Two concurrent threads evaluate the condition before either writes the updated state.
- **Related Historical AYS:** `AYS-1003`

---

## BUG-PAY-004: Webhook Handler Ignores Idempotency Key Causing Duplicate Credit Notifications

- **File:** `app/services/webhook_service.py`
- **Function:** `handle_gateway_webhook(payload, event_id)`
- **Severity:** P2 (High)
- **Symptom:** External gateway delivery retries cause duplicate processing of payment confirmation events, triggering multiple confirmation emails and duplicate fulfillment requests.
- **Root Cause:** The webhook handler extracts `event_id` but never checks the event deduplication store before dispatching processing events.
