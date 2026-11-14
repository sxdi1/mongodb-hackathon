"""Normalize expense facts from chat into a versioned, persistence-ready record."""
import re
from decimal import Decimal
from typing import Any

from .models import ExpenseMention

MAX_AMOUNT_CENTS = 100_000_000
CURRENCY_CODES = r'CAD|USD|EUR|GBP|AUD|NZD'
MONEY = re.compile(
    rf'(?<![\w.])(?:(?P<prefix>{CURRENCY_CODES})\s*)?'
    rf'(?P<symbol>[$€£])?\s*'
    rf'(?P<amount>(?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?:\.\d{{1,2}})?)'
    rf'(?:\s*(?P<suffix>{CURRENCY_CODES}|dollars?|bucks?))?(?!\w)',
    re.IGNORECASE,
)
DATE_TEXT = re.compile(
    r'\b(today|yesterday|last night|this morning|this afternoon|'
    r'last week|on \d{4}-\d{2}-\d{2})\b',
    re.IGNORECASE,
)
EXPENSE_CUE = re.compile(
    r'\b(spent|paid|bill|receipt|total(?:led)?|came to|'
    r'charge(?:d)?|bought|ordered|expense|cost(?:s|ed|ing)?)\b',
    re.IGNORECASE,
)
EXPENSE_QUESTION_OR_ESTIMATE = re.compile(
    r'\b(?:how much|what does|what will|will|would|estimate|estimated|'
    r'budget|per person)\b',
    re.IGNORECASE,
)
PURCHASE_CONTEXT = re.compile(
    r'\b(dinner|lunch|breakfast|meal|food|coffee|taxi|uber|gas|hotel|'
    r'ticket|groceries|restaurant|snacks?)\b',
    re.IGNORECASE,
)


def _currency(match: re.Match[str]) -> tuple[str, str]:
    explicit = match.group('prefix') or match.group('suffix')
    if explicit and explicit.lower() not in {'dollar', 'dollars', 'buck', 'bucks'}:
        return explicit.upper(), 'explicit'
    symbol = match.group('symbol')
    if symbol == '€':
        return 'EUR', 'explicit'
    if symbol == '£':
        return 'GBP', 'explicit'
    return 'CAD', 'group_default'


def _amount(match: re.Match[str]) -> int | None:
    try:
        cents = int(Decimal(match.group('amount').replace(',', '')) * 100)
    except (ValueError, ArithmeticError):
        return None
    return cents if 0 <= cents <= MAX_AMOUNT_CENTS else None


def _date_text(text: str) -> str | None:
    match = DATE_TEXT.search(text)
    return match.group(0) if match else None


def _clean_phrase(value: str) -> str | None:
    value = DATE_TEXT.sub('', value)
    value = re.sub(r'\b(?:yesterday|today|tonight)\b', '', value, flags=re.IGNORECASE)
    value = value.strip()
    value = re.sub(r'^(?:we|i|you|they|it|this|that)\b[\s,]*', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^(?:paid|spent|bought|ordered|got|had|cost(?:s|ed|ing)?|came to|was|is|total(?:led)?)\b[\s,]*', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\b(?:cost(?:s|ed|ing)?|came to|was|is|total(?:led)?)\s*$', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\s*(?:,?\s*(?:and\s+)?(?:this|that|it)(?:\s+ended up)?)\s*$', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^(?:for|on)\s+', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\s+', ' ', value).strip(" \t\r\n,.;:!?-'\"")
    if not value or value.lower() in {'it', 'this', 'that', 'the expense', 'the total'}:
        return None
    return value[:200]


def _text_facts(text: str, allow_bare_amount: bool = False) -> dict[str, Any]:
    matches = list(MONEY.finditer(text))
    money_match = next(
        (
            match for match in matches
            if match.group('symbol') or match.group('prefix') or match.group('suffix')
        ),
        None,
    )
    if money_match is None and (EXPENSE_CUE.search(text) or allow_bare_amount):
        money_match = next(iter(matches), None)

    amount_cents = _amount(money_match) if money_match else None
    currency, currency_source = _currency(money_match) if money_match else ('CAD', 'group_default')
    date_text = _date_text(text)
    description = None
    merchant = None

    if money_match:
        before = text[:money_match.start()].strip(' \t\r\n,.;:!?-')
        after = text[money_match.end():].strip(' \t\r\n,.;:!?-')
        for_match = re.match(r'^(?:for|on)\s+(.+)$', after, re.IGNORECASE)
        if for_match:
            description = _clean_phrase(for_match.group(1))
        else:
            description = _clean_phrase(before)
        if description and re.search(r'\bat\b', description, re.IGNORECASE):
            description, merchant = re.split(r'\s+at\s+', description, maxsplit=1, flags=re.IGNORECASE)
            description = _clean_phrase(description)
            merchant = _clean_phrase(merchant)
        if merchant is None:
            at_match = re.search(r'\bat\s+(.+)$', after, re.IGNORECASE)
            if at_match:
                merchant = _clean_phrase(at_match.group(1))
    else:
        for_match = re.search(r'\b(?:for|on)\s+(.+)$', text, re.IGNORECASE)
        if for_match:
            description = _clean_phrase(for_match.group(1))

    return {
        'description': description,
        'merchant': merchant,
        'amount_cents': amount_cents,
        'currency': currency,
        'currency_source': currency_source,
        'occurred_on_text': date_text,
        'items': [],
    }


