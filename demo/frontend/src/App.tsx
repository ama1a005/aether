import {useEffect,useState} from 'react';
import {api} from './api';
import type {DemoCase,ExecutionMode,PipelineRun} from './types';
import {CaseWorkspace} from './components/CaseWorkspace';
import {PipelineView} from './components/PipelineView';
import {JsonPanel} from './components/JsonPanel';
import {Phase1Evidence} from './components/Phase1Evidence';

const views=['CASE WORKSPACE','FHIR MCP DATA','AGENT PIPELINE','ATTACK LAB','CAUSAL ANALYSIS','PHASE-1 EVIDENCE'] as const;
const labels=['Select a record','Retrieve evidence','Run the agents','Apply the attack','Test the repair','Show experimental results'];
const descriptions=['Inspect the source record and its diagnostic labels.','Inspect the data supplied to the agents.','Follow evidence from Agent A through the message to Agent B.','Change the declared evidence field and compare the decision.','Restore the clean message and inspect the resulting decision.','Review retained Qwen experiments and their measured outcomes.'];
export default function App(){
 const [cases,setCases]=useState<DemoCase[]>([]),[caseId,setCaseId]=useState('DEMO-PAT-001'),[step,setStep]=useState(0);
 const [mode,setMode]=useState<ExecutionMode>(new URLSearchParams(location.search).get('mode')==='real_fhir_mcp_deterministic'?'real_fhir_mcp_deterministic':'mock_deterministic');
 const [discovery,setDiscovery]=useState<unknown>(),[tools,setTools]=useState<unknown>(),[clean,setClean]=useState<PipelineRun>(),[attack,setAttack]=useState<PipelineRun>();
 const [rescue,setRescue]=useState<Record<string,unknown>>(),[induction,setInduction]=useState<Record<string,unknown>>();
 const [busy,setBusy]=useState(''),[error,setError]=useState('');
 useEffect(()=>{api.cases().then(setCases).catch(e=>setError(String(e)))},[]);
 const item=cases.find(c=>c.case_id===caseId);
 function reset(){setDiscovery(undefined);setTools(undefined);setClean(undefined);setAttack(undefined);setRescue(undefined);setInduction(undefined);setError('')}
 async function task(label:string,call:()=>Promise<any>,save:(value:any)=>void){setBusy(label);setError('');try{save(await call())}catch(e){setError(String(e))}finally{setBusy('')}}
 const ready=[!!item,!!tools,!!clean,!!attack,!!rescue,true];
 return <><header><span className="mark">AETHER</span><span>Cross-Agent Causal Analysis</span></header>
 <div className="shell"><nav aria-label="Workflow">{labels.map((label,index)=><button key={label} disabled={!!busy} className={step===index?'active':''} onClick={()=>setStep(index)}><span>{String(index+1).padStart(2,'0')}</span> {label}</button>)}</nav>
 <main><div className="section-head"><div><p className="eyebrow">STEP {step+1} OF 6</p><h1>{labels[step]}</h1><p>{descriptions[step]}</p></div></div>
 {step===0&&<div className="actions"><label>Execution <select aria-label="execution mode" disabled={!!busy} value={mode} onChange={e=>{setMode(e.target.value as ExecutionMode);reset()}}><option value="mock_deterministic">Local deterministic pipeline</option><option value="real_fhir_mcp_deterministic">WSO2 FHIR MCP Server · deterministic agents</option></select></label></div>}
 <p className="execution-note">{mode==='mock_deterministic'?'Local deterministic execution using PTB-XL metadata.':'WSO2 FHIR MCP Server over Streamable HTTP; deterministic agents.'} Retained real-model results appear in step 6.</p>
 {error&&<div className="error" role="alert">{error}<p>The operation did not complete. Retry after resolving the reported service error.</p></div>}
 {!item&&!error&&<p role="status">Loading records…</p>}
 {item&&step===0&&<CaseWorkspace item={item} cases={cases} onSelect={id=>{setCaseId(id);reset()}}/>}
 {item&&step===1&&<section><h2>{item.display_name}</h2><div className="actions">{mode==='real_fhir_mcp_deterministic'&&<button disabled={!!busy} onClick={()=>task('Discovering tools',()=>api.discover(),setDiscovery)}>Discover MCP Tools</button>}<button disabled={!!busy} onClick={()=>task('Retrieving evidence',()=>api.tools(caseId,mode),setTools)}>Retrieve record evidence</button></div>{busy&&<p role="status">{busy}…</p>}{discovery!==undefined&&<JsonPanel title="Discovered MCP tools" value={discovery}/>} {tools!==undefined&&<JsonPanel title="Retrieved evidence and source provenance" value={tools}/>}</section>}
 {item&&step>=2&&step<=4&&<PipelineView mode={mode} view={views[step] as 'AGENT PIPELINE'|'ATTACK LAB'|'CAUSAL ANALYSIS'} clean={clean} attack={attack} rescue={rescue} induction={induction} busy={busy} error="" onClean={()=>{setClean(undefined);setAttack(undefined);setRescue(undefined);setInduction(undefined);task('Running clean pipeline',()=>api.clean(caseId,mode),setClean)}} onAttack={()=>{setAttack(undefined);setRescue(undefined);setInduction(undefined);task('Running attack',()=>api.attack(caseId,mode),setAttack)}} onRescue={()=>task('Running rescue',()=>api.rescue(caseId,mode),setRescue)} onInduction={()=>task('Running induction',()=>api.induction(caseId,mode),setInduction)} onReset={reset}/>}
 {step===5&&<Phase1Evidence/>}
 <footer className="workflow-footer"><button className="secondary" disabled={step===0||!!busy} onClick={()=>setStep(step-1)}>Previous</button><span>{ready[step]?'Ready to continue':'Run this stage to continue'}</span>{step<5?<button disabled={!ready[step]||!!busy} onClick={()=>setStep(step+1)}>Continue to {labels[step+1].toLowerCase()} →</button>:<button disabled={!!busy} onClick={()=>{reset();setStep(0)}}>Start another walkthrough</button>}</footer>
 </main></div></>;
}
