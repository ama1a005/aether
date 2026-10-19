import {useEffect,useState} from 'react';
import {api} from './api';
import type {DemoCase,EvidenceCard,ExecutionMode,PipelineRun,ReplayBundle,StatusRow} from './types';
import {CaseWorkspace} from './components/CaseWorkspace';
import {PipelineView} from './components/PipelineView';
import {EvidenceView} from './components/EvidenceView';
import {StatusView} from './components/StatusView';
import {JsonPanel} from './components/JsonPanel';

const views=['CASE WORKSPACE','MCP TOOLS','AGENT PIPELINE','ATTACK LAB','CAUSAL ANALYSIS','RESEARCH EVIDENCE','SYSTEM STATUS'] as const;

export default function App(){
  const [cases,setCases]=useState<DemoCase[]>([]); const [caseId,setCaseId]=useState('DEMO-PAT-001');
  const [view,setView]=useState<(typeof views)[number]>('CASE WORKSPACE'); const [mode,setMode]=useState<ExecutionMode>('deterministic');
  const [replaySource,setReplaySource]=useState<'deterministic'|'live'>('deterministic');
  const [tools,setTools]=useState<unknown[]>(); const [clean,setClean]=useState<PipelineRun>(); const [attack,setAttack]=useState<PipelineRun>();
  const [rescue,setRescue]=useState<Record<string,unknown>>(); const [induction,setInduction]=useState<Record<string,unknown>>(); const [evidence,setEvidence]=useState<EvidenceCard[]>([]); const [status,setStatus]=useState<StatusRow[]>([]);
  const [busy,setBusy]=useState(''); const [error,setError]=useState(''); const [review,setReview]=useState(false);
  useEffect(()=>{api.cases().then(setCases).catch(e=>setError(String(e)));api.evidence().then(setEvidence);api.status().then(setStatus)},[]);
  const item=cases.find(c=>c.case_id===caseId);
  async function task(label:string,fn:()=>Promise<unknown>,save:(x:any)=>void){setBusy(label);setError('');try{save(await fn())}catch(e){setError(String(e))}finally{setBusy('')}}
  async function loadReplay(){await task(`Loading verified ${replaySource} replay`,()=>replaySource==='live'?api.liveReplay(caseId):api.replay(caseId),(bundle:ReplayBundle)=>{setClean(bundle.clean);setAttack(bundle.attacked);setRescue(bundle.rescue)})}
  function reset(){setTools(undefined);setClean(undefined);setAttack(undefined);setRescue(undefined);setInduction(undefined);setError('')}
  const execute=(call:()=>Promise<unknown>,save:(x:any)=>void)=>mode==='replay'?loadReplay():task(mode==='live_model_mcp'?'Running real Qwen + MCP stage':'Running deterministic fallback stage',call,save);
  const modeLabel=mode==='live_model_mcp'?'LIVE LOCAL MODEL + REAL MCP':mode==='deterministic'?'DETERMINISTIC FALLBACK':replaySource==='live'?'VERIFIED LIVE-MODEL REPLAY':'VERIFIED DETERMINISTIC REPLAY';
  return <><header><div><span className="mark">AETHER</span><small>INTERMEDIATE REVIEW · LOCALHOST</small></div><div className="actions"><select aria-label="execution mode" value={mode} onChange={e=>{setMode(e.target.value as ExecutionMode);reset()}}><option value="live_model_mcp">Live Qwen + real MCP</option><option value="deterministic">Deterministic fallback</option><option value="replay">Verified replay</option></select>{mode==='replay'&&<select aria-label="replay source" value={replaySource} onChange={e=>{setReplaySource(e.target.value as 'deterministic'|'live');reset()}}><option value="deterministic">Deterministic replay</option><option value="live">Live-model replay</option></select>}<label><input type="checkbox" checked={review} onChange={e=>setReview(e.target.checked)}/> Review mode</label></div></header><div className="notice">Mode: <b>{modeLabel}</b>. Synthetic research demonstration only; not clinical decision support.</div><div className="shell"><nav>{views.map(v=><button className={view===v?'active':''} key={v} onClick={()=>setView(v)}>{v}</button>)}</nav><main>{cases.length===0&&!error&&<div className="progress">Loading the 12 synthetic demo cases from the local API…</div>}{error&&<div className="error"><b>Local demo request failed.</b><br/>{error}<br/>Verify <code>http://127.0.0.1:8000/api/demo/health</code>, then refresh this page.</div>}{mode==='replay'&&<div className="notice"><b>{modeLabel}</b> <button onClick={loadReplay}>Load selected case replay</button></div>}{item&&view==='CASE WORKSPACE'&&<CaseWorkspace item={item} cases={cases} onSelect={id=>{setCaseId(id);reset()}}/>}{item&&view==='MCP TOOLS'&&<section><p className="eyebrow">MCP TOOLS</p><h2>{item.case_id} tool workspace</h2><button onClick={()=>task('Running tools',()=>api.tools(caseId,mode),setTools)} disabled={!!busy||mode==='replay'}>Run All Tools</button>{tools&&<JsonPanel title="Exact backend tool responses" value={tools}/>}</section>}{item&&(view==='AGENT PIPELINE'||view==='ATTACK LAB'||view==='CAUSAL ANALYSIS')&&<PipelineView view={view} clean={clean} attack={attack} rescue={rescue} induction={induction} busy={busy} error={error} onClean={()=>execute(()=>api.clean(caseId,mode),setClean)} onAttack={()=>execute(()=>api.attack(caseId,mode),setAttack)} onRescue={()=>execute(()=>api.rescue(caseId,mode),setRescue)} onInduction={()=>execute(()=>api.induction(caseId,mode),setInduction)} onReset={reset}/>} {view==='RESEARCH EVIDENCE'&&<EvidenceView cards={evidence}/>} {view==='SYSTEM STATUS'&&<StatusView rows={status}/>} {review&&<aside><b>REVIEW MODE</b><p>Demo UI → <code>demo/backend/app.py</code> → explicit execution mode.</p><p>Scientific cards are read from committed result artifacts; they are not recomputed.</p></aside>}</main></div></>
}
