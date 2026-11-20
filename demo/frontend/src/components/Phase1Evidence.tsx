import {useEffect,useState} from 'react';
import {api} from '../api';
import type {EvidenceCard,Phase1Status} from '../types';

export function Phase1Evidence(){
  const [report,setReport]=useState<Phase1Status>();
  const [cards,setCards]=useState<EvidenceCard[]>([]);
  const [error,setError]=useState('');
  useEffect(()=>{Promise.all([api.phase1Status(),api.evidence()]).then(([status,evidence])=>{setReport(status);setCards(evidence)}).catch(value=>setError(String(value)))},[]);
  if(error)return <section className="error"><b>Evidence audit failed closed.</b><p>{error}</p></section>;
  if(!report)return <div className="progress">Auditing repository evidence…</div>;
  const complete=report.stages.filter(stage=>stage.readiness==='COMPLETE').length;
  const supporting=cards.filter(card=>['Qwen SAE','SmolLM2 Qualification','Real-Qwen Agent C'].includes(card.title));
  return <section><p className="eyebrow">PHASE-1 EVIDENCE</p><h2>{report.overall_evidence}</h2>
    <p>{complete} of {report.stages.length} frozen completion gates are complete or not applicable. Readiness never counts as evidence.</p>
    <h3>Verified causal-core progression</h3><div className="grid">{cards.filter(card=>card.title.startsWith('CORE-')).map(card=><article key={card.title}>
      <b>{card.title}</b><p><strong>{card.status}</strong><br/>{card.provenance_type}</p>
      <small>{card.artifact}</small><pre>{JSON.stringify(card.details,null,2)}</pre>
    </article>)}</div><aside><b>INTERPRETATION</b><p>CORE-05 is a successful once-only internal test on the frozen synthetic substrate. The L20H5 repair requires a paired clean activation donor and is not an oracle-free deployable defense.</p></aside>
    <h3>Completed supporting studies</h3><p>Negative results are completed experiments, but they do not satisfy positive scientific completion gates.</p><div className="grid">{supporting.map(card=><article key={card.title}>
      <b>{card.title}</b><p><strong>{card.status}</strong><br/>{card.provenance_type}</p><small>{card.artifact}</small><pre>{JSON.stringify(card.details,null,2)}</pre>
    </article>)}</div>
    <div className="grid">{report.stages.map(stage=><article key={stage.id}>
      <b>{stage.id.replaceAll('_',' ').toUpperCase()}</b>
      <p><strong>Evidence:</strong> {stage.evidence_status}<br/><strong>Execution:</strong> {stage.readiness}<br/><strong>Mode:</strong> {stage.execution}</p>
      {stage.runner&&<p><code>{stage.runner}</code></p>}
      <small>Expected: {stage.expected_artifact}</small>
    </article>)}</div><aside><b>CLAIM BOUNDARY</b><p>{report.claim_boundary}</p></aside></section>;
}
