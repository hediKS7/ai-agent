from langchain_core.tools import tool
from ddgs import DDGS
import pandas as pd
from io import StringIO

# ── Web search configuration ──────────────────────────────────────────────────
WEB_SEARCH_MAX_USES = 20
WEB_SEARCH_ALLOWED_DOMAINS = [
    "linkedin.com", "github.com", "arxiv.org", "scholar.google.com",
    "coursera.org", "edx.org", "huggingface.co", "openai.com",
    "mistral.ai", "anthropic.com", "deepmind.com", "research.google.com",
    "ieee.org", "acm.org", "nature.com", "medium.com", "towardsdatascience.com",
    "lemonde.fr", "techcrunch.com", "wired.com"
]

_search_call_count = {}  # Track per-user usage

@tool
def web_search(query: str, user_id: str = "default") -> str:
    """
    Search the web for current information.
    Max uses: 20 per session.
    Searches across allowed domains only when specified.
    """
    # Check max_uses
    count = _search_call_count.get(user_id, 0)
    if count >= WEB_SEARCH_MAX_USES:
        return f"Web search limit reached ({WEB_SEARCH_MAX_USES} searches per session)."
    _search_call_count[user_id] = count + 1

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No results found."
        return "\n\n".join(
            f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body'][:200]}"
            for r in results
        )
    except Exception as e:
        return f"Search error: {e}"

@tool
def web_search_domain(query: str, domain: str = "") -> str:
    """
    Search within a specific allowed domain.
    Example: web_search_domain('LangGraph tutorial', 'github.com')
    """
    if domain and domain not in WEB_SEARCH_ALLOWED_DOMAINS:
        return f"Domain {domain} is not in the allowed list."
    full_query = f"site:{domain} {query}" if domain else query
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(full_query, max_results=3))
        if not results:
            return "No results found."
        return "\n\n".join(
            f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body'][:200]}"
            for r in results
        )
    except Exception as e:
        return f"Search error: {e}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a numeric math expression. Do NOT use for time or scheduling."""
    try:
        forbidden = ["AM", "PM", ":", "hour", "minute", "time", "day"]
        if any(w in expression for w in forbidden):
            return "Error: use direct reasoning for time/scheduling, not calculator."
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"

@tool
def analyze_csv(csv_content: str) -> str:
    """Analyze CSV data and return summary statistics."""
    try:
        df = pd.read_csv(StringIO(csv_content))
        return df.describe().to_string()
    except Exception as e:
        return f"CSV analysis error: {e}"

def get_tools():
    return [web_search, web_search_domain, calculator, analyze_csv]

def reset_search_count(user_id: str):
    """Reset search count for a user (call at session start)."""
    _search_call_count[user_id] = 0
