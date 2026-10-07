import json

from webhook_dispatcher import (
    Dispatcher,
    Event,
    FakeClock,
    FakeHttpClient,
    InMemoryStore,
    RetryPolicy,
    Subscription,
)

URL = "https://customer.example.com/hooks"


def setup(responses=None, max_attempts=5):
    clock = FakeClock()
    store = InMemoryStore()
    http = FakeHttpClient(clock, {URL: responses or []})
    store.add_subscription(Subscription("sub-1", URL))
    dispatcher = Dispatcher(store, http, clock, RetryPolicy(max_attempts=max_attempts))
    return clock, store, http, dispatcher


def add_event(store, clock, event_id="evt-1", payload=None, due_in=0.0):
    store.add_event(Event(
        id=event_id,
        subscription_id="sub-1",
        payload=payload or {"type": "invoice.paid", "id": event_id},
        created_at=clock.now(),
        next_attempt_at=clock.now() + due_in,
    ))


def test_delivers_pending_event():
    clock, store, http, dispatcher = setup()
    clock.advance(5)
    add_event(store, clock, payload={"type": "invoice.paid", "amount": 1200})

    assert dispatcher.run_once() == 1

    assert len(http.sent) == 1
    request = http.sent[0]
    assert request.url == URL
    assert json.loads(request.body) == {"type": "invoice.paid", "amount": 1200}
    assert request.headers["Content-Type"] == "application/json"
    assert request.at == 5
    assert store.get_event("evt-1").status == "delivered"


def test_does_not_deliver_before_due():
    clock, store, http, dispatcher = setup()
    add_event(store, clock, due_in=30)

    dispatcher.run_once()
    assert http.sent == []

    clock.advance(30)
    dispatcher.run_once()
    assert len(http.sent) == 1


def test_server_error_is_retried_after_backoff():
    clock, store, http, dispatcher = setup([500, 200])
    add_event(store, clock)

    dispatcher.run_once()
    event = store.get_event("evt-1")
    assert event.status == "pending"
    assert event.next_attempt_at == 10

    clock.advance(9)
    dispatcher.run_once()
    assert len(http.sent) == 1

    clock.advance(1)
    dispatcher.run_once()
    assert len(http.sent) == 2
    assert store.get_event("evt-1").status == "delivered"


def test_attempts_are_recorded():
    clock, store, http, dispatcher = setup([503, 200])
    add_event(store, clock)

    dispatcher.run_once()
    clock.advance(10)
    dispatcher.run_once()

    attempts = store.attempts_for("evt-1")
    assert [(a.attempt, a.status_code, a.at) for a in attempts] == [(1, 503, 0), (2, 200, 10)]


def test_gives_up_after_max_attempts():
    clock, store, http, dispatcher = setup([500] * 10, max_attempts=5)
    add_event(store, clock)

    for _ in range(10):
        dispatcher.run_once()
        clock.advance(10_000)

    assert len(http.sent) == 5
    assert store.get_event("evt-1").status != "pending"


def test_permanent_failure_not_retried():
    clock, store, http, dispatcher = setup([400, 200])
    add_event(store, clock)

    for _ in range(5):
        dispatcher.run_once()
        clock.advance(10_000)

    assert len(http.sent) == 1
    assert store.get_event("evt-1").status != "pending"
