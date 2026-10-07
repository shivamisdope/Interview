import json
import logging

from .http_client import RequestTimeout
from .models import DeliveryAttempt, Event
from .retry_policy import RetryPolicy

log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, store, http_client, clock, retry_policy=None, batch_size=10):
        self.store = store
        self.http = http_client
        self.clock = clock
        self.retry_policy = retry_policy or RetryPolicy()
        self.batch_size = batch_size

    def run_once(self) -> int:
        """Deliver the events that are due now. Returns how many were picked up."""
        events = self.store.fetch_due(self.clock.now(), self.batch_size)
        self.store.mark_in_progress([e.id for e in events])
        try:
            for event in events:
                self._deliver(event)
        except RequestTimeout as exc:
            log.warning("delivery failed: %s", exc)
        return len(events)

    def _deliver(self, event: Event) -> None:
        subscription = self.store.get_subscription(event.subscription_id)
        if subscription is None or not subscription.active:
            event.status = "failed"
            event.last_error = "subscription inactive"
            self.store.save_event(event)
            return

        event.attempts += 1
        now = self.clock.now()
        body = json.dumps(event.payload)
        response = self.http.send(subscription.url, body, self._headers(event, now))
        self.store.record_attempt(
            DeliveryAttempt(event.id, event.attempts, now, status_code=response.status_code)
        )

        if 200 <= response.status_code < 300:
            event.status = "delivered"
            event.last_error = None
        elif self.retry_policy.should_retry(event.attempts):
            event.status = "pending"
            event.next_attempt_at = now + self.retry_policy.next_delay(event.attempts)
            event.last_error = f"HTTP {response.status_code}"
        else:
            event.status = "failed"
            event.last_error = f"HTTP {response.status_code}"
        self.store.save_event(event)

    def _headers(self, event: Event, now: float) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Webhook-Attempt": str(event.attempts),
            "X-Webhook-Timestamp": str(int(now)),
        }
