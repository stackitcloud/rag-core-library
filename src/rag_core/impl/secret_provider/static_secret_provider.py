"""Provide static token provider."""

from rag_core.secret_provider.secret_provider import SecretProvider
from rag_core.impl.settings.aleph_alpha_settings import AlephAlphaSettings


class StaticSecretProvider(SecretProvider):
    """Simple API token provider."""

    def __init__(self, settings: AlephAlphaSettings):
        """Simple API token provider.

        Parameters
        ----------
        settings : AlephAlphaSettings
            Settings for AlephAlpha
        """
        self._api_key = settings.aleph_alpha_api_key

    @property
    def provided_key(self) -> str:
        return "aleph_alpha_api_key"

    def provide_token(self) -> dict:
        return {self.provided_key: self._api_key}
