import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
import httpx

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.lib import brain_client
from orchestrator.graph import nodes
from orchestrator.graph.state import AgentState

async def test_brain_client_fallback():
    print("Testing brain_client fallback...")
    
    # Mock httpx to raise an error
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Simulated Network Error")
        
        result = await brain_client.call_brain(150, 200, 100, "MAKE_OFFER", "positive", "test_sess", [])
        
        print(f"Result: {result}")
        
        # Verify fix
        if result["action"] == "COUNTER" and result["response_key"] == "ENGINE_UNAVAILABLE":
            print("✅ brain_client fallback logic passed!")
        else:
            print(f"❌ brain_client fallback logic failed! Got: {result}")

async def test_brain_node_fallback():
    print("\nTesting brain_node fallback...")
    
    # Mock call_brain to raise an exception (simulating what happens inside brain_node block)
    # Actually brain_node catches exceptions from call_brain too.
    
    state = AgentState(
        session_id="test",
        mam=150.0,
        user_input="hi",
        history=[],
        asking_price=200.0,
        intent="unknown",
        sentiment="neutral"
    )

    with patch('orchestrator.graph.nodes.call_brain', side_effect=Exception("Total Failure")):
        
        new_state = await nodes.brain_node(state)
        
        brain_out = new_state.get("_brain_raw", {})
        print(f"Brain Raw Output: {brain_out}")
        
        # Verify MS5 required fields
        if (brain_out.get("policy_type") == "rule-based" and 
            brain_out.get("policy_version") == "fallback" and
            brain_out.get("decision_metadata", {}).get("reason") == "brain_failed"):
            print("✅ brain_node fallback schema passed!")
        else:
            print("❌ brain_node fallback schema failed!")

if __name__ == "__main__":
    asyncio.run(test_brain_client_fallback())
    asyncio.run(test_brain_node_fallback())
