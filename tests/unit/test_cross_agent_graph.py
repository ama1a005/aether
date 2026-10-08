import unittest
import json
from causal.candidate_graph.cross_agent_graph import CrossAgentGraph

class TestCrossAgentGraph(unittest.TestCase):
    def test_graph_serialization_roundtrip(self):
        g = CrossAgentGraph()
        g.add_node({"id": "n1", "type": "layer", "region": "sender", "retained": True, "metadata": {}})
        g.add_edge({"src": "n1", "dst": "n2", "type": "internal", "bridge": False, "weight": 1.0})
        
        g_json = g.to_json()
        g2 = CrossAgentGraph.from_json(g_json)
        self.assertEqual(g.nodes, g2.nodes)
        self.assertEqual(g.edges, g2.edges)
        
    def test_all_node_types(self):
        types = ['attention_head', 'mlp_block', 'layer', 'message_field', 'message_text', 'message_span', 'decision']
        g = CrossAgentGraph()
        for i, t in enumerate(types):
            g.add_node({"id": f"n{i}", "type": t, "region": "sender", "retained": True, "metadata": {}})
        self.assertEqual(len(g.nodes), len(types))
        
    def test_get_nodes_by_region(self):
        g = CrossAgentGraph()
        g.add_node({"id": "n1", "region": "sender"})
        g.add_node({"id": "n2", "region": "message"})
        self.assertEqual(len(g.get_nodes_by_region("sender")), 1)
        self.assertEqual(len(g.get_nodes_by_region("message")), 1)
        
    def test_bridge_edges(self):
        g = CrossAgentGraph()
        g.add_edge({"src": "1", "dst": "2", "bridge": True})
        g.add_edge({"src": "2", "dst": "3", "bridge": False})
        self.assertEqual(len(g.get_bridge_edges()), 1)
        
    def test_load_from_activation_traces(self):
        sender = {"component_ids": ["s1", "s2"]}
        receiver = {"component_ids": ["r1"]}
        msg = {"fields": ["m1"]}
        g = CrossAgentGraph.load_from_activation_traces(sender, receiver, msg)
        self.assertEqual(len(g.nodes), 4)
        
    def test_circuit_subgraph(self):
        g = CrossAgentGraph()
        g.add_node({"id": "1", "region": "sender"})
        g.add_node({"id": "2", "region": "receiver"})
        g.add_node({"id": "3", "region": "message"})
        g.add_edge({"src": "1", "dst": "2"})
        
        sub = g.get_circuit_subgraph(["1", "2"])
        self.assertEqual(len(sub.nodes), 2)
        self.assertEqual(len(sub.edges), 1)

if __name__ == '__main__':
    unittest.main()