def make_expense_mention(values: dict[str, Any]) -> dict[str, Any]:
    currency_source = values.get('currency_source')
    fields = {
        key: values[key]
        for key in ('description', 'merchant', 'amount_cents', 'currency', 'occurred_on_text', 'items')
        if key in values
    }
    if isinstance(fields.get('currency'), str):
        fields['currency'] = fields['currency'].upper()
    details = ExpenseMention.model_validate(fields)
    payload = details.model_dump(mode='json')
    explicit_currency = payload['currency'] is not None
    payload['schema_version'] = 1
    payload['kind'] = 'expense_mention'
    payload['currency'] = payload['currency'] or 'CAD'
    payload['currency_source'] = currency_source or ('explicit' if explicit_currency else 'group_default')
    missing = [
        key for key in ('amount_cents', 'description')
        if payload[key] is None or payload[key] == ''
    ]
    payload['missing_fields'] = missing
    payload['status'] = 'needs_clarification' if missing else 'captured'
    return payload


def _pending_from_history(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not history or history[-1].get('actor') != 'bouncer':
        return None
    context = history[-1].get('reply_context') or {}
    if context.get('kind') != 'expense_mention':
        return None
    message_id = context.get('message_id')
    for message in reversed(history[:-1]):
        if message.get('id') == message_id:
            extraction = message.get('extraction')
            if extraction and extraction.get('kind') == 'expense_mention':
                return extraction
    return None


def extract_expense_mention(
    text: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    history = history or []
    pending = _pending_from_history(history)
    facts = _text_facts(text, allow_bare_amount=bool(pending))
    if pending:
        previous = ExpenseMention.model_validate({
            key: pending.get(key)
            for key in ('description', 'merchant', 'amount_cents', 'currency', 'occurred_on_text', 'items')
        })
        merged = previous.model_dump(mode='json')
        merged['currency_source'] = pending.get('currency_source', 'group_default')
        if facts['amount_cents'] is not None:
            merged['amount_cents'] = facts['amount_cents']
            if facts['currency_source'] == 'explicit':
                merged['currency'] = facts['currency']
                merged['currency_source'] = facts['currency_source']
        if facts['description']:
            merged['description'] = facts['description']
        elif facts['amount_cents'] is None and 'description' in pending.get('missing_fields', []):
            answer = _clean_phrase(text)
            if answer:
                merged['description'] = answer
        if facts['merchant']:
            merged['merchant'] = facts['merchant']
        if facts['occurred_on_text']:
            merged['occurred_on_text'] = facts['occurred_on_text']
        if facts['items']:
            merged['items'] = facts['items']
        mention = make_expense_mention(merged)
        for key in ('reported_by', 'source_message_id'):
            if pending.get(key):
                mention[key] = pending[key]
        return mention

    if EXPENSE_QUESTION_OR_ESTIMATE.search(text) and not re.search(r'\b(paid|spent|receipt|bill)\b', text, re.IGNORECASE):
        return None
    if not EXPENSE_CUE.search(text) and not (
        facts['amount_cents'] is not None and PURCHASE_CONTEXT.search(text)
    ):
        return None
    return make_expense_mention(facts)


def expense_reply(mention: dict[str, Any]) -> str:
    if 'amount_cents' in mention['missing_fields'] and 'description' in mention['missing_fields']:
        return 'I can keep track of that. What was the expense for, and what was the total?'
    if 'amount_cents' in mention['missing_fields']:
        return f"I've noted {mention['description']}. What was the total amount?"
    if 'description' in mention['missing_fields']:
        cents = mention['amount_cents']
        return f"Got it, {mention['currency']} {cents // 100}.{cents % 100:02d}. What was that for?"
    cents = mention['amount_cents']
    where = f" at {mention['merchant']}" if mention['merchant'] else ''
    return (
        f"Got it — {mention['description']}{where} was {mention['currency']} {cents // 100}.{cents % 100:02d}. "
        "I've captured those details in this chat; I haven't added a shared expense yet. "
        "Was that the full total, including tax and tip?"
    )
