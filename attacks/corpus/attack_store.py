import os
import json
from collections import defaultdict
from typing import List, Dict, Any
from contracts.schemas import AttackSpec

class AttackStore:
    def __init__(self, corpus_dir: str = 'data/attack_cases'):
        self.corpus_dir = corpus_dir
        os.makedirs(self.corpus_dir, exist_ok=True)

    def add(self, spec: AttackSpec) -> None:
        path = os.path.join(self.corpus_dir, f"{spec.attack_id}.json")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(spec.to_json())

    def load(self, attack_id: str) -> AttackSpec:
        path = os.path.join(self.corpus_dir, f"{attack_id}.json")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return AttackSpec.from_dict(data)

    def load_family(self, family: str) -> List[AttackSpec]:
        return [self.load(aid) for aid in self.list_all() if self.load(aid).family == family]

    def list_all(self) -> List[str]:
        if not os.path.exists(self.corpus_dir):
            return []
        attack_ids = []
        for fname in os.listdir(self.corpus_dir):
            if fname.endswith('.json') and fname != 'MANIFEST.json':
                attack_ids.append(fname[:-5])
        return sorted(attack_ids)

    def get_manifest(self) -> Dict[str, Any]:
        total = 0
        by_family = defaultdict(int)
        by_surface = defaultdict(int)
        for aid in self.list_all():
            spec = self.load(aid)
            total += 1
            by_family[spec.family] += 1
            by_surface[spec.target_surface] += 1
            
        return {
            'total_count': total,
            'by_family': dict(by_family),
            'by_surface': dict(by_surface),
            'version': '1.0'
        }
