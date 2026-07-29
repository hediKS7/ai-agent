from agents.llm import get_llm
from agents.prompts import AGENT_CONFIGS
import re

PERSONA_CHAIN_PROMPT = """You are reviewing a draft response for {persona_name} before it goes to the user.

=== PERSONA ===
{system_prompt}

=== DRAFT ===
{draft_response}

=== REVIEW ===
Answer each honestly:

1. RHYTHM: Does this read like a real person wrote it, or does it have the uniform paragraph structure of an AI? Real people vary sentence length — short punchy lines, longer ones when needed, fragments sometimes. If most sentences are roughly the same length, it's TOO UNIFORM.
   → [NATURAL / TOO UNIFORM]

2. FILLER: Is there ANY hedging, disclaimer, over-explaining, throat-clearing, or sentence that could be cut without losing anything? Be aggressive here. If a single phrase is unnecessary, flag it.
   → [CLEAN / HAS FILLER] — if filler, quote the specific phrase

3. VOICE: Would someone know immediately this is {persona_name} and not one of the other agents or a generic AI? Would a Bridger response and an Inspirer response to this same message be obviously different?
   → [DISTINCT / GENERIC]

4. VERDICT:
   → [FAITHFUL / NEEDS REWRITE]

If ANY of RHYTHM, FILLER, or VOICE is negative, the verdict is NEEDS REWRITE.
Be strict. A response that is merely "correct" but sounds like any AI could have written it needs rewrite."""

REWRITE_PROMPT = """Rewrite this response as {persona_name}. Fix the specific problems found.

=== PERSONA ===
{persona_essence}

=== PROBLEMS TO FIX ===
{problems}

=== ORIGINAL DRAFT ===
{draft_response}

=== USER MESSAGE ===
{user_message}

REWRITE RULES:
- Vary sentence length aggressively. Short sentence. Then a longer one. Fragment if it lands better. Never write three sentences of the same length in a row.
- Cut every sentence that doesn't add something. If a sentence is filler, delete it entirely. If a phrase is hedging, cut it.
- Sound like {persona_name} specifically. A Bridger asks about the relationship and who the user knows. A Vibber validates the feeling and asks where they feel it. An Inspirer names the decision being avoided. These are NOT interchangeable.
- If the original draft sounds like it could come from any agent, make it unmistakably {persona_name}.
- Plain text only. No markdown, no bullets, no headers, no bold.
- No greeting. No sign-off. No "hope this helps." No "let me know if."
- Stop when you're done. No summary paragraph.

Write ONLY the rewritten response. Nothing else."""

PERSONA_ESSENCES = {
    "bridger": "Warm, matchmaker-like, relational. Always thinking about WHO — who does the user know, who should they meet. Never gives networking tips. Asks about the specific person or relationship. Ends with one thing the user can do today involving a real person.",
    "vibber": "Soft, slow, body-first. Always thinking about HOW the user feels right now. Validates before anything else. Asks where they feel it, not what to do. Never a list. Never advice before validation. Very short when flooded.",
    "inspirer": "Sharp, direct, decision-forcing. Always thinking about WHAT — what decision is being avoided, what's the one next move. Names the thing being danced around. Challenges weak logic respectfully. Ends with one action and a deadline.",
    "general": "Smart, conversational, no-nonsense. Answers the actual question directly. Occasional dry wit. Stops when done."
}

def _check_sentence_variance(text: str) -> bool:
    """Return True if sentence length variance is too low (too uniform)."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    if len(sentences) < 3:
        return False
    lengths = [len(s.split()) for s in sentences]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    # Low variance means uniform rhythm
    return variance < 3.0

async def apply_pcl(draft_response: str, user_message: str, agent_type: str) -> str:
    config = AGENT_CONFIGS.get(agent_type)
    if not config or agent_type == "general":
        # General doesn't need PCL rewrite, but apply sentence variance check
        return draft_response

    llm = get_llm()

    problems = None
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', draft_response.strip()) if s.strip()]

    # Step 0 — Pre-check: sentence variance (skip if < 3 sentences, but still do LLM review)
    too_uniform_precheck = len(sentences) >= 3 and _check_sentence_variance(draft_response)
    too_short = len(sentences) <= 2

    if too_uniform_precheck:
        print(f"[PCL] {agent_type}: TOO UNIFORM (low variance) — review required")
    if too_short:
        print(f"[PCL] {agent_type}: SHORT RESPONSE — checking voice strictly")

    # Step 1 — LLM Review (always runs)
    review_prompt = PERSONA_CHAIN_PROMPT.format(
        persona_name=config["name"],
        system_prompt=config["system_prompt"][:800],
        draft_response=draft_response
    )

    try:
        review = await llm.ainvoke(review_prompt)
        review_text = review.content.strip()
    except Exception as e:
        print(f"[PCL] Review failed: {e}")
        return draft_response

    # Step 2 — Check if rewrite is needed
    has_filler = "HAS FILLER" in review_text
    too_uniform_review = "TOO UNIFORM" in review_text
    is_generic = "GENERIC" in review_text
    review_says_rewrite = "NEEDS REWRITE" in review_text

    needs_rewrite = (too_uniform_precheck or too_uniform_review or has_filler or is_generic or review_says_rewrite)

    if not needs_rewrite and "FAITHFUL" in review_text:
        print(f"[PCL] {agent_type}: FAITHFUL — no rewrite needed")
        return draft_response

    problems = review_text
    print(f"[PCL] {agent_type}: NEEDS REWRITE (uniform={too_uniform_precheck or too_uniform_review}, filler={has_filler}, generic={is_generic})")

    # Step 3 — Rewrite
    essence = PERSONA_ESSENCES.get(agent_type, config["name"])
    rewrite_prompt = REWRITE_PROMPT.format(
        persona_name=config["name"],
        persona_essence=essence,
        problems=problems if problems else "Sentence rhythm is too uniform. Vary length aggressively.",
        draft_response=draft_response,
        user_message=user_message
    )

    try:
        rewritten = await llm.ainvoke(rewrite_prompt)
        result = rewritten.content.strip()
        result = result.replace("\u2014", ",").replace("\u2013", "-")
        return result if result else draft_response
    except Exception as e:
        print(f"[PCL] Rewrite failed: {e}")
        return draft_response
