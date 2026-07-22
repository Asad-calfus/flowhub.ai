"""Domain exceptions, translated to HTTP responses by handlers registered in app.main."""


class NotFoundError(Exception):
    def __init__(self, entity: str, entity_id: str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} '{entity_id}' not found")


class DuplicateError(Exception):
    pass


class InvalidInputError(Exception):
    pass


class ClassificationUnavailableError(Exception):
    """Raised when a live LLM run is requested but the provider/API key isn't configured."""


class ClassificationFailedError(Exception):
    """Raised when a classifier call/parse fails (e.g. invalid structured AI output)."""


class InvalidTokenError(Exception):
    """Raised when a signed share-link token is missing, malformed, expired, or doesn't
    match the resource it's presented for (src/reports/signing.py)."""
