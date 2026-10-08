"""Mock Payment Gateway Client."""
import logging
import time

logger = logging.getLogger(__name__)


class GatewayTimeoutException(Exception):
    """Raised when external payment provider gateway times out."""
    pass


class GatewayDeclinedException(Exception):
    """Raised when charge is declined by issuing bank."""
    pass


class PaymentGatewayClient:
    """Mock external payment gateway integration."""

    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def charge(self, amount: float, currency: str, payment_method: str) -> dict:
        """Call external gateway API to authorize and capture funds."""
        logger.info(f"Dispatching charge to upstream gateway: {amount} {currency}")

        # Simulate timeout on amounts ending in .99 or specific triggers
        if amount > 5000.0 or str(amount).endswith(".99"):
            logger.error("Gateway request timed out after socket connection timeout")
            raise GatewayTimeoutException("Upstream gateway read timeout after 30000ms")

        if amount == 402.0:
            raise GatewayDeclinedException("Card declined: insufficient funds")

        return {
            "gateway_ref": f"GW-TXN-{int(time.time() * 1000)}",
            "status": "APPROVED",
            "auth_code": "AUTH-9921",
        }

    def refund(self, original_tx_id: str, amount: float, currency: str) -> dict:
        """Process refund on upstream gateway."""
        logger.info(f"Processing upstream refund for tx {original_tx_id}: {amount} {currency}")
        return {
            "refund_ref": f"GW-REF-{int(time.time() * 1000)}",
            "status": "SETTLED",
        }
