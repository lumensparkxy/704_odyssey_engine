"""
CLI package for Odyssey Engine.

Provides both legacy and ADK-powered CLI interfaces.
Use lazy imports to avoid loading legacy code when using ADK mode.
"""

__all__ = ["OdysseyCLI", "OdysseyADKCLI"]


def __getattr__(name):
    """Lazy import to avoid circular dependencies and legacy code issues."""
    if name == "OdysseyCLI":
        from .interface import OdysseyCLI
        return OdysseyCLI
    elif name == "OdysseyADKCLI":
        from .adk_interface import OdysseyADKCLI
        return OdysseyADKCLI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
