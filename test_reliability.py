"""
Reliability tests for the user-facing improvements.
Run: python3 test_reliability.py
Requires the backend to be running on localhost:8000.
"""
import requests, json, sys, time, re

API = "http://localhost:8000"
USER_ID = "399de5aa-fbde-4dbd-85d7-c5825b5c2a95"
PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")

def chat(message, agent="general", conv_id=None):
    body = {"message": message, "user_id": USER_ID, "agent_type": agent}
    if conv_id:
        body["conversation_id"] = conv_id
    r = requests.post(f"{API}/chat", json=body, timeout=180)
    return r.json()

print("=" * 60)
print("RELIABILITY TESTS")
print("=" * 60)

# ── 1. Sentiment Enforcement ────────────────────────────────────────────────
print("\n--- 1. Sentiment Enforcement ---")

# 1a. Stressed message → very_short response (max 2 sentences)
r = chat("I am so stressed I can't breathe", "vibber")
resp = r["response"]
sentences = [s for s in re.split(r'(?<=[.!?])\s+', resp.strip()) if s]
test("Stressed → ≤2 sentences", len(sentences) <= 2,
     f"Got {len(sentences)} sentences: {resp[:100]}")

# 1b. Anxious message → short response (max 3 sentences)
r = chat("I feel really anxious about my presentation tomorrow", "vibber")
resp = r["response"]
sentences = [s for s in re.split(r'(?<=[.!?])\s+', resp.strip()) if s]
test("Anxious → ≤3 sentences", len(sentences) <= 3,
     f"Got {len(sentences)} sentences: {resp[:100]}")

# ── 2. Sustained Distress Pattern ───────────────────────────────────────────
print("\n--- 2. Sustained Distress Pattern ---")

# Send 3 stressed messages in a row, check the 4th is very short
for i in range(3):
    chat(f"I feel terrible day {i+1}", "vibber")
    time.sleep(0.5)

r = chat("What should I do to feel better", "vibber")
resp = r["response"]
no_advice = not any(w in resp.lower() for w in ["you should", "try ", "have you considered", "why don't"])
sentences = [s for s in re.split(r'(?<=[.!?])\s+', resp.strip()) if s]
test("Sustained distress → no advice language", no_advice,
     f"Found advice language in: {resp[:120]}")
test("Sustained distress → very short (≤2)", len(sentences) <= 2,
     f"Got {len(sentences)} sentences")

# ── 3. Agent Voice Distinctness ─────────────────────────────────────────────
print("\n--- 3. Agent Voice Distinctness ---")

# Same message to different agents — responses should be clearly different
r1 = chat("I feel stuck", "vibber")
r2 = chat("I feel stuck", "inspirer")
vibber_resp = r1["response"].lower()
inspirer_resp = r2["response"].lower()

# Vibber should validate/feel, Inspirer should challenge/decide
vibber_validates = any(w in vibber_resp for w in ["feel", "where", "body", "hear you", "that makes sense"])
inspirer_challenges = any(w in inspirer_resp for w in ["what's stopping", "decision", "avoiding", "which kind", "stuck on what"])
test("Vibber validates feelings", vibber_validates, f"Vibber: {vibber_resp[:100]}")
test("Inspirer challenges/decides", inspirer_challenges, f"Inspirer: {inspirer_resp[:100]}")
test("Responses are different", vibber_resp != inspirer_resp)

# ── 4. Bridger Follow-up Scheduling ─────────────────────────────────────────
print("\n--- 4. Bridger Follow-up Scheduling ---")

r = chat("Add Marie Curie (researcher at CNRS) to my network. I met her at a physics conference.", "bridger")
time.sleep(0.5)
resp = r.get("response", "")
test("Bridger processes add_contact", len(resp) > 0, resp[:80])

# Check followups were scheduled
r2 = requests.get(f"{API}/followups/{USER_ID}", timeout=10)
fups = r2.json().get("followups", [])
bridger_fups = [f for f in fups if f.get("agent_type") == "bridger"]
test("Bridger follow-up scheduled", len(bridger_fups) >= 1,
     f"Found {len(bridger_fups)} bridger follow-ups")

# ── 5. Inspirer Commitment Tracking ──────────────────────────────────────────
print("\n--- 5. Inspirer Commitment Tracking ---")

r = chat("I will reach out to three potential users by Friday", "inspirer")
time.sleep(0.5)

r2 = requests.get(f"{API}/followups/{USER_ID}", timeout=10)
comms = r2.json().get("commitments", [])
test("Commitment saved", len(comms) >= 1,
     f"Found {len(comms)} commitments: {[c['description'][:40] for c in comms]}")

# ── 6. API Health ────────────────────────────────────────────────────────────
print("\n--- 6. API Health ---")

try:
    r = requests.get(f"{API}/health", timeout=5)
    test("Backend health check", r.status_code == 200 and r.json().get("status") == "ok")
except Exception as e:
    test("Backend health check", False, str(e))

try:
    r = requests.get(f"{API}/followups/{USER_ID}", timeout=5)
    test("Followups API", r.status_code == 200)
except Exception as e:
    test("Followups API", False, str(e))

# ── 7. PCL Sentence Variance Check ───────────────────────────────────────────
print("\n--- 7. PCL Sentence Variance Check ---")

from agents.pcl import _check_sentence_variance
# Uniform sentences → True (needs rewrite)
test("Uniform sentences flagged",
     _check_sentence_variance("Short. Another short one. Yet another same.") == True)
# Varied sentences → False (OK)
test("Varied sentences pass",
     _check_sentence_variance("Short. This one is significantly longer and more detailed. Punchy. Medium length one.") == False)

# ── 8. Sentiment Enforcement Function ────────────────────────────────────────
print("\n--- 8. Sentiment Enforcement Function ---")

from agents.sentiment import enforce_response_length
long_text = "First sentence. Second sentence here. Third one right here. Fourth sentence. Fifth one."
result = enforce_response_length(long_text, 2)
test("enforce_response_length to 2", len(result.split(". ")) <= 2 and "First sentence." in result,
     f"Got: {result}")

result = enforce_response_length(long_text, 3)
test("enforce_response_length to 3", len(result.split(". ")) <= 3,
     f"Got: {result}")

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 60)

if FAIL > 0:
    sys.exit(1)
