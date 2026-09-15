"""API package — FastAPI surface for V3."""

from agent.meta import attach_meta
from api.app import app, create_app

__all__ = ["app", "attach_meta", "create_app"]
