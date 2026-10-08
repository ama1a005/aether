from typing import List, Dict, Any

class CandidateGraphBuilder:
    def build(self, component_ids: List[str], regions: Dict[str, str]) -> Dict[str, Any]:
        nodes = []
        edges = []
        
        for cid in component_ids:
            region = regions.get(cid, 'sender')
            ntype = 'mlp' if 'MLP' in cid else 'head' if 'H' in cid else 'layer'
            nodes.append({'id': cid, 'type': ntype, 'region': region})
            
        region_nodes = {'sender': [], 'message': [], 'receiver': []}
        for n in nodes:
            if n['region'] in region_nodes:
                region_nodes[n['region']].append(n['id'])
                
        # fully connected within region
        for reg, n_list in region_nodes.items():
            for i in range(len(n_list)):
                for j in range(i+1, len(n_list)):
                    edges.append({'src': n_list[i], 'dst': n_list[j], 'type': 'internal', 'bridge': False})
                    
        # placeholder bridge edges
        if region_nodes['sender'] and region_nodes['message']:
            edges.append({'src': region_nodes['sender'][0], 'dst': region_nodes['message'][0], 'type': 'bridge', 'bridge': True})
        if region_nodes['message'] and region_nodes['receiver']:
            edges.append({'src': region_nodes['message'][0], 'dst': region_nodes['receiver'][0], 'type': 'bridge', 'bridge': True})
            
        return {'nodes': nodes, 'edges': edges}
