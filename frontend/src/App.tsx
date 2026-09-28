import { useEffect, useMemo, useState } from 'react'
import {
  Activity, CheckCircle2, ClipboardCheck, Database, FileText, FileUp, Gauge, Layers3, Map,
  Server, ShieldAlert, UserCheck, Waypoints, XCircle
} from 'lucide-react'
import {
  API, applyNetworkMapping, assess, createTargetCluster, decideApproval, evaluateWaveCapacity,
  getApprovals, getReadiness, getRunbook, getTargetClusters, getWorkloads, planWaves,
  reconcilePrismClusters, requestWaveApproval, updateTargetCluster, uploadInventory
} from './api'

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

type TargetCluster = {
  id:number; name:string; prism_ext_id:string; physical_cpu_cores:number;
  cpu_overcommit_ratio:number; allocated_vcpu:number; total_memory_gb:number;
  used_memory_gb:number; usable_storage_gb:number; used_storage_gb:number; enabled:boolean;
}

type Approval = {
  id:number; wave_number:number; target_cluster_id:number; status:string;
  requested_by:string; requested_at:string; decided_by:string; decided_at:string|null;
  change_ticket:string; notes:string; decision_notes:string; headroom_percent:number;
}

type CapacityEvaluation = {
  headroom_percent:number;
  demand:{wave:number;workloads:number;vcpu:number;memory_gb:number;storage_gb:number};
  candidates:{
    cluster_id:number;cluster_name:string;fit:boolean;score:number;reasons:string[];
    projected_vcpu:number;projected_memory_gb:number;projected_storage_gb:number;
    max_vcpu_after_headroom:number;max_memory_after_headroom_gb:number;max_storage_after_headroom_gb:number;
  }[];
}

const DEFAULT_MAPPING = `# source=target
VLAN120=AHV-PROD-APP
VLAN121=AHV-PROD-DB
DEV-*=AHV-DEV`

const EMPTY_CLUSTER = {
  name:'AHV-PROD-A', prism_ext_id:'', physical_cpu_cores:64, cpu_overcommit_ratio:4,
  allocated_vcpu:80, total_memory_gb:1024, used_memory_gb:320,
  usable_storage_gb:20000, used_storage_gb:7000, enabled:true,
}

