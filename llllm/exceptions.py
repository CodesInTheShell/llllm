"""Package-specific exceptions."""


class LLLLMError(Exception):
    """Base exception for package errors."""


class ProviderConfigurationError(LLLLMError):
    """Raised when provider configuration is invalid or incomplete."""


class ProviderRequestError(LLLLMError):
    """Raised when a provider request fails."""


class InvalidInputError(LLLLMError):
    """Raised when a user input payload is not supported."""


class ProviderFallbackError(LLLLMError):
    """Raised when primary and fallback provider attempts are exhausted."""
