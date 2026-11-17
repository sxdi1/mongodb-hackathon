"""Deterministic presentation dialogue; no provider calls or simulated writes."""
import re
from .expense_mentions import expense_reply

SCRIPT = {
    'hey bouncer!': "Hey Alex, Sara and Dev! Ready for our Montreal evening? Let's choose dinner, check everyone's needs, and keep track of the bill.",
    'i want tacos in montreal': 'Our scripted option is Taco Night, a fictional dinner scenario in Montreal. We will compare it against the group budget and dietary needs. What is our budget per person?',
    'our budget is $30 per person': 'Scenario budget: CAD 30 each, CAD 90 for three people. Dinner at 7 pm, followed by a free walk in Old Montreal. Next, let\'s check dietary needs.',
    'we need halal and nut-free options': 'Dietary checkpoint: REVIEW. We need trusted confirmation of halal and nut-free options before approving dinner. The scripted restaurant is not verified; no booking has been made.',
    'we paid $90 for dinner': 'Dinner total captured: CAD 90.00. For this scenario, Alex paid for Alex, Sara and Dev. Ask me to split it equally to preview what each person owes; no money will move.',
    'split it equally': 'Scripted CAD 90 dinner split: Alex CAD 30, Sara CAD 30, Dev CAD 30. Assuming Alex paid, Sara and Dev would each owe Alex CAD 30. This is a preview, not a payment or ledger entry.',
    'recap': 'Scripted recap: a CAD 90 dinner for three, CAD 30 each, followed by an Old Montreal walk. Dietary verification remains unresolved. The conversation and reported bill are saved; no reservation, payment or shared ledger expense was created.',
}


def reply(text, history, extraction):
    message = ' '.join(text.lower().split())
    if message in SCRIPT:
        return SCRIPT[message]
    if extraction:
        return expense_reply(extraction)
    if re.search(r'\b(split|owe|owes)\b', message):
        mention = next((m.get('extraction') for m in reversed(history)
                        if (m.get('extraction') or {}).get('status') == 'captured'), None)
        if mention:
            cents = mention['amount_cents']
            base, remainder = divmod(cents, 3)
            shares = [base + (i < remainder) for i in range(3)]
            return 'Equal-split preview for Alex, Sara and Dev: ' + ', '.join(
                f'{name}: {mention["currency"]} {share / 100:.2f}'
                for name, share in zip(['Alex', 'Sara', 'Dev'], shares)
            ) + '. This is a calculation only; no payments or ledger entries were made.'
        return 'What was the full bill? Try "We paid $90 for dinner" and I can preview a three-person split.'
    if re.search(r'\b(halal|allerg|nuts?|nut-free|vegetarian|dietary)\b', message):
        return 'Let\'s confirm halal, vegetarian and nut-free options directly with the restaurant. A menu claim alone is not verified dietary evidence, so the plan still needs review.'
    if re.search(r'\b(summary|recap|itinerary)\b', message):
        return 'Demo plan: dinner in Montreal, then a walk in Old Montreal. Confirm the group budget, dinner time and dietary requirements before agreeing. Nothing has been booked. Report the dinner total here when you have it.'
    if re.search(r'\b(book|reserve|confirm)\b', message):
        return 'I can help prepare the plan, but I cannot make reservations. Confirm dietary options and availability with the restaurant before booking.'
    if re.search(r'\b(cheap|cheaper|budget)\b|\$\d+', message):
        return 'For this demo, let\'s target CAD 30 per person including tax and tip, then a free walk in Old Montreal. Does 7 pm work for everyone?'
    if re.search(r'\b(7|seven|tonight|tomorrow|yes|sounds good)\b', message):
        return 'Great, 7 pm is our proposed dinner time in this scripted scenario. We still need to confirm dietary options and availability. After dinner, we can plan a walk in Old Montreal.'
    if re.search(r'\b(tacos?|chinese|restaurant|dinner|food)\b', message):
        cuisine = 'tacos' if 'taco' in message else 'Chinese food' if 'chinese' in message else 'dinner'
        return f'Let\'s plan {cuisine} in Montreal. What is everyone\'s budget per person? This scripted demo does not fetch live restaurant listings or availability.'
    if re.search(r'\b(hi|hey|hello|start)\b', message):
        return 'Hey everyone! Let\'s plan our Montreal evening. Tell me what you want to eat, your budget, or a bill you want to keep track of.'
    if re.search(r'\b(thanks|thank)\b', message):
        return 'You\'re welcome! Ask for a recap, or share a dinner bill and I can help calculate the split.'
    return 'For this demo, try "I want tacos in Montreal", "Our budget is $30 per person", "We paid $90 for dinner", or "Split it equally".'