export default function App(){
  const [rows,setRows]=useState<Workload[]>([])
  const [busy,setBusy]=useState(false)
  const [message,setMessage]=useState('')
  const [mappingText,setMappingText]=useState(DEFAULT_MAPPING)
  const [readiness,setReadiness]=useState<Readiness|null>(null)
  const [runbook,setRunbook]=useState<any|null>(null)
  const [clusters,setClusters]=useState<TargetCluster[]>([])
  const [clusterForm,setClusterForm]=useState<any>(EMPTY_CLUSTER)
  const [editingClusterId,setEditingClusterId]=useState<number|null>(null)
  const [capacity,setCapacity]=useState<CapacityEvaluation|null>(null)
  const [capacityWave,setCapacityWave]=useState(1)
  const [headroom,setHeadroom]=useState(20)
  const [prismStatus,setPrismStatus]=useState<any|null>(null)
  const [approvals,setApprovals]=useState<Approval[]>([])
  const [approvalWave,setApprovalWave]=useState(1)
  const [approvalClusterId,setApprovalClusterId]=useState(0)
  const [requestedBy,setRequestedBy]=useState('migration.engineer')
  const [changeTicket,setChangeTicket]=useState('CHG-2026-0042')
  const [decidedBy,setDecidedBy]=useState('change.manager')

  const refresh=async()=>setRows(await getWorkloads())
  const refreshClusters=async()=>setClusters(await getTargetClusters())
  const refreshApprovals=async()=>setApprovals(await getApprovals())
  useEffect(()=>{refresh().catch(()=>{});refreshClusters().catch(()=>{});refreshApprovals().catch(()=>{})},[])

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
      setReadiness(null); setRunbook(null); setCapacity(null)
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

  const saveCluster=async()=>{
    setBusy(true);setMessage('')
    try{
      if(editingClusterId){
        await updateTargetCluster(editingClusterId,clusterForm)
        setMessage(`Target cluster ${clusterForm.name} updated`)
      }else{
        await createTargetCluster(clusterForm)
        setMessage(`Target cluster ${clusterForm.name} added`)
      }
      await refreshClusters()
      setEditingClusterId(null)
      setClusterForm({...EMPTY_CLUSTER,name:`AHV-PROD-${clusters.length+2}`})
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const editCluster=(cluster:TargetCluster)=>{
    setEditingClusterId(cluster.id)
    setClusterForm({...cluster})
  }

  const evalCapacity=async()=>{
    setBusy(true);setMessage('')
    try{
      const result=await evaluateWaveCapacity(capacityWave,headroom)
      setCapacity(result)
      const fit=result.candidates.filter((x:any)=>x.fit).length
      setMessage(`Wave ${capacityWave}: ${fit}/${result.candidates.length} cluster(s) fit the configured headroom policy`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const reconcile=async()=>{
    setBusy(true);setMessage('')
    try{
      const result=await reconcilePrismClusters()
      setPrismStatus(result)
      setMessage(`Prism reconciliation: ${result.matched} matched, ${result.unmatched} unmatched`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const requestApproval=async()=>{
    if(!approvalClusterId){setMessage('Select a target cluster before requesting approval');return}
    setBusy(true);setMessage('')
    try{
      await requestWaveApproval(approvalWave,{
        target_cluster_id:approvalClusterId,
        requested_by:requestedBy,
        change_ticket:changeTicket,
        headroom_percent:headroom,
        notes:'Requested from Migration Factory governance dashboard',
      })
      await refreshApprovals()
      setMessage(`Wave ${approvalWave} submitted for change approval`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const decide=async(id:number,decision:'Approved'|'Rejected')=>{
    setBusy(true);setMessage('')
    try{
      await decideApproval(id,{decision,decided_by:decidedBy,notes:`${decision} from governance dashboard`})
      await refreshApprovals()
      setMessage(`Approval #${id} marked ${decision}`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  return <div className="page">
    <header>
      <div>
        <p className="eyebrow">VMWARE → NUTANIX AHV</p>
        <h1>Migration Factory</h1>
        <p className="subtitle">Enterprise migration assessment, deterministic network mapping, readiness controls, target-cluster capacity planning and Prism Central reconciliation.</p>
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

    <section className="panel capacityPanel">
      <div className="panelHead">
        <div><h2><Gauge size={18}/> Target AHV capacity planner</h2><p>Model placement using an explicit CPU overcommit envelope plus memory/storage headroom.</p></div>
        <button className="button" disabled={busy} onClick={reconcile}><Waypoints size={16}/> Reconcile Prism</button>
      </div>
      <div className="capacityLayout">
        <div className="clusterForm">
          <h3>Add target cluster</h3>
          <div className="formGrid">
            <Field label="Cluster name" value={clusterForm.name} onChange={(v:any)=>setClusterForm({...clusterForm,name:v})}/>
            <Field label="Prism extId (optional)" value={clusterForm.prism_ext_id} onChange={(v:any)=>setClusterForm({...clusterForm,prism_ext_id:v})}/>
            <Field label="Physical CPU cores" type="number" value={clusterForm.physical_cpu_cores} onChange={(v:any)=>setClusterForm({...clusterForm,physical_cpu_cores:+v})}/>
            <Field label="CPU overcommit ratio" type="number" step="0.5" value={clusterForm.cpu_overcommit_ratio} onChange={(v:any)=>setClusterForm({...clusterForm,cpu_overcommit_ratio:+v})}/>
            <Field label="Allocated vCPU" type="number" value={clusterForm.allocated_vcpu} onChange={(v:any)=>setClusterForm({...clusterForm,allocated_vcpu:+v})}/>
            <Field label="Total memory GB" type="number" value={clusterForm.total_memory_gb} onChange={(v:any)=>setClusterForm({...clusterForm,total_memory_gb:+v})}/>
            <Field label="Used memory GB" type="number" value={clusterForm.used_memory_gb} onChange={(v:any)=>setClusterForm({...clusterForm,used_memory_gb:+v})}/>
            <Field label="Usable storage GB" type="number" value={clusterForm.usable_storage_gb} onChange={(v:any)=>setClusterForm({...clusterForm,usable_storage_gb:+v})}/>
            <Field label="Used storage GB" type="number" value={clusterForm.used_storage_gb} onChange={(v:any)=>setClusterForm({...clusterForm,used_storage_gb:+v})}/>
          </div>
          <div className="formActions">
            <button className="button primary" disabled={busy} onClick={saveCluster}>{editingClusterId?'Save cluster':'Add target cluster'}</button>
            {editingClusterId && <button className="button" disabled={busy} onClick={()=>{setEditingClusterId(null);setClusterForm(EMPTY_CLUSTER)}}>Cancel edit</button>}
          </div>
        </div>

        <div className="clusterList">
          <div className="capacityControls">
            <label>Wave<input type="number" min="1" value={capacityWave} onChange={e=>setCapacityWave(+e.target.value)}/></label>
            <label>Headroom %<input type="number" min="0" max="50" value={headroom} onChange={e=>setHeadroom(+e.target.value)}/></label>
            <button className="button primary" disabled={busy||!clusters.length||!stats.waves} onClick={evalCapacity}>Evaluate placement</button>
          </div>

          {!clusters.length && <p className="muted">Add at least one target cluster capacity profile.</p>}
          {clusters.map(c=><div className="clusterCard" key={c.id}>
            <div><strong>{c.name}</strong><span>{c.prism_ext_id||'No Prism extId configured'}</span></div>
            <div className="clusterMetrics">
              <span>{c.physical_cpu_cores} cores × {c.cpu_overcommit_ratio}x</span>
              <span>{c.used_memory_gb}/{c.total_memory_gb} GB RAM</span>
              <span>{Math.round(c.used_storage_gb/1024*10)/10}/{Math.round(c.usable_storage_gb/1024*10)/10} TB</span>
            </div>
            <button className="iconButton textButton" title="Edit target cluster" onClick={()=>editCluster(c)}>Edit</button>
          </div>)}

          {capacity && <div className="placementResults">
            <h3>Wave {capacity.demand.wave} demand: {capacity.demand.vcpu} vCPU · {capacity.demand.memory_gb} GB RAM · {Math.round(capacity.demand.storage_gb/1024*10)/10} TB</h3>
            {capacity.candidates.map(c=><div className={`placement ${c.fit?'fit':'nofit'}`} key={c.cluster_id}>
              <div><strong>{c.cluster_name}</strong><span>{c.fit?'Fits policy':'Does not fit policy'} · score {c.score}</span></div>
              <ul>{c.reasons.map((x,i)=><li key={i}>{x}</li>)}</ul>
            </div>)}
          </div>}

          {prismStatus && <div className="prismSummary">Prism Central: <strong>{prismStatus.matched} matched</strong> · {prismStatus.unmatched} unmatched · {prismStatus.prism_clusters} discovered</div>}
        </div>
      </div>
      <p className="capacityDisclaimer">Capacity results are a planning envelope, not a production sizing recommendation. Final sizing must consider measured utilization, HA/N+1, resiliency, reservations and current Nutanix sizing guidance.</p>
    </section>

    <section className="panel governancePanel">
      <div className="panelHead">
        <div><h2><UserCheck size={18}/> Migration governance</h2><p>Approval requests are accepted only after readiness and selected-cluster capacity gates pass.</p></div>
      </div>
      <div className="governanceLayout">
        <div className="approvalForm">
          <div className="formGrid governanceFields">
            <Field label="Wave" type="number" value={approvalWave} onChange={(v:any)=>setApprovalWave(+v)}/>
            <label className="field"><span>Target cluster</span><select value={approvalClusterId} onChange={e=>setApprovalClusterId(+e.target.value)}><option value={0}>Select cluster</option>{clusters.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
            <Field label="Requested by" value={requestedBy} onChange={setRequestedBy}/>
            <Field label="Change ticket" value={changeTicket} onChange={setChangeTicket}/>
            <Field label="Decision actor" value={decidedBy} onChange={setDecidedBy}/>
          </div>
          <button className="button primary" disabled={busy||!rows.length||!clusters.length} onClick={requestApproval}><UserCheck size={16}/> Request approval</button>
        </div>

        <div className="approvalList">
          {!approvals.length && <p className="muted">No migration approval requests yet.</p>}
          {approvals.map(a=><div className="approvalCard" key={a.id}>
            <div className="approvalMeta">
              <strong>Wave {a.wave_number} · Approval #{a.id}</strong>
              <span>{a.change_ticket||'No change ticket'} · requested by {a.requested_by}</span>
            </div>
            <div className={`approvalStatus ${a.status.toLowerCase()}`}>{a.status}</div>
            {a.status==='Pending' && <div className="approvalActions">
              <button className="iconButton approve" title="Approve" onClick={()=>decide(a.id,'Approved')}><CheckCircle2 size={16}/></button>
              <button className="iconButton reject" title="Reject" onClick={()=>decide(a.id,'Rejected')}><XCircle size={16}/></button>
            </div>}
          </div>)}
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
function Field({label,value,onChange,type='text',step}:{label:string,value:any,onChange:(v:string)=>void,type?:string,step?:string}){return <label className="field"><span>{label}</span><input type={type} step={step} value={value} onChange={e=>onChange(e.target.value)}/></label>}
