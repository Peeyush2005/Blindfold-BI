"""
Backwards-compatibility shim for Blindfold Privacy Gateway.
Points to app.core.gateway.blindfold_gateway.
"""

from app.core.gateway import blindfold_gateway as blindfold, BlindfoldGatewayService

BlindfoldGateway = BlindfoldGatewayService

__all__ = ["blindfold", "BlindfoldGateway"]
