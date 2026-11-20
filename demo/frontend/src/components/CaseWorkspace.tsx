import type {DemoCase} from '../types';
import {Badge} from './Badge';
import {JsonPanel} from './JsonPanel';

export function CaseWorkspace({item,cases,onSelect}:{item:DemoCase;cases:DemoCase[];onSelect:(id:string)=>void}) {
  return <section>
    <div className="section-head">
      <div><p className="eyebrow">CASE WORKSPACE · {cases.length} CASES LOADED</p><h2>{item.case_id} · {item.display_name}</h2></div>
      <Badge tone="amber">OFFICIAL-SOURCE PTB-XL RECORD</Badge>
    </div>
    <label htmlFor="patient-selector"><b>Select PTB-XL-derived case</b></label>
    <div className="selector">
      <button onClick={()=>onSelect(cases[Math.max(0,cases.indexOf(item)-1)].case_id)}>Previous</button>
      <select id="patient-selector" aria-label="Patient selector" value={item.case_id} onChange={event=>onSelect(event.target.value)}>
        {cases.map(candidate=><option key={candidate.case_id} value={candidate.case_id}>{candidate.case_id} — {candidate.presenting_complaint}</option>)}
      </select>
      <button onClick={()=>onSelect(cases[Math.min(cases.length-1,cases.indexOf(item)+1)].case_id)}>Next</button>
    </div>
    <div className="grid">
      <article><h3>Source record</h3><strong>{item.presenting_complaint}</strong><p>{item.symptom_duration}</p><p>{item.age} years · {item.sex}</p></article>
      <article><h3>AETHER-derived demo action</h3><div className={`decision ${item.expected_action==='ESCALATE'?'danger':'safe'}`}>{item.expected_action}</div><p>{item.notes}</p></article>
      <article><h3>Source limits</h3><p>{item.history.join(', ')||'History not supplied by PTB-XL metadata'}</p><h4>Medications</h4><p>{item.medications.join(', ')||'Not supplied by PTB-XL metadata'}</p></article>
      <article><h3>Derivation</h3>{item.timeline.map(line=><p key={line}>• {line}</p>)}</article>
    </div>
    <JsonPanel title="PTB-XL metadata and exact provenance" value={{ecg:item.ecg,provenance:item.provenance,unavailable_in_source:{vitals:item.vitals,labs:item.labs,additional_assessments:item.additional_assessments}}}/>
  </section>
}
