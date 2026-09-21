"""Who's making the current edit, and why — set once per request/tool call,
read by versioning.record_version() so callers don't have to thread actor/
message through every trip_service function.

FastAPI/Starlette run a sync route handler (and a sync "dependency with
yield") via anyio's worker threadpool, each call getting its OWN copy of the
current context — a mutation made inside one offloaded call is never copied
back out to the request's own context, and a Token from one such call can't
be reset from another (different Context entirely). So request-scoped actor/
message is set directly (see set_actor/set_message, used by an ASYNC
dependency in app.auth, which runs in the request's real context — no
offload — so its writes ARE visible to whatever gets offloaded afterwards).
`editing()` stays a plain context manager for MCP tool functions, which set
and clear it within one synchronous call, no thread hop in between."""
from contextlib import contextmanager
from contextvars import ContextVar

_actor: ContextVar[str] = ContextVar("edit_actor", default="Unknown")
_message: ContextVar[str | None] = ContextVar("edit_message", default=None)


def set_actor(actor: str) -> None:
    _actor.set(actor or "Unknown")


def set_message(message: str | None) -> None:
    _message.set(message or None)


@contextmanager
def editing(actor: str, message: str | None = None):
    actor_token = _actor.set(actor or "Unknown")
    message_token = _message.set(message or None)
    try:
        yield
    finally:
        _actor.reset(actor_token)
        _message.reset(message_token)


def current_actor() -> str:
    return _actor.get()


def current_message() -> str | None:
    return _message.get()
