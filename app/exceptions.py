class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class RetriesExhaustedError(LLMError):
    def __init__(self, last_error: str, attempts: int) -> None:
        self.last_error = last_error
        self.attempts = attempts
        super().__init__(f"Exhausted {attempts} retries. Last error: {last_error}")
