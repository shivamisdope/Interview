from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Subscription:
    id: str
    url: str
    active: bool = True


@dataclass
class Event:
    id: str
    subscription_id: str
    payload: dict[str, Any]
    created_at: float
    status: str = "pending"
    attempts: int = 0
    next_attempt_at: float = 0.0
    last_error: Optional[str] = None


@dataclass
class DeliveryAttempt:
    event_id: str
    attempt: int
    at: float
    status_code: Optional[int] = None
    error: Optional[str] = None
