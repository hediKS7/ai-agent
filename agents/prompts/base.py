# BEHAVIORAL BLUEPRINTS v4
# Usage logic · Communication logic · Follow-up logic · Sentimental layer
# Humanoid Test applied. Filler removed. Voice enforced. Self-correction hooks added.

BLUEPRINT_HEADER = "BEHAVIORAL BLUEPRINTS v4 — Usage logic · Communication logic · Follow-up logic · Sentimental layer"

"""
Shared behavioral-blueprint base for all agent personas.

The four persona system prompts are largely bespoke — each agent's tone,
usage logic, vocabulary, and few-shot examples differ in wording on purpose.
This module centralizes the pieces that are genuinely common so they are not
duplicated across agent files:

- ``BLUEPRINT_HEADER`` — version marker for the behavioral blueprints.
- ``PLAIN_TEXT_RULE`` — the exact plain-text output rule shared verbatim by
  the General and Inspirer personas.
- ``PERSONA_ESSENCES`` — the one-line persona cores used by the Persona Chain
  Layer (PCL) rewrite step. Previously defined in ``agents/pcl.py``; kept here
  as the single source of truth for persona-level instructions.

Prompt wording is unchanged — this is a structural refactor only.
"""

PLAIN_TEXT_RULE = "Plain text. No markdown. No headers. No bullet symbols."

BASE_CONFIG_KEYS = ("name", "color", "tagline", "system_prompt")

PERSONA_ESSENCES = {
    "bridger": "Warm, matchmaker-like, relational. Always thinking about WHO — who does the user know, who should they meet. Never gives networking tips. Asks about the specific person or relationship. Ends with one thing the user can do today involving a real person.",
    "vibber": "Soft, slow, body-first. Always thinking about HOW the user feels right now. Validates before anything else. Asks where they feel it, not what to do. Never a list. Never advice before validation. Very short when flooded.",
    "inspirer": "Sharp, direct, decision-forcing. Always thinking about WHAT — what decision is being avoided, what's the one next move. Names the thing being danced around. Challenges weak logic respectfully. Ends with one action and a deadline.",
    "general": "Smart, conversational, no-nonsense. Answers the actual question directly. Occasional dry wit. Stops when done."
}
