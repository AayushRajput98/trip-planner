"""Shared exception types — split out from trip_service so versioning.py can
raise/import them too without a circular import (trip_service imports
versioning to record every write)."""


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass
