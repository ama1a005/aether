import type {PipelineRun} from '../types';
import {Badge} from './Badge';
import {JsonPanel} from './JsonPanel';

const stages=['Patient','WSO2 MCP','FHIR Adapter','Agent A','Mediator','Agent B','Decision'];
type View='AGENT PIPELINE'|'ATTACK LAB'|'CAUSAL ANALYSIS';

export function PipelineView({view,clean,attack,rescue,induction,busy,error,onClean,onAttack,onRescue,onInduction,onReset}:{view:View;clean?:PipelineRun;attack?:PipelineRun;rescue?:Record<string,unknown>;induction?:Record<string,unknown>;busy:string;error:string;onClean:()=>void;onAttack:()=>void;onRescue:()=>void;onInduction:()=>void;onReset:()=>void}){
  const shown=view==='ATTACK LAB'?(attack||clean):(clean||attack);
  const title=view==='AGENT PIPELINE'?'Clean sender-to-receiver execution':view==='ATTACK LAB'?'Controlled post-MCP evidence attack':'Message-level causal interventions';
  return <section><div className="section-head"><div><p className="eyebrow">{view}</p><h2>{title}</h2></div><Badge>{shown?.provenance_type||'READY'}</Badge></div>
    {view==='AGENT PIPELINE'&&<><div className="pipeline">{stages.map(s=><div className={busy?'running':shown?'complete':'waiting'} key={s}>{s}</div>)}</div><div className="actions"><button onClick={onClean} disabled={!!busy}>Run Clean Pipeline</button><button className="secondary" onClick={onReset}>Reset Case</button></div></>}
    {view==='ATTACK LAB'&&<><p>Raw FHIR remains unchanged. AETHER flips only the declared downstream <code>risk_flag</code> after MCP retrieval.</p><div className="actions"><button onClick={onClean} disabled={!!busy}>Run Clean Baseline</button><button onClick={onAttack} disabled={!!busy}>Run Controlled Attack</button><button className="secondary" onClick={onReset}>Reset Case</button></div></>}
    {view==='CAUSAL ANALYSIS'&&<><p>Each action executes its own aligned clean and attacked prerequisites on the backend; visiting another page first is not required.</p><div className="actions"><button onClick={onRescue} disabled={!!busy}>Run Clean-Message Rescue</button><button onClick={onInduction} disabled={!!busy}>Run Attacked-Message Induction</button><button className="secondary" onClick={onReset}>Reset Case</button></div></>}
    {busy&&<div className="progress">{busy}… elapsed time is recorded by the backend.</div>}{error&&<div className="error">Stage failed: {error}</div>}
    {attack?.attack_delta&&view==='ATTACK LAB'&&<div className="diff"><h3>Attack delta</h3><div><code>{attack.attack_delta.path}</code> <b>{attack.attack_delta.clean}</b> → <b>{attack.attack_delta.attacked}</b></div><p>All non-designated fixture fields remain unchanged.</p></div>}
    {shown&&view!=='CAUSAL ANALYSIS'&&<div className="grid"><article><h3>Agent A / Sender</h3><JsonPanel title="Rendered input and raw output" value={shown.sender}/></article><article><h3>Serialized mediator</h3><p className="hash">SHA-256 {shown.mediator.sha256}</p><JsonPanel title="Raw and parsed mediator" value={shown.mediator}/></article><article><h3>Agent B / Receiver</h3><div className={`decision ${shown.receiver.decision==='ESCALATE'?'danger':'safe'}`}>{shown.receiver.decision}</div><p>Raw code: {shown.receiver.raw_output} · score: {shown.receiver.score}</p></article></div>}
    {rescue&&view==='CAUSAL ANALYSIS'&&<article className="rescue"><Badge tone="green">LEVEL 1 MESSAGE CAUSALITY</Badge><h3>Clean-message rescue</h3><JsonPanel title="Actual intervention output" value={rescue}/></article>}
    {induction&&view==='CAUSAL ANALYSIS'&&<article className="rescue"><Badge tone="amber">ATTACKED-MESSAGE INDUCTION</Badge><h3>Reverse-direction intervention</h3><JsonPanel title="Actual intervention output" value={induction}/></article>}
  </section>
}
