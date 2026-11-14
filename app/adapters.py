"""Future providers must verify webhook signatures and map external identities first."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ChatEnvelope:
    actor: str  # Resolved by server authentication, never from model output.
    text: str
    image: bytes | None = None
    mime_type: str = 'image/png'

class ChatAdapter(Protocol):
    def normalize(self, authenticated_actor: str, payload: dict) -> ChatEnvelope: ...

class WebAdapter:
    def normalize(self, authenticated_actor, payload):
        return ChatEnvelope(actor=authenticated_actor,**payload)

# Google Chat / Discord adapters intentionally have no unauthenticated webhook stub.
# Implement signature verification, external-group mapping, replay deduplication,
# then normalize to ChatEnvelope and call the same agent/service layer.
