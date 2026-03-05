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
