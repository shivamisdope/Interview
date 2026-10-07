from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay: float = 10.0
    multiplier: float = 2.0
    max_delay: float = 3600.0

    def should_retry(self, attempts_made: int) -> bool:
        return attempts_made <= self.max_attempts

    def next_delay(self, attempts_made: int) -> float:
        delay = self.base_delay * self.multiplier ** (attempts_made - 1)
        return min(delay, self.max_delay)
