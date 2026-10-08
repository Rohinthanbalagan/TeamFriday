"""
Webhook Service - Ingests external payment provider webhook notifications.
Contains intentional defect BUG-PAY-004.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Processed event ledger
_PROCESSED_EVENTS = set()


class WebhookService:
    def handle_gateway_webhook(self, event_type: str, event_id: str, payload: Dict[str, Any]) -> dict:
        """
        Process gateway notifications such as charge.succeeded or charge.failed.
        """
        logger.info(f"Received gateway webhook: {event_type} id={event_id}")

        # =========================================================================
        # BUG-PAY-004: Missing idempotency validation on external webhook retries
        # External payment gateways (e.g., Stripe, Adyen) retry webhooks upon 5xx/network blips.
        # This handler receives event_id, but never checks `if event_id in _PROCESSED_EVENTS`.
        # Retried webhooks trigger duplicate business logic and customer notifications.
        #
        # Correct implementation:
        # if event_id in _PROCESSED_EVENTS:
        #     logger.info(f"Duplicate event {event_id} ignored")
        #     return {"status": "DUPLICATE_IGNORED"}
        # _PROCESSED_EVENTS.add(event_id)
        # =========================================================================

        # Dispatches order confirmation and customer email
        logger.info(f"Executing business logic for event {event_id} (Type: {event_type})")
        return {
            "status": "PROCESSED",
            "event_id": event_id,
            "event_type": event_type,
        }
