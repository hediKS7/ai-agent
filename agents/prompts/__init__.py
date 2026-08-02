"""Agent persona prompts package.

Aggregates the per-persona CONFIG dicts so the rest of the pipeline keeps
using ``from agents.prompts import AGENT_CONFIGS`` unchanged.

Shared blueprint rules and persona essences live in ``agents.prompts.base``.
"""

from agents.prompts.base import PLAIN_TEXT_RULE, PERSONA_ESSENCES, BLUEPRINT_HEADER
from agents.prompts import general, bridger, vibber, inspirer

AGENT_CONFIGS = {
    "general": general.CONFIG,
    "bridger": bridger.CONFIG,
    "vibber": vibber.CONFIG,
    "inspirer": inspirer.CONFIG,
}

__all__ = [
    "AGENT_CONFIGS",
    "PLAIN_TEXT_RULE",
    "PERSONA_ESSENCES",
    "BLUEPRINT_HEADER",
]
