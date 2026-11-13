import {useEffect,useState} from 'react';
import {api} from '../api';
import type {Phase1Status} from '../types';

export function Phase1Evidence(){
  const [report,setReport]=useState<Phase1Status>();
  const [error,setError]=useState('');
  useEffect(()=>{api.phase1Status().then(setReport).catch(value=>setError(String(value)))},[]);
  if(error)return <section className="error"><b>Evidence audit failed closed.</b><p>{error}</p></section>;
  if(!report)return <div className="progress">Auditing repository evidence…</div>;
  const complete=report.stages.filter(stage=>stage.readiness==='COMPLETE').length;
  return <section><p className="eyebrow">PHASE-1 EVIDENCE</p><h2>{report.overall_evidence}</h2>
    <p>{complete} of {report.stages.length} frozen completion gates are complete or not applicable. Readiness never counts as evidence.</p>
    <div className="grid">{report.stages.map(stage=><article key={stage.id}>
      <b>{stage.id.replaceAll('_',' ').toUpperCase()}</b>
      <p><strong>Evidence:</strong> {stage.evidence_status}<br/><strong>Execution:</strong> {stage.readiness}<br/><strong>Mode:</strong> {stage.execution}</p>
      {stage.runner&&<p><code>{stage.runner}</code></p>}
      <small>Expected: {stage.expected_artifact}</small>
    </article>)}</div><aside><b>CLAIM BOUNDARY</b><p>{report.claim_boundary}</p></aside></section>;
}
