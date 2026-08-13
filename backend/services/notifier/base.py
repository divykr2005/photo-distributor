from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationResult:
    success: bool
    provider: str
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    is_transient: bool = False


class BaseNotifier(ABC):
    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        """Send notification to recipient."""
        pass
