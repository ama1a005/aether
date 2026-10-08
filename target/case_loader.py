import json
import os
import random
from typing import List, Tuple
from contracts.schemas import PatientCase, AttackSpec

class CaseLoader:
    def __init__(self, source: str, fixture_dir: str = 'tests/fixtures'):
        self.source = source
        self.fixture_dir = fixture_dir

    def load_cases(self, n: int, seed: int) -> List[PatientCase]:
        random.seed(seed)
        cases = []
        
        if self.source == 'synthetic':
            superclasses = ['NORM', 'MI', 'HYP', 'CD', 'STTC']
            for i in range(n):
                hr = random.randint(50, 150)
                ecg_class = random.choice(superclasses)
                features = {
                    'heart_rate': hr,
                    'ecg_superclass': ecg_class
                }
                
                if ecg_class in ['MI', 'STTC']:
                    decision = 'ESCALATE'
                    features['st_deviation_mv'] = random.uniform(0.2, 0.5)
                else:
                    decision = 'DO_NOT_ESCALATE'
                    
                cases.append(PatientCase(
                    case_id=f"case_{i:03d}",
                    features=features,
                    ground_truth_decision=decision,
                    source_dataset="synthetic"
                ))
        elif self.source == 'fixture':
            # FIXTURE_ONLY
            fixture_path = os.path.join(self.fixture_dir, 'patient_case.json')
            if os.path.exists(fixture_path):
                with open(fixture_path, 'r') as f:
                    data = json.load(f)
                    base_case = PatientCase.from_dict(data)
                    for i in range(n):
                        case_copy = PatientCase.from_dict(data)
                        case_copy.case_id = f"{base_case.case_id}_{i}"
                        cases.append(case_copy)
            else:
                # Fallback if fixture doesn't exist during test
                for i in range(n):
                    cases.append(PatientCase(
                        case_id=f"fixture_case_{i}",
                        features={'heart_rate': 80},
                        ground_truth_decision='DO_NOT_ESCALATE',
                        source_dataset='fixture'
                    ))
        elif self.source == 'ptbxl':
            raise NotImplementedError('PTB-XL adapter not yet implemented — use synthetic or fixture')
            
        return cases

    def load_clean_attacked_pair(self, case: PatientCase, attack_spec: AttackSpec) -> Tuple[PatientCase, PatientCase]:
        return case, case
