"""
Rule-based sentiment analysis for the agent pipeline.

Replaces the previous LLM-based sentiment detection (which asked Groq to
infer tone from a prompt). Sentiment is now computed programmatically.

Backends
--------
Default: ``vaderSentiment`` — rule-based, no model download, near-instant,
pure Python (English-focused). Selected via ``SENTIMENT_BACKEND=vader``.

Optional: a HuggingFace ``transformers`` pipeline (e.g.
``distilbert-base-uncased-finetuned-sst-2-english`` or a multilingual model
such as ``nlptown/bert-base-multilingual-uncased-sentiment``) via
``SENTIMENT_BACKEND=transformers`` and ``SENTIMENT_MODEL=...``. The
transformers import is deferred so the VADER path has no heavy dependency.

Both backends produce the same schema the LangGraph pipeline consumes:

    {emotion, intensity, signals, pacing_needed, response_length, note}
"""
import os

BACKEND = os.getenv("SENTIMENT_BACKEND", "vader").strip().lower()
TRANSFORMERS_MODEL = os.getenv(
    "SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
)

_EMOTION_NOTES = {
    "stressed": "Strong negative tone — keep it brief, ground first, no advice.",
    "anxious": "Negative tone — slow down, one small thing at a time.",
    "sad": "Mildly negative tone — validate before anything else.",
    "neutral": "Neutral state detected.",
    "hopeful": "Slightly positive tone — keep it light and encouraging.",
    "energized": "Positive tone — direct and energizing, no warm-up.",
}

_NEUTRAL_FALLBACK = {
    "emotion": "neutral",
    "intensity": 0.5,
    "signals": [],
    "pacing_needed": "normal",
    "response_length": "medium",
    "note": "",
}


def _detect_signals(text: str) -> list:
    signals = []
    stripped = text.strip()
    if any(c in text for c in "!?"):
        signals.append("punctuation")
    if stripped.isupper():
        signals.append("all caps")
    if len(stripped.split()) <= 6:
        signals.append("short message")
    if len(text) > 200:
        signals.append("long message")
    return signals


def _classify(compound: float) -> dict:
    """Map a sentiment score in [-1, 1] to the pipeline's emotion schema."""
    if compound < -0.45:
        return {"emotion": "stressed", "pacing_needed": "slow", "response_length": "very_short"}
    if compound < -0.25:
        return {"emotion": "anxious", "pacing_needed": "slow", "response_length": "short"}
    if compound < -0.05:
        return {"emotion": "sad", "pacing_needed": "slow", "response_length": "short"}
    if compound <= 0.05:
        return {"emotion": "neutral", "pacing_needed": "normal", "response_length": "medium"}
    if compound <= 0.4:
        return {"emotion": "hopeful", "pacing_needed": "normal", "response_length": "medium"}
    return {"emotion": "energized", "pacing_needed": "fast", "response_length": "medium"}


def _build_result(compound: float, signals: list) -> dict:
    classified = _classify(compound)
    emotion = classified["emotion"]
    return {
        "emotion": emotion,
        "intensity": round(min(1.0, abs(compound) * 1.3), 3),
        "signals": signals,
        "pacing_needed": classified["pacing_needed"],
        "response_length": classified["response_length"],
        "note": _EMOTION_NOTES.get(emotion, ""),
    }


def _vader_compound(text: str) -> float:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    return analyzer.polarity_scores(text)["compound"]


_transformers_pipeline = None


def _transformers_compound(text: str) -> float:
    """Synthetic compound in [-1, 1] from a transformers sentiment pipeline."""
    global _transformers_pipeline
    if _transformers_pipeline is None:
        from transformers import pipeline

        _transformers_pipeline = pipeline("sentiment-analysis", model=TRANSFORMERS_MODEL)

    result = _transformers_pipeline(text[:512])[0]
    label = str(result.get("label", "")).upper()
    score = float(result.get("score", 0.5))

    if "STAR" in label:
        stars = int(label[0])
        return (stars - 3) / 2
    if "POSITIVE" in label or "LABEL_1" in label:
        return score
    if "NEGATIVE" in label or "LABEL_0" in label:
        return -score
    return 0.0


def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of ``text`` and return the pipeline's sentiment dict."""
    if not text or not text.strip():
        return dict(_NEUTRAL_FALLBACK)

    signals = _detect_signals(text)

    try:
        if BACKEND == "transformers":
            compound = _transformers_compound(text)
        else:
            compound = _vader_compound(text)
    except Exception as e:  # pragma: no cover - defensive fallback
        print(f"[sentiment] Analyzer failed ({BACKEND}): {e}")
        return dict(_NEUTRAL_FALLBACK)

    result = _build_result(compound, signals)
    print(f"[sentiment] {result['emotion']} (intensity: {result['intensity']}) — {result['note'] or 'no note'}")
    return result
