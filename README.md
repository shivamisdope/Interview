# webhook-dispatcher

A small service that delivers webhook events to customer endpoints.

Customers register a **subscription** (an endpoint URL). When something happens
on our side we store an **event** for that subscription, and the **dispatcher**
picks up due events, POSTs them to the customer's URL, and records the result.
Failed deliveries are retried with exponential backoff.

```
webhook_dispatcher/
  models.py        Event, Subscription, DeliveryAttempt
  store.py         in-memory store (stands in for the database)
  dispatcher.py    picks due events, sends them, records results
  retry_policy.py  backoff and max attempts
  http_client.py   fake HTTP client with scripted responses per URL
  clock.py         fake clock
tests/
```

Nothing here touches the network or sleeps: the HTTP client returns scripted
responses (status codes, timeouts, headers) and time only moves when a test
calls `clock.advance(...)`.

## Running the tests

Python 3.11+.

```
pip install -r requirements.txt && pytest
```

## Working in this session

You can use any AI tools you like (Claude Code, Cursor, Copilot, ChatGPT, ...).
Please share your screen and think out loud as you work. We care more about
how you reason about the code and the changes than about how fast you type.
