import {useState} from 'react';
import type {StatusRow} from '../types';
import {api} from '../api';
import {Badge} from './Badge';
import {JsonPanel} from './JsonPanel';

export function StatusView({rows}:{rows:StatusRow[]}){
  const [model,setModel]=useState<Record<string,unknown>>(); const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  async function preload(){setBusy(true);setError('');try{setModel(await api.preloadModel())}catch(e){setError(String(e));setModel(await api.modelStatus())}finally{setBusy(false)}}
  return <section><p className="eyebrow">SYSTEM STATUS</p><h2>Completed, experimental, and unopened work</h2><div className="actions"><button onClick={preload} disabled={busy}>{busy?'LOADING PINNED LOCAL MODEL…':'PRELOAD MODEL'}</button><button onClick={()=>api.modelStatus().then(setModel)}>REFRESH MEMORY</button></div><p>Warm-up is optional, local-cache-only, and loads one Qwen2.5-0.5B instance. The deterministic demo remains available if memory is insufficient.</p>{error&&<p className="error">Model not ready: {error}</p>}{model&&<JsonPanel title={model.ready?'Model Ready':'Model Not Ready'} value={model}/>}<table><thead><tr><th>Capability</th><th>Status</th></tr></thead><tbody>{rows.map(r=><tr key={r.capability}><td>{r.capability}</td><td><Badge tone={r.status.includes('VERIFIED')||r.status==='WORKING'?'green':r.status.includes('INSUFFICIENT')||r.status.includes('BLOCKED')?'red':'amber'}>{r.status}</Badge></td></tr>)}</tbody></table></section>
}
