# cli_demo.py
import sys
import os
import uuid
import random
import importlib.util
import asyncio

# ---------------------------  
# Base directory (orchestrator/)
# ---------------------------
base_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, base_dir)

# ---------------------------
# Import modules using importlib
# ---------------------------

# 1️⃣ NLU
spec_nlu = importlib.util.spec_from_file_location(
    "nlu.main", os.path.join(base_dir, "microservices", "nlu-service", "app", "main.py")
)
nlu_main = importlib.util.module_from_spec(spec_nlu)
spec_nlu.loader.exec_module(nlu_main)
nlu_parse = nlu_main.parse
NLUInput = nlu_main.NLUInput

# 2️⃣ Strategy Core
spec_strategy_core = importlib.util.spec_from_file_location(
    "strategy_core", os.path.join(base_dir, "microservices", "strategy-engine", "app", "strategy_core.py")
)
strategy_core = importlib.util.module_from_spec(spec_strategy_core)
spec_strategy_core.loader.exec_module(strategy_core)
make_decision = strategy_core.make_decision

# 3️⃣ Strategy Schemas
spec_schemas = importlib.util.spec_from_file_location(
    "schemas", os.path.join(base_dir, "microservices", "strategy-engine", "app", "schema.py")
)
schemas = importlib.util.module_from_spec(spec_schemas)
spec_schemas.loader.exec_module(schemas)
StrategyInput = schemas.StrategyInput
StrategyOutput = schemas.StrategyOutput

# 4️⃣ LLM Phraser
spec_prompt = importlib.util.spec_from_file_location(
    "prompt_templates", os.path.join(base_dir, "microservices", "llm-phraser", "app", "llm_prompt.py")
)
prompt_templates = importlib.util.module_from_spec(spec_prompt)
spec_prompt.loader.exec_module(prompt_templates)
get_formatted_prompt = prompt_templates.get_formatted_prompt

# ---------------------------
# Session Setup
# ---------------------------
session_id = "Ashna"
history = []

print("🤖 Negotiation Bot CLI Demo (Full Flow Test)")
print("Type 'exit' or 'quit' to stop\n")
print(f"🔑 Session ID: {session_id}\n")
print("💡 Try typing greetings ('hi'), offers (100, 150), 'deal', questions about previous offer, and bye\n")

# ---------------------------
# Async main loop
# ---------------------------
async def main():
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in ["exit", "quit"]:
            break

        # 1️⃣ Run NLU
        nlu_input = NLUInput(text=user_text, session_id=session_id)
        nlu_result = await nlu_parse(nlu_input)
        user_intent = nlu_result["intent"]
        user_sentiment = nlu_result["sentiment"]
        user_offer = nlu_result["entities"].get("PRICE")

        # 2️⃣ Prepare Strategy Input
        asking_price = 200  # Example initial price
        mam = 150           # Example MAM (floor)

        strategy_input = StrategyInput(
            mam=mam,
            asking_price=asking_price,
            user_offer=user_offer or 0,
            user_intent=user_intent,
            user_sentiment=user_sentiment,
            session_id=session_id,
            history=history.copy()
        )

        # 3️⃣ Make Strategy Decision
        decision: StrategyOutput = make_decision(strategy_input)

        # 4️⃣ Format Response via LLM Phraser
        system_prompt, bot_response = get_formatted_prompt(decision)

        # 5️⃣ Print Bot Response
        print(f"Bot: {bot_response}\n")

        # 6️⃣ Update History
        if user_offer:
            history.append({"role": "user", "offer": user_offer})
        else:
            history.append({"role": "user", "text": user_text})

        if decision.counter_price:
            history.append({"role": "bot", "counter_price": decision.counter_price})
        else:
            history.append({"role": "bot", "text": bot_response})

if __name__ == "__main__":
    asyncio.run(main())
