import { useEffect, useMemo, useState } from 'react'
import { Activity, ClipboardCheck, Database, FileText, FileUp, Layers3, Map, Server, ShieldAlert } from 'lucide-react'
import { API, applyNetworkMapping, assess, getReadiness, getRunbook, getWorkloads, planWaves, uploadInventory } from './api'

type Workload = {
  id:number; name:string; cpu:number; memory_gb:number; storage_gb:number; os:string;
  source_network:string; target_network:string; criticality:string; downtime_minutes:number;
  app_group:string; owner:string; migration_score:number|null; migration_risk:string|null;
  migration_reasons:string|null; wave_number:number|null;
}

type Readiness = {
  total:number; ready:number; ready_with_warnings:number; blocked:number;
  workloads:{workload_id:number;name:string;status:string;blockers:string[];warnings:string[]}[]
}

const DEFAULT_MAPPING = `# source=target
VLAN120=AHV-PROD-APP
VLAN121=AHV-PROD-DB
DEV-*=AHV-DEV`

export default function App(){
  const [rows,setRows]=useState<Workload[]>([])
  const [busy,setBusy]=useState(false)
  const [message,setMessage]=useState('')
  const [mappingText,setMappingText]=useState(DEFAULT_MAPPING)
  const [readiness,setReadiness]=useState<Readiness|null>(null)
  const [runbook,setRunbook]=useState<any|null>(null)

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

  const act=async(fn:()=>Promise<any>, ok:string)=>{
    setBusy(true); setMessage('')
    try{ await fn(); await refresh(); setMessage(ok) }
    catch(e:any){ setMessage(e.message) }
    finally{ setBusy(false) }
  }

  const upload=async(e:any)=>{
    const f=e.target.files?.[0]
    if(f){
      setReadiness(null); setRunbook(null)
      await act(()=>uploadInventory(f),`Imported ${f.name}`)
    }
  }

  const applyMappings=async()=>{
    const rules=mappingText.split('\n')
      .map(x=>x.trim())
      .filter(x=>x && !x.startsWith('#') && x.includes('='))
      .map(x=>{
        const idx=x.indexOf('=')
        return {source:x.slice(0,idx).trim(),target:x.slice(idx+1).trim()}
      })
      .filter(x=>x.source && x.target)
    if(!rules.length){setMessage('Add at least one source=target mapping rule');return}
    await act(()=>applyNetworkMapping(rules),`Applied ${rules.length} network mapping rule(s)`)
  }

  const checkReadiness=async()=>{
    setBusy(true); setMessage('')
    try{
      const r=await getReadiness()
      setReadiness(r)
      setMessage(`Readiness checked: ${r.blocked} blocked, ${r.ready_with_warnings} with warnings`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const loadRunbook=async(wave:number)=>{
    setBusy(true);setMessage('')
    try{setRunbook(await getRunbook(wave))}
    catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  return <div className="page">
    <header>
      <div>
        <p className="eyebrow">VMWARE → NUTANIX AHV</p>
        <h1>Migration Factory</h1>
        <p className="subtitle">Enterprise migration assessment, deterministic network mapping, readiness controls, wave planning and Prism Central discovery.</p>
      </div>
      <div className="badge"><Activity size={18}/> v0.2</div>
    </header>

    <section className="actions">
      <label className="button primary"><FileUp size={17}/> Import RVTools <input type="file" accept=".csv,.xlsx,.xlsm" onChange={upload}/></label>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(assess,'Assessment complete')}><ShieldAlert size={17}/> Assess</button>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(planWaves,'Migration waves generated')}><Layers3 size={17}/> Plan waves</button>
      <button className="button" disabled={busy||!rows.length} onClick={checkReadiness}><ClipboardCheck size={17}/> Readiness</button>
      <a className="button" href={`${API}/api/v1/reports/migration-plan.csv`}><Database size={17}/> Export plan</a>
    </section>

    {message && <div className="notice">{message}</div>}

    <section className="stats">
      <Stat icon={<Server/>} label="Workloads" value={stats.vms}/>
      <Stat label="vCPU" value={stats.cpu}/>
      <Stat label="Memory" value={`${Math.round(stats.ram)} GB`}/>
      <Stat label="Storage" value={`${Math.round(stats.storage/1024*10)/10} TB`}/>
      <Stat label="Waves" value={stats.waves}/>
      <Stat label="High complexity" value={stats.high}/>
    </section>

    <section className="planningGrid">
      <div className="panel planningPanel">
        <div className="panelHead">
          <div><h2><Map size={18}/> AHV network mapping</h2><p>Map VMware port groups/VLANs to target AHV subnets. Wildcards are supported.</p></div>
        </div>
        <div className="panelBody">
          <textarea value={mappingText} onChange={e=>setMappingText(e.target.value)} spellCheck={false}/>
          <button className="button primary" disabled={busy||!rows.length} onClick={applyMappings}>Apply network map</button>
        </div>
      </div>

      <div className="panel planningPanel">
        <div className="panelHead">
          <div><h2><ClipboardCheck size={18}/> Migration readiness</h2><p>Planning gate only; it is not a Nutanix Move compatibility certification.</p></div>
        </div>
        <div className="panelBody">
          {readiness ? <div className="readinessGrid">
            <Mini label="Ready" value={readiness.ready} tone="ok"/>
            <Mini label="Warnings" value={readiness.ready_with_warnings} tone="warn"/>
            <Mini label="Blocked" value={readiness.blocked} tone="bad"/>
          </div> : <p className="muted">Run Readiness after mapping target networks.</p>}
          {readiness?.workloads.filter(x=>x.status==='Blocked').slice(0,4).map(x=>
            <div className="blocker" key={x.workload_id}><strong>{x.name}</strong><span>{x.blockers.join(' • ')}</span></div>
          )}
        </div>
      </div>
    </section>

    <section className="panel">
      <div className="panelHead">
        <div><h2>Estate assessment</h2><p>Scores represent migration complexity, not Nutanix compatibility.</p></div>
      </div>
      <div className="tableWrap"><table><thead><tr><th>Wave</th><th>VM</th><th>App</th><th>Size</th><th>Network</th><th>Criticality</th><th>Score</th><th>Risk</th><th>Runbook</th></tr></thead><tbody>
        {rows.map(r=><tr key={r.id}>
          <td>{r.wave_number||'—'}</td>
          <td><strong>{r.name}</strong><span>{r.os}</span></td>
          <td>{r.app_group}</td>
          <td>{r.cpu} vCPU<br/>{r.memory_gb} GB RAM<br/>{r.storage_gb} GB</td>
          <td>{r.source_network}<span>→ {r.target_network||'unmapped'}</span></td>
          <td>{r.criticality}<span>{r.downtime_minutes}m max downtime</span></td>
          <td>{r.migration_score??'—'}</td>
          <td><Risk value={r.migration_risk}/></td>
          <td>{r.wave_number?<button className="iconButton" title="Open wave runbook" onClick={()=>loadRunbook(r.wave_number!)}><FileText size={16}/></button>:'—'}</td>
        </tr>)}
        {!rows.length&&<tr><td colSpan={9} className="empty">Import <code>samples/rvtools_sample.csv</code> to begin.</td></tr>}
      </tbody></table></div>
    </section>

    {runbook && <section className="panel runbookPanel">
      <div className="panelHead"><div><h2>Wave {runbook.wave} cutover / rollback runbook</h2><p>{runbook.workloads.join(', ')}</p></div><button className="button" onClick={()=>setRunbook(null)}>Close</button></div>
      <div className="runbookCols">
        <RunbookList title="Pre-cutover" items={runbook.pre_cutover}/>
        <RunbookList title="Cutover" items={runbook.cutover}/>
        <RunbookList title="Rollback" items={runbook.rollback}/>
      </div>
    </section>}
  </div>
}

function Stat({label,value,icon}:{label:string,value:any,icon?:any}){return <div className="stat">{icon}<div><span>{label}</span><strong>{value}</strong></div></div>}
function Risk({value}:{value:string|null}){return value?<span className={`risk ${value.toLowerCase()}`}>{value}</span>:<>—</>}
function Mini({label,value,tone}:{label:string,value:number,tone:string}){return <div className={`mini ${tone}`}><span>{label}</span><strong>{value}</strong></div>}
function RunbookList({title,items}:{title:string,items:string[]}){return <div><h3>{title}</h3><ol>{items.map((x,i)=><li key={i}>{x}</li>)}</ol></div>}
