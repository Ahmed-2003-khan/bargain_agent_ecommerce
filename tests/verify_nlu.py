import asyncio
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocking logic to test the regex function directly (unit test style)
def verify_nlu_logic():
    print("Testing NLU Logic...")

    greetings = ["hi", "hello", "hey"]
    text_cases = [
        ("I want this in 120", "MAKE_OFFER"), # The failing case
        ("Hi there", "GREET"),
        ("Hello", "GREET"),
        ("I want this", "ASK_QUESTION"), # Assuming 'this' alone doesn't trigger greet
        ("This is 120", "MAKE_OFFER"),
    ]

    # Re-implementing the logic from main.py for testing without running the full FastAPI app imports
    def contains_word(text, words):
        pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
        return re.search(pattern, text, re.IGNORECASE) is not None

    def get_intent(text):
        text = text.lower()
        price_match = re.search(r"(\d+)", text)
        price = float(price_match.group(1)) if price_match else None

        if contains_word(text, greetings):
            return "GREET"
        elif price:
            return "MAKE_OFFER"
        else:
            return "OTHER"

    for text, expected in text_cases:
        result = get_intent(text)
        status = "✅" if result == expected else f"❌ (Got {result})"
        print(f"Input: '{text}' -> Expected: {expected} | Status: {status}")

if __name__ == "__main__":
    verify_nlu_logic()
