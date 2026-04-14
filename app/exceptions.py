class AIStructuredOutputError(Exception):
    """Gemini returned text that is not valid JSON or does not match the schema."""
