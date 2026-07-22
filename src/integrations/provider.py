import abc
from typing import Dict, Any, List, Optional

class ExternalEventProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The identifier/name of the provider (e.g. 'eventbrite', 'meetup')."""
        pass

    @abc.abstractmethod
    def register_webhook(self, endpoint_url: str, actions: List[str] = None) -> Dict[str, Any]:
        """Registers a webhook URL with the provider."""
        pass

    @abc.abstractmethod
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """Lists registered webhooks from the provider."""
        pass

    @abc.abstractmethod
    def delete_webhook(self, webhook_id: str) -> bool:
        """Deletes a registered webhook."""
        pass

    @abc.abstractmethod
    def sync_all_events(self) -> Dict[str, Any]:
        """Manually synchronizes all events from the provider."""
        pass

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, ExternalEventProvider] = {}

    def register(self, provider: ExternalEventProvider):
        self._providers[provider.name.lower()] = provider

    def get(self, name: str) -> Optional[ExternalEventProvider]:
        return self._providers.get(name.lower())

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

# Global registry instance
provider_registry = ProviderRegistry()
