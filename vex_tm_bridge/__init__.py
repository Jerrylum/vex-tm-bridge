"""VEX Tournament Manager Bridge

A Python bridge for interacting with VEX Tournament Manager software.
"""

__version__ = "0.1.0"

from .impl import get_bridge_engine

__all__ = ["get_bridge_engine"]
