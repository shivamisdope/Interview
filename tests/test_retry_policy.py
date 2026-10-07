from webhook_dispatcher import RetryPolicy


def test_backoff_doubles_each_attempt():
    policy = RetryPolicy(base_delay=10, multiplier=2)
    assert [policy.next_delay(n) for n in range(1, 5)] == [10, 20, 40, 80]


def test_backoff_is_capped():
    policy = RetryPolicy(base_delay=10, multiplier=2, max_delay=60)
    assert policy.next_delay(3) == 40
    assert policy.next_delay(4) == 60
    assert policy.next_delay(20) == 60


def test_retries_allowed_early_on():
    policy = RetryPolicy(max_attempts=5)
    assert policy.should_retry(1)
    assert policy.should_retry(3)
