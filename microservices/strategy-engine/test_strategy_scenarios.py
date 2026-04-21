import os
import json
from fastapi.testclient import TestClient

os.environ["INTERNAL_SERVICE_KEY"] = "test-secret-key-123"

from app.main import app

client = TestClient(app)
INTERNAL_KEY = "test-secret-key-123"

def run_tests():
    headers = {"X-Internal-Key": INTERNAL_KEY}
    results = []

    def test_case(name, input_data, expected_action=None, expected_key=None, description=""):
        print(f"  → Running: {name}")
        response = client.post("/decide", json=input_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            action = result.get("action")
            resp_key = result.get("response_key")

            # Validation
            action_pass = (expected_action is None) or (action == expected_action)
            key_pass    = (expected_key is None)    or (resp_key == expected_key)
            verdict     = "✅ PASS" if (action_pass and key_pass) else "❌ FAIL"

            results.append({
                "Test Case":    name,
                "Description":  description,
                "Status":       "Success",
                "Verdict":      verdict,
                "Expected Action":  expected_action or "Any",
                "Expected Key":     expected_key    or "Any",
                "Input":        input_data,
                "Output":       result,
                "Action":       action,
                "ResponseKey":  resp_key,
                "CounterPrice": result.get("counter_price"),
                "Metadata":     result.get("decision_metadata", {}),
            })
        else:
            results.append({
                "Test Case":   name,
                "Description": description,
                "Status":      f"Failed HTTP {response.status_code}",
                "Verdict":     "❌ FAIL",
                "Input":       input_data,
                "Output":      response.text,
            })

    # =========================================================================
    # BASE CONFIG
    # =========================================================================
    mam           = 40000.0
    asking_price  = 50000.0

    print("\n" + "="*60)
    print("  V2.0 STRATEGY ENGINE — FULL TEST SUITE")
    print("="*60)

    # =========================================================================
    # SECTION 1: NON-OFFER INTENTS
    # =========================================================================
    print("\n[1] NON-OFFER INTENTS")

    test_case(
        name="1a. Greeting Intent",
        description="User says hello — no price involved, must return GREET_HELLO",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 0.0, "user_intent": "GREET",
            "user_sentiment": "positive", "session_id": "t_1a", "history": []
        },
        expected_action="REJECT", expected_key="GREET_HELLO"
    )

    test_case(
        name="1b. Bye Intent",
        description="User says goodbye — session should end gracefully",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 0.0, "user_intent": "BYE",
            "user_sentiment": "neutral", "session_id": "t_1b", "history": []
        },
        expected_action="REJECT", expected_key="BYE_GOODBYE"
    )

    test_case(
        name="1c. Deal Confirmation — last bot price used",
        description="User confirms deal. counter_price should be last bot's offer (45000)",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 45000.0, "user_intent": "DEAL",
            "user_sentiment": "positive", "session_id": "t_1c",
            "history": [
                {"role": "user", "offer": 40000.0},
                {"role": "bot", "counter_price": 45000.0}
            ]
        },
        expected_action="ACCEPT", expected_key="DEAL_ACCEPTED"
    )

    test_case(
        name="1d. Deal Confirmation — no history (fallback to user_offer)",
        description="User says DEAL but there's no history. Bot uses user_offer as price.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 43000.0, "user_intent": "DEAL",
            "user_sentiment": "positive", "session_id": "t_1d", "history": []
        },
        expected_action="ACCEPT", expected_key="DEAL_ACCEPTED"
    )

    test_case(
        name="1e. Ask Previous Offer",
        description="User asks what offers were made — metadata should contain both prices",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 40000.0, "user_intent": "ASK_PREVIOUS_OFFER",
            "user_sentiment": "neutral", "session_id": "t_1e",
            "history": [
                {"role": "user", "offer": 38000.0},
                {"role": "bot", "counter_price": 46000.0}
            ]
        },
        expected_action="REJECT", expected_key="PREVIOUS_OFFER"
    )

    # =========================================================================
    # SECTION 2: GUARDS (Over/Under Asking)
    # =========================================================================
    print("\n[2] OFFER GUARDS")

    test_case(
        name="2a. Over-Asking Guard",
        description="User offers MORE than asking price. Bot should redirect to asking price.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 55000.0, "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_2a", "history": []
        },
        expected_action="REJECT", expected_key="OFFER_ABOVE_ASKING"
    )

    test_case(
        name="2b. Exact Asking Price Offer",
        description="User offers EXACTLY the asking price. Should accept (above MAM).",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 50000.0, "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_2b", "history": []
        },
        expected_action="ACCEPT"
    )

    # =========================================================================
    # SECTION 3: ACCEPT RULES
    # =========================================================================
    print("\n[3] ACCEPT RULES")

    test_case(
        name="3a. Standard Accept — exactly at MAM",
        description="User offer == MAM exactly. Must accept immediately.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 40000.0, "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_3a", "history": []
        },
        expected_action="ACCEPT", expected_key="ACCEPT_FINAL"
    )

    test_case(
        name="3b. Standard Accept — above MAM",
        description="User offer is above MAM. Quick accept.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 43000.0, "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_3b", "history": []
        },
        expected_action="ACCEPT", expected_key="ACCEPT_FINAL"
    )

    test_case(
        name="3c. Sentiment Accept — frustrated user, 96% of MAM, 2+ past offers",
        description="Negative user near MAM with history. v2 guard: needs >= 2 past offers.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": round(mam * 0.96),  # 38400
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_3c",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 47000.0},
                {"role": "user", "offer": 37000.0},
                {"role": "bot", "counter_price": 44000.0},
            ]
        },
        expected_action="ACCEPT", expected_key="ACCEPT_SENTIMENT_CLOSE"
    )

    test_case(
        name="3d. Sentiment Accept BLOCKED — frustrated but only 1 past offer (v2 guard)",
        description="v2 fix: negative sentiment on 2nd offer only. Should NOT accept — counter instead.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": round(mam * 0.96),  # 38400
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_3d",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 47000.0},
            ]
        },
        expected_action="COUNTER"   # Should NOT accept — only 1 past offer
    )

    test_case(
        name="3e. Sentiment Accept BLOCKED — first offer ever (exploit prevention)",
        description="v1 bug: user could trigger sentiment accept on very first offer. v2 blocks this.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": round(mam * 0.96),
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_3e",
            "history": []
        },
        expected_action="COUNTER"   # Must be blocked
    )

    # =========================================================================
    # SECTION 4: LOWBALL REJECT
    # =========================================================================
    print("\n[4] LOWBALL REJECT")

    test_case(
        name="4a. Lowball — exactly 70% of MAM (boundary)",
        description="Offer is exactly at lowball boundary. Should counter (not reject).",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": mam * 0.70,  # 28000 — right at boundary
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_4a", "history": []
        },
        expected_action="COUNTER"
    )

    test_case(
        name="4b. Lowball — below 70% of MAM",
        description="Offer too low. No counter, straight reject.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": mam * 0.60,  # 24000
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_4b", "history": []
        },
        expected_action="REJECT", expected_key="REJECT_LOWBALL"
    )

    test_case(
        name="4c. Lowball — negative sentiment doesn't save a terrible offer",
        description="Even if user is frustrated, a lowball stays rejected.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 20000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_4c", "history": []
        },
        expected_action="REJECT", expected_key="REJECT_LOWBALL"
    )

    # =========================================================================
    # SECTION 5: DIMINISHING CONCESSION LADDER
    # =========================================================================
    print("\n[5] DIMINISHING CONCESSION LADDER")

    test_case(
        name="5a. Offer #1 — 35% concession factor",
        description="First ever offer. Factor should be 0.35 (most generous).",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 35000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_5a",
            "history": []
        },
        expected_action="COUNTER", expected_key="STANDARD_COUNTER"
    )

    test_case(
        name="5b. Offer #3 — 20% concession factor",
        description="3rd offer. Factor drops to 0.20 — bot slowing down.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_5b",
            "history": [
                {"role": "user", "offer": 33000.0},
                {"role": "bot", "counter_price": 48000.0},
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46500.0},
            ]
        },
        expected_action="COUNTER", expected_key="STANDARD_COUNTER"
    )

    test_case(
        name="5c. Offer #5 — 10% concession factor",
        description="5th offer. Factor is 0.10 — bot barely moving.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 37000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_5c",
            "history": [
                {"role": "user", "offer": 32000.0},
                {"role": "bot", "counter_price": 49000.0},
                {"role": "user", "offer": 33000.0},
                {"role": "bot", "counter_price": 47000.0},
                {"role": "user", "offer": 34000.0},
                {"role": "bot", "counter_price": 45500.0},
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 44000.0},
            ]
        },
        expected_action="COUNTER"
    )

    # =========================================================================
    # SECTION 6: PATTERN DETECTION
    # =========================================================================
    print("\n[6] PATTERN DETECTION")

    test_case(
        name="6a. Stalling Pattern — user barely moved",
        description="User moved < 1% of asking price. Bot should hold firm.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 35300.0,   # moved only 300 from 35000 (0.6% of 50000)
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_6a",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_HOLD_FIRM"
    )

    test_case(
        name="6b. Rapid Close Pattern — user jumped a large amount",
        description="User jumped >15% of the remaining gap. Bot should encourage to close.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 39000.0,   # big jump from 34000
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_6b",
            "history": [
                {"role": "user", "offer": 34000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_ENCOURAGE_CLOSE"
    )

    test_case(
        name="6c. Normal Pattern — steady progress",
        description="User moving at normal pace. Standard counter.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36500.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_6c",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER", expected_key="STANDARD_COUNTER"
    )

    test_case(
        name="6d. First offer — no history to detect pattern",
        description="No history means no pattern. Should fall back to 'normal'.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_6d",
            "history": []
        },
        expected_action="COUNTER", expected_key="STANDARD_COUNTER"
    )

    # =========================================================================
    # SECTION 7: SENTIMENT MODIFIERS ON COUNTER
    # =========================================================================
    print("\n[7] SENTIMENT MODIFIERS ON COUNTER")

    test_case(
        name="7a. Positive Sentiment — bot should give less (×0.80 factor)",
        description="Excited user doesn't need extra discount. Check metadata for concession_factor.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_7a",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER"
        # counter_price should be HIGHER than neutral equivalent (less discount)
    )

    test_case(
        name="7b. Neutral Sentiment — baseline concession",
        description="Neutral user, standard factor. Compare with 7a to verify modifier works.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_7b",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER"
    )

    test_case(
        name="7c. Negative Sentiment — no modifier on counter (just normal)",
        description="Negative user in counter zone. No bonus — standard factor applies.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_7c",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER"
    )

    # =========================================================================
    # SECTION 8: FINAL ROUND LOGIC
    # =========================================================================
    print("\n[8] FINAL ROUND (Offer >= 5)")

    test_case(
        name="8a. Final Round — offer #5",
        description="5th offer triggers final round. Factor = 0.50 (split gap).",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 38000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_8a",
            "history": [
                {"role": "user", "offer": 32000.0},
                {"role": "bot", "counter_price": 49000.0},
                {"role": "user", "offer": 34000.0},
                {"role": "bot", "counter_price": 46000.0},
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 44000.0},
                {"role": "user", "offer": 36000.0},
                {"role": "bot", "counter_price": 42000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_FINAL_OFFER"
    )

    test_case(
        name="8b. Final Round — pattern modifiers should be IGNORED",
        description="Even with stalling pattern, final round bypasses pattern logic.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36100.0,   # stalling (barely moved from 36000)
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_8b",
            "history": [
                {"role": "user", "offer": 32000.0},
                {"role": "bot", "counter_price": 49000.0},
                {"role": "user", "offer": 34000.0},
                {"role": "bot", "counter_price": 46000.0},
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 44000.0},
                {"role": "user", "offer": 36000.0},
                {"role": "bot", "counter_price": 42000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_FINAL_OFFER"
    )

    # =========================================================================
    # SECTION 9: SAFETY CLAMPS
    # =========================================================================
    print("\n[9] SAFETY CLAMPS")

    test_case(
        name="9a. Bot must never go below MAM",
        description="Even after many rounds, counter_price must stay >= MAM (40000).",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 39500.0,   # just below MAM, in counter zone
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_9a",
            "history": [
                {"role": "user", "offer": 38000.0},
                {"role": "bot", "counter_price": 40500.0},   # bot is already near MAM
            ]
        },
        expected_action="COUNTER"
        # counter_price must be >= 40000
    )

    test_case(
        name="9b. Bot must never exceed its previous offer",
        description="counter_price should always be <= last bot offer. No price going up.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_9b",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 44000.0},
            ]
        },
        expected_action="COUNTER"
        # counter_price must be <= 44000
    )

    # =========================================================================
    # SECTION 10: EDGE CASES & WEIRD INPUTS
    # =========================================================================
    print("\n[10] EDGE CASES & WEIRD INPUTS")

    test_case(
        name="10a. user_offer == 0.0 with MAKE_OFFER intent",
        description="Zero offer — should be a lowball reject.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 0.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10a", "history": []
        },
        expected_action="REJECT", expected_key="REJECT_LOWBALL"
    )

    test_case(
        name="10b. user_offer == 1 rupee",
        description="Basically zero. Lowball reject.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 1.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_10b", "history": []
        },
        expected_action="REJECT", expected_key="REJECT_LOWBALL"
    )

    test_case(
        name="10c. user_offer exactly 1 rupee below MAM",
        description="Just barely missing MAM. Should counter, not accept.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": mam - 1,  # 39999
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10c", "history": []
        },
        expected_action="COUNTER"
    )

    test_case(
        name="10d. Huge history — 20 turns",
        description="Very long negotiation. Bot should still calculate correctly.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 38500.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10d",
            "history": [
                {"role": "user", "offer": 28000.0}, {"role": "bot", "counter_price": 49000.0},
                {"role": "user", "offer": 30000.0}, {"role": "bot", "counter_price": 47500.0},
                {"role": "user", "offer": 31000.0}, {"role": "bot", "counter_price": 46000.0},
                {"role": "user", "offer": 33000.0}, {"role": "bot", "counter_price": 44500.0},
                {"role": "user", "offer": 34500.0}, {"role": "bot", "counter_price": 43500.0},
                {"role": "user", "offer": 35500.0}, {"role": "bot", "counter_price": 42800.0},
                {"role": "user", "offer": 36000.0}, {"role": "bot", "counter_price": 42200.0},
                {"role": "user", "offer": 37000.0}, {"role": "bot", "counter_price": 41500.0},
                {"role": "user", "offer": 37500.0}, {"role": "bot", "counter_price": 41000.0},
                {"role": "user", "offer": 38000.0}, {"role": "bot", "counter_price": 40700.0},
            ]
        },
        expected_action="COUNTER"
        # Must not go below MAM
    )

    test_case(
        name="10e. UNKNOWN intent — fallback behavior",
        description="NLU couldn't detect intent. Should handle gracefully without crash.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 35000.0,
            "user_intent": "UNKNOWN",
            "user_sentiment": "neutral", "session_id": "t_10e", "history": []
        }
        # No strict expectation — just must not crash (HTTP 200)
    )

    test_case(
        name="10f. INVALID intent — fallback behavior",
        description="Invalid intent from NLU. Should handle gracefully.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 35000.0,
            "user_intent": "INVALID",
            "user_sentiment": "neutral", "session_id": "t_10f", "history": []
        }
    )

    test_case(
        name="10g. mam == asking_price (no room to negotiate)",
        description="Weird config: seller's floor IS the asking price. Any offer below = lowball.",
        input_data={
            "mam": 50000.0, "asking_price": 50000.0,
            "user_offer": 47000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10g", "history": []
        },
        expected_action="REJECT", expected_key="REJECT_LOWBALL"
    )

    test_case(
        name="10h. Floats with many decimal places",
        description="Precision test — should ceil correctly and not crash.",
        input_data={
            "mam": 40000.33, "asking_price": 50000.99,
            "user_offer": 35123.456,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10h", "history": []
        },
        expected_action="COUNTER"
    )

    test_case(
        name="10i. History with missing offer fields",
        description="Some history turns have no 'offer' key. Should not crash.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 36000.0,
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "neutral", "session_id": "t_10i",
            "history": [
                {"role": "user"},                          # no offer key
                {"role": "bot", "counter_price": 46000.0},
                {"role": "user", "offer": None},           # offer is None
                {"role": "bot"},                           # no counter_price
            ]
        },
        expected_action="COUNTER"
    )

    test_case(
        name="10j. Stalling + Positive Sentiment — combined modifiers",
        description="Stalling (×0.40) + positive sentiment (×0.80) stack. Very small concession expected.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 35200.0,   # barely moved from 35000
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "positive", "session_id": "t_10j",
            "history": [
                {"role": "user", "offer": 35000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_HOLD_FIRM"
    )

    test_case(
        name="10k. Rapid Close + Negative Sentiment",
        description="User jumped a lot (rapid_close) but is negative. Should still encourage close.",
        input_data={
            "mam": mam, "asking_price": asking_price,
            "user_offer": 39000.0,   # big jump
            "user_intent": "MAKE_OFFER",
            "user_sentiment": "negative", "session_id": "t_10k",
            "history": [
                {"role": "user", "offer": 33000.0},
                {"role": "bot", "counter_price": 46000.0},
            ]
        },
        expected_action="COUNTER", expected_key="COUNTER_ENCOURAGE_CLOSE"
    )

    # =========================================================================
    # SECTION 11: SECURITY
    # =========================================================================
    print("\n[11] SECURITY")

    print("  → Running: 11a. Missing Auth Header")
    r = client.post("/decide", json={
        "mam": mam, "asking_price": asking_price,
        "user_offer": 45000.0, "user_intent": "MAKE_OFFER",
        "user_sentiment": "neutral", "session_id": "sec1", "history": []
    })
    results.append({
        "Test Case":   "11a. Security — Missing Header",
        "Description": "No X-Internal-Key header. Must return 403.",
        "Status":      f"HTTP {r.status_code}",
        "Verdict":     "✅ PASS" if r.status_code == 403 else "❌ FAIL",
        "Expected Action": "HTTP 403",
        "Output": r.text,
    })

    print("  → Running: 11b. Wrong Auth Key")
    r2 = client.post("/decide", json={
        "mam": mam, "asking_price": asking_price,
        "user_offer": 45000.0, "user_intent": "MAKE_OFFER",
        "user_sentiment": "neutral", "session_id": "sec2", "history": []
    }, headers={"X-Internal-Key": "wrong-key-999"})
    results.append({
        "Test Case":   "11b. Security — Wrong Key",
        "Description": "Wrong X-Internal-Key. Must return 403.",
        "Status":      f"HTTP {r2.status_code}",
        "Verdict":     "✅ PASS" if r2.status_code == 403 else "❌ FAIL",
        "Expected Action": "HTTP 403",
        "Output": r2.text,
    })

    # =========================================================================
    # WRITE RESULTS TO MARKDOWN
    # =========================================================================
    total  = len(results)
    passed = sum(1 for r in results if "✅" in r.get("Verdict", ""))
    failed = total - passed

    output_file = "strategy_test_results_v2.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 🧠 Strategy Engine v2.0 — Full Test Results\n\n")
        f.write(f"> **{passed}/{total} passed** | {failed} failed\n\n")
        f.write("---\n\n")

        sections = {
            "1": "NON-OFFER INTENTS",
            "2": "OFFER GUARDS",
            "3": "ACCEPT RULES",
            "4": "LOWBALL REJECT",
            "5": "DIMINISHING CONCESSION LADDER",
            "6": "PATTERN DETECTION",
            "7": "SENTIMENT MODIFIERS",
            "8": "FINAL ROUND",
            "9": "SAFETY CLAMPS",
            "10": "EDGE CASES",
            "11": "SECURITY",
        }

        current_section = None
        for res in results:
            section_num = res["Test Case"].split(".")[0].strip()
            if section_num != current_section:
                current_section = section_num
                label = sections.get(section_num, "")
                f.write(f"\n## Section {section_num}: {label}\n\n")

            verdict = res.get("Verdict", "")
            f.write(f"### {res['Test Case']}  {verdict}\n")
            f.write(f"*{res.get('Description', '')}*\n\n")
            f.write(f"**Status:** `{res['Status']}`\n\n")

            if "Action" in res:
                f.write(f"| Field | Value |\n|---|---|\n")
                f.write(f"| Action | `{res['Action']}` |\n")
                f.write(f"| Response Key | `{res['ResponseKey']}` |\n")
                f.write(f"| Counter Price | `{res.get('CounterPrice')}` |\n")
                f.write(f"| Expected Action | `{res.get('Expected Action', 'Any')}` |\n")
                f.write(f"| Expected Key | `{res.get('Expected Key', 'Any')}` |\n\n")

                meta = res.get("Metadata", {})
                if meta:
                    f.write("**Decision Metadata:**\n```json\n")
                    f.write(json.dumps(meta, indent=2))
                    f.write("\n```\n\n")

            f.write("\n<details><summary>Full Input/Output</summary>\n\n")
            f.write("**Input:**\n```json\n")
            f.write(json.dumps(res.get("Input", {}), indent=2))
            f.write("\n```\n\n**Output:**\n```json\n")
            f.write(json.dumps(res.get("Output", {}), indent=2))
            f.write("\n```\n\n</details>\n\n---\n\n")

        # Summary table
        f.write("\n## 📊 Summary Table\n\n")
        f.write("| # | Test Case | Verdict | Action | Counter Price |\n")
        f.write("|---|---|---|---|---|\n")
        for res in results:
            f.write(f"| {res['Test Case'].split('.')[0]} "
                    f"| {res['Test Case']} "
                    f"| {res.get('Verdict','—')} "
                    f"| `{res.get('Action','—')}` "
                    f"| `{res.get('CounterPrice','—')}` |\n")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed | {failed} failed")
    print(f"  Saved to: {output_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_tests()