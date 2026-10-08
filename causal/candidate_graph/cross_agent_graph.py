import json
from typing import List, Dict

class CrossAgentGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node_dict: dict):
        self.nodes[node_dict["id"]] = node_dict

    def add_edge(self, edge_dict: dict):
        self.edges.append(edge_dict)

    def get_nodes_by_region(self, region: str) -> List[dict]:
        return [n for n in self.nodes.values() if n.get("region") == region]

    def get_bridge_edges(self) -> List[dict]:
        return [e for e in self.edges if e.get("bridge") == True]

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'CrossAgentGraph':
        g = cls()
        g.nodes = d.get("nodes", {})
        g.edges = d.get("edges", [])
        return g

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'CrossAgentGraph':
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load_from_activation_traces(cls, sender_trace_meta: dict, receiver_trace_meta: dict, message_record: dict) -> 'CrossAgentGraph':
        g = cls()
        for comp_id in sender_trace_meta.get("component_ids", []):
            g.add_node({"id": comp_id, "type": "layer", "region": "sender", "retained": True, "metadata": {}})
        for msg_id in message_record.get("fields", []):
            g.add_node({"id": msg_id, "type": "message_field", "region": "message", "retained": True, "metadata": {}})
        for comp_id in receiver_trace_meta.get("component_ids", []):
            g.add_node({"id": comp_id, "type": "layer", "region": "receiver", "retained": True, "metadata": {}})
        return g

    def get_circuit_subgraph(self, retained_node_ids: List[str]) -> 'CrossAgentGraph':
        sub = CrossAgentGraph()
        for n_id in retained_node_ids:
            if n_id in self.nodes:
                sub.add_node(self.nodes[n_id])
        retained_set = set(retained_node_ids)
        for e in self.edges:
            if e["src"] in retained_set and e["dst"] in retained_set:
                sub.add_edge(e)
        return sub

    def node_count_by_region(self) -> Dict[str, int]:
        counts = {}
        for n in self.nodes.values():
            r = n.get("region")
            counts[r] = counts.get(r, 0) + 1
        return counts

    def summary(self) -> str:
        return f"CrossAgentGraph: {len(self.nodes)} nodes, {len(self.edges)} edges. Region counts: {self.node_count_by_region()}"
