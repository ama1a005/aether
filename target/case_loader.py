import json
import os
import random
from typing import List, Tuple
from contracts.schemas import PatientCase, AttackSpec

class CaseLoader:
    def __init__(self, source: str, fixture_dir: str = 'tests/fixtures',
                 ptbxl_root: str | None = None, ptbxl_folds: tuple[int, ...] = (1,)):
        """Select an explicit supported case source."""
        if source not in {'synthetic', 'fixture', 'ptbxl'}:
            raise ValueError(f"Unsupported case source: {source}")
        self.source = source
        self.fixture_dir = fixture_dir
        self.ptbxl_root = ptbxl_root
        self.ptbxl_folds = ptbxl_folds

    def load_cases(self, n: int, seed: int) -> List[PatientCase]:
        """Load cases deterministically without altering process random state."""
        if type(n) is not int or n < 0:
            raise ValueError("Case count must be a nonnegative integer")
        rng = random.Random(seed)
        cases = []
        
        if self.source == 'synthetic':
            superclasses = ['NORM', 'MI', 'HYP', 'CD', 'STTC']
            for i in range(n):
                hr = rng.randint(50, 150)
                ecg_class = rng.choice(superclasses)
                features = {
                    'heart_rate': hr,
                    'ecg_superclass': ecg_class
                }
                
                if ecg_class in ['MI', 'STTC']:
                    decision = 'ESCALATE'
                    features['st_deviation_mv'] = rng.uniform(0.2, 0.5)
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
                raise FileNotFoundError(f"Required patient fixture is missing: {fixture_path}")
        elif self.source == 'ptbxl':
            if self.ptbxl_root is None:
                raise ValueError('ptbxl_root is required; no dataset path is inferred')
            from pathlib import Path
            from benchmarks.ptbxl import load_ptbxl_cases
            cases = load_ptbxl_cases(Path(self.ptbxl_root), folds=self.ptbxl_folds,
                                     n=n, seed=seed)
            
        return cases

    def load_clean_attacked_pair(self, case: PatientCase, attack_spec: AttackSpec) -> Tuple[PatientCase, PatientCase]:
        return case, case
