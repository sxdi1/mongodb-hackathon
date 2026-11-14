"""Future providers must verify webhook signatures and map external identities first."""
from dataclasses import dataclass, field
from typing import Callable, Protocol

@dataclass(frozen=True)
class ChatEnvelope:
    actor: str  # Resolved by server authentication, never from model output.
    text: str
    image: bytes | None = None
    mime_type: str = 'image/png'
    actor_name: str = ''
    history: list[dict[str, str]] = field(default_factory=list)
    search: Callable[[str], dict] | None = None

class ChatAdapter(Protocol):
    def normalize(self, authenticated_actor: str, payload: dict) -> ChatEnvelope: ...

class WebAdapter:
    def normalize(self, authenticated_actor, payload):
        return ChatEnvelope(actor=authenticated_actor,**payload)

# Google Chat / Discord adapters intentionally have no unauthenticated webhook stub.
# Implement signature verification, external-group mapping, replay deduplication,
# then normalize to ChatEnvelope and call the same agent/service layer.
