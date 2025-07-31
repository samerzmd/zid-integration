"""Custom exceptions for the Zid integration service"""

from fastapi import HTTPException


class ZidAPIException(Exception):
    """Base exception for Zid API related errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationException(ZidAPIException):
    """Exception for authentication related errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class TokenExpiredException(AuthenticationException):
    """Exception for expired token errors"""
    def __init__(self, message: str = "Access token has expired"):
        super().__init__(message)


class WebhookValidationException(ZidAPIException):
    """Exception for webhook validation errors"""
    def __init__(self, message: str = "Webhook validation failed"):
        super().__init__(message, status_code=400)


class RateLimitException(ZidAPIException):
    """Exception for rate limiting errors"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ProductNotFoundException(ZidAPIException):
    """Exception for product not found errors"""
    def __init__(self, product_id: int):
        message = f"Product with ID {product_id} not found"
        super().__init__(message, status_code=404)


class OrderNotFoundException(ZidAPIException):
    """Exception for order not found errors"""
    def __init__(self, order_id: int):
        message = f"Order with ID {order_id} not found"
        super().__init__(message, status_code=404)