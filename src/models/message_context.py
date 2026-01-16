"""Data models for message handling context"""
from dataclasses import dataclass
from typing import Optional, NamedTuple


class ValidationResult(NamedTuple):
    """Result of message validation"""
    is_valid: bool
    reason: Optional[str] = None


@dataclass
class MessageContext:
    """User context for message processing"""
    user_id: str
    subscription: Optional[dict]
    onboarding: Optional[dict]
    awaiting_custom_note: bool
    pending_note: Optional[dict]

    @property
    def is_pending_activation(self) -> bool:
        """Check if user is pending activation"""
        return self.subscription and self.subscription.get('status') == 'pending'

    @property
    def is_in_onboarding(self) -> bool:
        """Check if user is in onboarding flow"""
        return self.onboarding and not self.onboarding.get('completed_at')

    @property
    def is_in_note_entry(self) -> bool:
        """Check if user is entering a custom note"""
        return self.awaiting_custom_note
