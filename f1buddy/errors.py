class UserError(Exception):
    """Something the user can fix. The message is shown to them as-is."""


class SourceError(Exception):
    """An external source failed. `detail` is logged, never shown."""

    def __init__(self, source: str, detail: str = ""):
        super().__init__(f"{source}: {detail}")
        self.source = source
        self.detail = detail


class ParseError(SourceError):
    """A page was fetched but no longer has the structure the parser expects."""
