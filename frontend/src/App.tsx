import { useEffect, useMemo, useState } from 'react'
import { Activity, Database, FileUp, Layers3, Server, ShieldAlert } from 'lucide-react'
import { API, assess, getWorkloads, planWaves, uploadInventory } from './api'

type Workload = {
  id:number; name:string; cpu:number; memory_gb:number; storage_gb:number; os:string;
  source_network:string; target_network:string; criticality:string; downtime_minutes:number;
  app_group:string; owner:string; migration_score:number|null; migration_risk:string|null;
  migration_reasons:string|null; wave_number:number|null;
}

export default function App(){
  const [rows,setRows]=useState<Workload[]>([]); const [busy,setBusy]=useState(false); const [message,setMessage]=useState('')
  const refresh=async()=>setRows(await getWorkloads())
  useEffect(()=>{refresh().catch(()=>{})},[])
  const stats=useMemo(()=>({
    vms: rows.length,
    cpu: rows.reduce((a,b)=>a+b.cpu,0),
    ram: rows.reduce((a,b)=>a+b.memory_gb,0),
    storage: rows.reduce((a,b)=>a+b.storage_gb,0),
    waves: Math.max(0,...rows.map(r=>r.wave_number||0)),
    high: rows.filter(r=>r.migration_risk==='High').length,
  }),[rows])
  const act=async(fn:()=>Promise<any>, ok:string)=>{setBusy(true);setMessage('');try{await fn();await refresh();setMessage(ok)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
  const upload=async(e:any)=>{const f=e.target.files?.[0];if(f) await act(()=>uploadInventory(f),`Imported ${f.name}`)}
  return <div className="page">
    <header><div><p className="eyebrow">VMWARE → NUTANIX AHV</p><h1>Migration Factory</h1><p className="subtitle">Inventory normalization, explainable migration complexity, wave planning and Prism Central discovery.</p></div><div className="badge"><Activity size={18}/> v0.1 MVP</div></header>
    <section className="actions">
      <label className="button primary"><FileUp size={17}/> Import RVTools <input type="file" accept=".csv,.xlsx,.xlsm" onChange={upload}/></label>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(assess,'Assessment complete')}><ShieldAlert size={17}/> Run assessment</button>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(planWaves,'Migration waves generated')}><Layers3 size={17}/> Plan waves</button>
      <a className="button" href={`${API}/api/v1/reports/migration-plan.csv`}><Database size={17}/> Export plan</a>
    </section>
    {message && <div className="notice">{message}</div>}
    <section className="stats">
      <Stat icon={<Server/>} label="Workloads" value={stats.vms}/><Stat label="vCPU" value={stats.cpu}/><Stat label="Memory" value={`${Math.round(stats.ram)} GB`}/><Stat label="Storage" value={`${Math.round(stats.storage/1024*10)/10} TB`}/><Stat label="Waves" value={stats.waves}/><Stat label="High complexity" value={stats.high}/>
    </section>
    <section className="panel"><div className="panelHead"><div><h2>Estate assessment</h2><p>Scores represent migration complexity, not Nutanix compatibility.</p></div></div>
      <div className="tableWrap"><table><thead><tr><th>Wave</th><th>VM</th><th>App</th><th>Size</th><th>Network</th><th>Criticality</th><th>Score</th><th>Risk</th></tr></thead><tbody>
        {rows.map(r=><tr key={r.id}><td>{r.wave_number||'—'}</td><td><strong>{r.name}</strong><span>{r.os}</span></td><td>{r.app_group}</td><td>{r.cpu} vCPU<br/>{r.memory_gb} GB RAM<br/>{r.storage_gb} GB</td><td>{r.source_network}<span>→ {r.target_network||'unmapped'}</span></td><td>{r.criticality}<span>{r.downtime_minutes}m max downtime</span></td><td>{r.migration_score??'—'}</td><td><Risk value={r.migration_risk}/></td></tr>)}
        {!rows.length&&<tr><td colSpan={8} className="empty">Import <code>samples/rvtools_sample.csv</code> to begin.</td></tr>}
      </tbody></table></div>
    </section>
  </div>
}
function Stat({label,value,icon}:{label:string,value:any,icon?:any}){return <div className="stat">{icon}<div><span>{label}</span><strong>{value}</strong></div></div>}
function Risk({value}:{value:string|null}){return value?<span className={`risk ${value.toLowerCase()}`}>{value}</span>:<>—</>}
