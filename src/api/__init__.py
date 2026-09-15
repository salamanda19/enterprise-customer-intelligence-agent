"""API package — FastAPI surface for V3."""

from api.app import app, attach_meta, create_app

__all__ = ["app", "attach_meta", "create_app"]
