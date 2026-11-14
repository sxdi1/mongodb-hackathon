from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Profile(Strict):
    name: str = Field(min_length=1, max_length=60)
    requirements: list[str] = Field(default_factory=list, max_length=20)
    transport: list[Literal['walk','car','bus','train']] = Field(min_length=1)
    budget_cents: int = Field(ge=0, le=10000000)

class Policy(Strict):
    requirements: list[str] = Field(default_factory=list, max_length=20)
    transport: list[Literal['walk','car','bus','train']] = Field(min_length=1)
    cap_cents: int = Field(ge=0, le=10000000)
    blocked_tags: list[str] = Field(default_factory=lambda: ['alcohol','pork'])

class Proposal(Strict):
    title: str = Field(min_length=1, max_length=200)
    category: Literal['food','activity','transport','expense']
    cost_cents: int = Field(ge=0, le=10000000, description='Per person for plans; total for expenses')
    tags: list[str] = Field(default_factory=list, max_length=30)
    claims: list[str] = Field(default_factory=list, max_length=30)
    venue_id: str | None = None
    transport: Literal['walk','car','bus','train'] = 'walk'
    start: datetime | None = None
    end: datetime | None = None
    travel_minutes: int = Field(default=15, ge=0, le=1440)
    @model_validator(mode='after')
    def dates(self):
        if bool(self.start) != bool(self.end): raise ValueError('Provide both start and end')
        if self.start and (not self.start.tzinfo or not self.end.tzinfo or self.end <= self.start):
            raise ValueError('Use timezone-aware start/end, end after start')
        return self

class ExpenseLine(Strict):
    description: str = Field(min_length=1, max_length=200)
    amount_cents: int | None = Field(default=None, ge=0, le=100000000)

class ExpenseMention(Strict):
    description: str | None = Field(default=None, max_length=200, description='Expense or purchase description stated in chat')
    merchant: str | None = Field(default=None, max_length=200, description='Merchant explicitly named in chat')
    amount_cents: int | None = Field(default=None, ge=0, le=100000000, description='Total amount stated, as integer cents; for example $12.34 is 1234')
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$', description='ISO 4217 currency explicitly stated, such as CAD or USD; leave null if unstated')
    occurred_on_text: str | None = Field(default=None, max_length=80, description='Date or relative date exactly as stated, not inferred')
    items: list[ExpenseLine] = Field(default_factory=list, max_length=50)

class ConversationUnderstanding(Strict):
    keywords: list[str] = Field(min_length=1, max_length=12, description='Important words or short phrases the user mentioned')
    intent: str = Field(min_length=1, max_length=120, description='Short description of what the user appears to be doing or asking')
    entities: list[str] = Field(default_factory=list, max_length=12, description='Explicit names, places, amounts, dates, or items mentioned')

class Chat(Strict):
    text: str = Field(min_length=1, max_length=4000)
    image_base64: str | None = Field(default=None, max_length=2800000)
    mime_type: Literal['image/png','image/jpeg'] = 'image/png'

class Vote(Strict):
    proposal_id: str

class Acknowledge(Strict):
    kind: Literal['sent','received']

class Cancel(Strict):
    approved: bool = False
