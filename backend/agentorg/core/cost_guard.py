class CostLimitExceeded(Exception):
    pass


class CostGuard:
    def __init__(self, max_cost_usd: float | None = None, max_tokens: int | None = None):
        self.max_cost_usd = max_cost_usd
        self.max_tokens = max_tokens

    def check(self, current_cost_usd: float, current_tokens: int, run_id: str = "") -> None:
        if self.max_cost_usd and current_cost_usd >= self.max_cost_usd:
            raise CostLimitExceeded(
                f"Run {run_id[:8]} exceeded cost limit ${self.max_cost_usd:.2f} "
                f"(current: ${current_cost_usd:.4f})"
            )
        if self.max_tokens and current_tokens >= self.max_tokens:
            raise CostLimitExceeded(
                f"Run {run_id[:8]} exceeded token limit {self.max_tokens:,} "
                f"(current: {current_tokens:,})"
            )

    def warn_approaching(self, current_cost_usd: float, threshold: float = 0.8) -> bool:
        if self.max_cost_usd:
            return current_cost_usd >= self.max_cost_usd * threshold
        return False
