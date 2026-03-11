"""Exceptions for LLM service layer."""


class LLMValidationError(Exception):
    """LLM response failed schema validation after retries."""

    def __init__(self, schema_name: str, errors: list[str], attempts: int) -> None:
        self.schema_name = schema_name
        self.errors = errors
        self.attempts = attempts
        detail = "; ".join(errors[:3])
        super().__init__(
            f"{schema_name} validation failed after {attempts} attempt(s): {detail}"
        )


class LLMContentFilterError(Exception):
    """LLM request was rejected by the provider's content filter."""

    def __init__(self, original_error: Exception) -> None:
        self.original_error = original_error
        super().__init__(
            f"Content filter rejected the request: {original_error}"
        )
