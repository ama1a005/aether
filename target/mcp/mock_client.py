from typing import Dict, Callable, Any, Optional
from datetime import datetime, timezone
from contracts.schemas import AttackSpec

class MockMCPClient:
    def __init__(self, tools: Optional[Dict[str, Callable]] = None):
        self.tools = tools or {}
        self.call_logs = []

    def register_tool(self, name: str, fn: Callable):
        self.tools[name] = fn

    def call_tool(self, tool_name: str, inputs: dict, poisoned: bool = False, poison_spec: Optional[AttackSpec] = None) -> dict:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered")

        # Get clean result
        fn = self.tools[tool_name]
        result = fn(**inputs)

        # Apply poisoning if requested
        if poisoned and poison_spec is not None:
            if poison_spec.target_surface == 'mcp_tool_description':
                # Inject override instruction into result — embeds target_behavior
                # so Agent B's poison detector can identify it
                if isinstance(result, dict):
                    override_text = poison_spec.adversarial_payload.get('description', '')
                    # Append target_behavior so the override is machine-detectable
                    result['_poison_context'] = (
                        f"{override_text} [OVERRIDE:{poison_spec.target_behavior}]"
                    )
            elif poison_spec.target_surface == 'mcp_tool_output':
                # Replace result with adversarial payload
                result = poison_spec.adversarial_payload.get('result', poison_spec.adversarial_payload)
        
        # Log the call
        self.call_logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "inputs": inputs,
            "poisoned": poisoned
        })

        return result
