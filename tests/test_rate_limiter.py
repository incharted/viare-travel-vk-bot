from services.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_blocks_after_limit_is_reached():
    limiter = InMemoryRateLimiter()

    assert limiter.allow(user_id=1, max_events=2, window_sec=60) is True
    assert limiter.allow(user_id=1, max_events=2, window_sec=60) is True
    assert limiter.allow(user_id=1, max_events=2, window_sec=60) is False


def test_rate_limiter_keeps_users_independent():
    limiter = InMemoryRateLimiter()

    assert limiter.allow(user_id=1, max_events=1, window_sec=60) is True
    assert limiter.allow(user_id=1, max_events=1, window_sec=60) is False
    assert limiter.allow(user_id=2, max_events=1, window_sec=60) is True
