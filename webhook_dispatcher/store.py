import threading
from dataclasses import replace
from typing import Optional

from .models import DeliveryAttempt, Event, Subscription


class InMemoryStore:
    """Thread-safe in-memory stand-in for the events database.

    Records are copied on the way in and out, like rows from a real database,
    so callers have to save changes explicitly.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._subscriptions: dict[str, Subscription] = {}
        self._events: dict[str, Event] = {}
        self._attempts: list[DeliveryAttempt] = []

    def add_subscription(self, subscription: Subscription) -> None:
        with self._lock:
            self._subscriptions[subscription.id] = replace(subscription)

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            return replace(sub) if sub else None

    def add_event(self, event: Event) -> None:
        with self._lock:
            if event.id in self._events:
                raise ValueError(f"duplicate event id {event.id}")
            self._events[event.id] = replace(event)

    def get_event(self, event_id: str) -> Optional[Event]:
        with self._lock:
            event = self._events.get(event_id)
            return replace(event) if event else None

    def save_event(self, event: Event) -> None:
        with self._lock:
            self._events[event.id] = replace(event)

    def fetch_due(self, now: float, limit: int) -> list[Event]:
        with self._lock:
            due = [
                e for e in self._events.values()
                if e.status == "pending" and e.next_attempt_at <= now
            ]
            due.sort(key=lambda e: (e.next_attempt_at, e.created_at))
            return [replace(e) for e in due[:limit]]

    def mark_in_progress(self, event_ids: list[str]) -> None:
        with self._lock:
            for event_id in event_ids:
                self._events[event_id].status = "in_progress"

    def record_attempt(self, attempt: DeliveryAttempt) -> None:
        with self._lock:
            self._attempts.append(attempt)

    def attempts_for(self, event_id: str) -> list[DeliveryAttempt]:
        with self._lock:
            return [a for a in self._attempts if a.event_id == event_id]
