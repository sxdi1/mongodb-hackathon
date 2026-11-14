import os
import re
from typing import Any

from .expense_mentions import extract_expense_mention
from .models import ConversationUnderstanding

SYSTEM = '''You are Bouncer, a helpful participant in a group chat.
Read the latest message together with recent conversation context.
Return important keywords, a brief intent, explicit entities such as people, places, amounts, dates, and items, and a concise conversational reply.
The reply must directly acknowledge or answer the latest message using only information in the chat. Do not invent facts, make bookings, spend money, or take actions.
If the user asks for information that is not available, say what is missing and ask one useful follow-up question.
Use recent conversation only to resolve references such as “there”, “that”, or “the cheaper one”.
'''

STOP_WORDS = {
    'a', 'about', 'actually', 'am', 'an', 'and', 'are', 'at', 'be', 'been',
    'can', 'could', 'did', 'do', 'does', 'for', 'from', 'get', 'got', 'had',
    'has', 'have', 'hey', 'hi', 'how', 'i', 'in', 'is', 'it', 'just', 'me',
    'my', 'of', 'on', 'or', 'our', 'please', 'so', 'that', 'the', 'there',
    'they', 'this', 'to', 'us', 'was', 'we', 'what', 'when', 'where', 'which',
    'who', 'will', 'with', 'would', 'you', 'your',
}


def _local_understanding(text: str) -> dict[str, Any]:
    tokens = re.findall(r'\$?\d+(?:[.,]\d{1,2})?|[A-Za-z][A-Za-z0-9\'-]*', text)
    keywords: list[str] = []
    for token in tokens:
        normalized = token.strip("'-").lower()
        if normalized and normalized not in STOP_WORDS and normalized not in keywords:
            keywords.append(normalized)
        if len(keywords) == 12:
            break
    if not keywords:
        keywords = ['general chat']
    if re.search(r'\b(hi|hello|hey)\b', text, re.IGNORECASE):
        intent = 'greeting'
    elif re.search(r'\b(paid|spent|cost|costed|expense|bill|receipt)\b', text, re.IGNORECASE):
        intent = 'reporting an expense'
    elif re.search(r'\b(what|where|when|who|why|how|can|could|should)\b', text, re.IGNORECASE):
        intent = 'asking a question'
    elif re.search(r'\b(plan|propose|visit|go|try)\b', text, re.IGNORECASE):
        intent = 'suggesting a plan'
    else:
        intent = 'sharing information'
    return {'keywords':keywords, 'intent':intent, 'entities':[]}


def _response(analysis: dict[str, Any]) -> str:
    if analysis.get('reply'):
        return analysis['reply'].strip()
    keywords = ', '.join(analysis['keywords'])
    intent = analysis['intent'].strip()
    if intent:
        return f'I understood these keywords: {keywords}. It sounds like you’re {intent}.'
    return f'I understood these keywords: {keywords}.'


def _result(
    text: str,
    history: list[dict[str, Any]],
    source: str,
    status: str,
) -> dict[str, Any]:
    analysis = ConversationUnderstanding.model_validate(_local_understanding(text)).model_dump(mode='json')
    extraction = extract_expense_mention(text, history)
    return {
        'reply':_response(analysis),
        'tools':[],
        'analysis':analysis,
        'analysis_source':source,
        'extraction':extraction,
        'agent_status':status,
    }


def fallback(envelope) -> dict[str, Any]:
    """Return a local keyword summary when Gemini is unavailable."""
    return _result(envelope.text, envelope.history, 'local_fallback', 'fallback')


def run(envelope) -> dict[str, Any]:
    if envelope.image:
        return {
            'reply':'I can’t analyze images in this mode. Please type the message you want me to understand.',
            'tools':[],
            'analysis':None,
            'analysis_source':'none',
            'extraction':None,
            'agent_status':'ok',
        }

    if os.getenv('AGENT_MODE', 'mock') != 'gemini':
        return _result(envelope.text, envelope.history, 'local', 'ok')

    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=os.environ['GEMINI_API_KEY'],
        http_options=types.HttpOptions(timeout=30000),
    )
    contents = [
        types.Content(
            role='model' if message['actor'] == 'bouncer' else 'user',
            parts=[types.Part.from_text(text=f"{message['name']}: {message['text']}")],
        )
        for message in envelope.history
    ]
    contents.append(types.Content(role='user', parts=[
        types.Part.from_text(text=f'{envelope.actor_name or envelope.actor}: {envelope.text}')
    ]))
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            'keywords': types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                min_items=1,
                max_items=12,
            ),
            'intent': types.Schema(type=types.Type.STRING, min_length=1, max_length=120),
            'entities': types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                max_items=12,
            ),
            'reply': types.Schema(type=types.Type.STRING, min_length=1, max_length=500),
        },
        required=['keywords', 'intent', 'entities', 'reply'],
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        response_mime_type='application/json',
        response_schema=response_schema,
        temperature=0,
    )
    response = client.models.generate_content(
        model=os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview'),
        contents=contents,
        config=config,
    )
    if not response.text:
        raise RuntimeError('Gemini returned no structured message understanding')
    analysis = ConversationUnderstanding.model_validate_json(response.text).model_dump(mode='json')
    extraction = extract_expense_mention(envelope.text, envelope.history)
    return {
        'reply':_response(analysis),
        'tools':[],
        'analysis':analysis,
        'analysis_source':'gemini',
        'extraction':extraction,
        'agent_status':'ok',
    }
