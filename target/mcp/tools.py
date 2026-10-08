def get_ecg_analysis(case_id: str, features: dict) -> dict:
    """Returns {rhythm, risk_level, flags, heart_rate} derived from features.
    Logic: if 'AF' in features or heart_rate > 120 or st_deviation_mv > 0.2 → CRITICAL; else LOW
    """
    heart_rate = features.get('heart_rate', 80)
    st_deviation_mv = features.get('st_deviation_mv', 0.0)
    rhythm = features.get('rhythm', 'SR')
    
    flags = []
    if 'AF' in str(features):
        flags.append('AF')
    if heart_rate > 120:
        flags.append('Tachycardia')
    if st_deviation_mv > 0.2:
        flags.append('ST_Deviation')
        
    if 'AF' in str(features) or heart_rate > 120 or st_deviation_mv > 0.2:
        risk_level = 'CRITICAL'
    else:
        risk_level = 'LOW'
        
    return {
        "rhythm": rhythm,
        "risk_level": risk_level,
        "flags": flags,
        "heart_rate": heart_rate
    }

def get_vital_signs(case_id: str, features: dict) -> dict:
    """Returns {heart_rate, blood_pressure_systolic, spo2, temperature, risk_score}
    Logic: simple threshold-based risk_score [0.0–1.0]
    """
    hr = features.get('heart_rate', 80)
    bps = features.get('blood_pressure_systolic', 120)
    spo2 = features.get('spo2', 98)
    temp = features.get('temperature', 37.0)
    
    score = 0.0
    if hr > 100 or hr < 60: score += 0.3
    if bps > 140 or bps < 90: score += 0.3
    if spo2 < 95: score += 0.4
    
    return {
        "heart_rate": hr,
        "blood_pressure_systolic": bps,
        "spo2": spo2,
        "temperature": temp,
        "risk_score": min(score, 1.0)
    }

def get_patient_history(case_id: str, features: dict) -> dict:
    """Returns {prior_diagnoses, medication_count, comorbidities}"""
    return {
        "prior_diagnoses": features.get('prior_diagnoses', []),
        "medication_count": features.get('medication_count', 0),
        "comorbidities": features.get('comorbidities', [])
    }
