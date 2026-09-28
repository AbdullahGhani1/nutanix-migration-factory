import { useEffect, useMemo, useState } from 'react'
import {
  Activity, CheckCircle2, ClipboardCheck, Database, FileText, FileUp, Gauge, GitBranch, Layers3, Map,
  Server, ShieldAlert, UserCheck, Waypoints, XCircle
} from 'lucide-react'
import {
  applyNetworkMapping, assess, createDependency, createExecution, createTargetCluster, decideApproval, downloadAuthenticated, evaluateWaveCapacity,
  getApprovals, getDependencies, getDependencyGraph, getExecutions, getPrismEnvironmentSummary, getPrismNetworkReconciliation,
  getReadiness, getRunbook, getTargetClusters, getTechnicalValidations, getWorkloads, optimizeWaves, planWaves,
  reconcilePrismClusters, recordTechnicalValidation, requestWaveApproval, setSessionApiKey, testPrismConnection, transitionExecution, updateTargetCluster, uploadInventory
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

type Execution = {
  id:number; approval_id:number; wave_number:number; target_cluster_id:number; status:string;
  operator:string; move_plan_name:string; change_ticket:string; started_at:string|null;
  completed_at:string|null; cutover_duration_minutes:number|null; uat_status:string;
  rollback_executed:boolean; validation_summary:string; rollback_reason:string;
  evidence_reference:string; notes:string; created_at:string;
}

type TechnicalValidation = {
  id:number; execution_id:number; tool:string; status:string; actor:string;
  hosts_total:number; hosts_passed:number; hosts_failed:number;
  prism_validation:string; guest_validation:string; artifact_sha256:string;
  evidence_reference:string; summary:string; recorded_at:string;
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
  const [prismEnvironment,setPrismEnvironment]=useState<any|null>(null)
  const [prismNetwork,setPrismNetwork]=useState<any|null>(null)
  const [approvals,setApprovals]=useState<Approval[]>([])
  const [approvalWave,setApprovalWave]=useState(1)
  const [approvalClusterId,setApprovalClusterId]=useState(0)
  const [requestedBy,setRequestedBy]=useState('migration.engineer')
  const [changeTicket,setChangeTicket]=useState('CHG-2026-0042')
  const [decidedBy,setDecidedBy]=useState('change.manager')
  const [dependencies,setDependencies]=useState<any[]>([])
  const [dependencyGraph,setDependencyGraph]=useState<any|null>(null)
  const [optimizerResult,setOptimizerResult]=useState<any|null>(null)
  const [upstreamId,setUpstreamId]=useState(0)
  const [downstreamId,setDownstreamId]=useState(0)
  const [apiKey,setApiKey]=useState('')
  const [executions,setExecutions]=useState<Execution[]>([])
  const [executionApprovalId,setExecutionApprovalId]=useState(0)
  const [executionOperator,setExecutionOperator]=useState('migration.engineer')
  const [movePlanName,setMovePlanName]=useState('')
  const [cutoverMinutes,setCutoverMinutes]=useState(0)
  const [validationSummary,setValidationSummary]=useState('')
  const [rollbackReason,setRollbackReason]=useState('')
  const [evidenceReference,setEvidenceReference]=useState('')
  const [technicalValidations,setTechnicalValidations]=useState<TechnicalValidation[]>([])
  const [validationExecutionId,setValidationExecutionId]=useState(0)
  const [validationStatus,setValidationStatus]=useState('Passed')
  const [validationHostsTotal,setValidationHostsTotal]=useState(0)
  const [validationHostsPassed,setValidationHostsPassed]=useState(0)
  const [validationHostsFailed,setValidationHostsFailed]=useState(0)
  const [prismValidation,setPrismValidation]=useState('Passed')
  const [guestValidation,setGuestValidation]=useState('Passed')
  const [validationArtifactSha,setValidationArtifactSha]=useState('')
  const [technicalValidationSummary,setTechnicalValidationSummary]=useState('')

  const refresh=async()=>setRows(await getWorkloads())
  const refreshClusters=async()=>setClusters(await getTargetClusters())
  const refreshApprovals=async()=>setApprovals(await getApprovals())
  const refreshExecutions=async()=>setExecutions(await getExecutions())
  const refreshTechnicalValidations=async()=>setTechnicalValidations(await getTechnicalValidations())
  const refreshDependencies=async()=>{
    setDependencies(await getDependencies())
    setDependencyGraph(await getDependencyGraph())
  }
  useEffect(()=>{refresh().catch(()=>{});refreshClusters().catch(()=>{});refreshApprovals().catch(()=>{});refreshExecutions().catch(()=>{});refreshTechnicalValidations().catch(()=>{});refreshDependencies().catch(()=>{})},[])

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
      setReadiness(null); setRunbook(null); setCapacity(null); setDependencies([]); setDependencyGraph(null); setOptimizerResult(null)
      await act(()=>uploadInventory(f),`Imported ${f.name}`)
      await refreshApprovals().catch(()=>{})
      await refreshExecutions().catch(()=>{})
      await refreshTechnicalValidations().catch(()=>{})
      await refreshDependencies().catch(()=>{})
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

  const runOptimizer=async()=>{
    setBusy(true);setMessage('')
    try{
      const result=await optimizeWaves()
      setOptimizerResult(result)
      await refresh()
      setMessage(`Optimized ${result.waves.length} migration wave(s) using ${result.strategy}`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
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

  const discoverPrism=async()=>{
    setBusy(true);setMessage('')
    try{
      const [connection,environment,network]=await Promise.all([
        testPrismConnection(),
        getPrismEnvironmentSummary(),
        getPrismNetworkReconciliation(),
      ])
      setPrismEnvironment(environment)
      setPrismNetwork(network)
      setMessage(`Prism connected: ${environment.clusters} cluster(s), ${environment.vms} VM(s), ${environment.subnets} subnet(s); network mappings ${network.matched}/${network.targets} matched`)
    }catch(e:any){
      setPrismEnvironment(null)
      setPrismNetwork(null)
      setMessage(e.message)
    }finally{setBusy(false)}
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

  const addDependency=async()=>{
    if(!upstreamId||!downstreamId){setMessage('Select upstream and downstream workloads');return}
    setBusy(true);setMessage('')
    try{
      await createDependency({
        upstream_workload_id:upstreamId,
        downstream_workload_id:downstreamId,
        dependency_type:'service',
        notes:'Defined in Migration Factory dependency planner',
      })
      await refreshDependencies()
      setMessage('Workload dependency added')
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const connectApiKey=async()=>{
    setSessionApiKey(apiKey)
    setMessage(apiKey?'Session API key applied':'Session API key cleared')
    await Promise.all([
      refresh().catch(()=>{}),
      refreshClusters().catch(()=>{}),
      refreshApprovals().catch(()=>{}),
      refreshExecutions().catch(()=>{}),
      refreshTechnicalValidations().catch(()=>{}),
      refreshDependencies().catch(()=>{}),
    ])
  }

  const download=async(path:string,filename:string)=>{
    setBusy(true);setMessage('')
    try{await downloadAuthenticated(path,filename)}
    catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const createExecutionRecord=async()=>{
    if(!executionApprovalId){setMessage('Select an approved migration request');return}
    setBusy(true);setMessage('')
    try{
      await createExecution({
        approval_id:executionApprovalId,
        operator:executionOperator,
        move_plan_name:movePlanName,
        evidence_reference:evidenceReference,
        notes:'Execution record created from Migration Factory dashboard',
      })
      await refreshExecutions()
      setMessage(`Execution record created for approval #${executionApprovalId}`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const moveExecution=async(execution:Execution,action:'start'|'complete'|'rollback'|'fail')=>{
    setBusy(true);setMessage('')
    try{
      const payload:any={
        action,
        actor:executionOperator,
        evidence_reference:evidenceReference||undefined,
        notes:`${action} recorded from Migration Factory dashboard`,
      }
      if(action==='complete'){
        payload.cutover_duration_minutes=cutoverMinutes
        payload.uat_status='Passed'
        payload.validation_summary=validationSummary
      }
      if(action==='rollback'){
        payload.cutover_duration_minutes=cutoverMinutes||undefined
        payload.uat_status='Failed'
        payload.validation_summary=validationSummary
        payload.rollback_reason=rollbackReason
      }
      if(action==='fail'){
        payload.cutover_duration_minutes=cutoverMinutes||undefined
        payload.uat_status='Failed'
        payload.validation_summary=validationSummary
        payload.rollback_reason=rollbackReason
      }
      await transitionExecution(execution.id,payload)
      await refreshExecutions()
      setMessage(`Execution #${execution.id} moved to ${action}`)
    }catch(e:any){setMessage(e.message)}
    finally{setBusy(false)}
  }

  const recordValidationEvidence=async()=>{
    if(!validationExecutionId){setMessage('Select a started/completed migration execution');return}
    setBusy(true);setMessage('')
    try{
      await recordTechnicalValidation(validationExecutionId,{
        tool:'Ansible',
        status:validationStatus,
        actor:executionOperator,
        hosts_total:validationHostsTotal,
        hosts_passed:validationHostsPassed,
        hosts_failed:validationHostsFailed,
        prism_validation:prismValidation,
        guest_validation:guestValidation,
        artifact_sha256:validationArtifactSha,
        evidence_reference:evidenceReference,
        summary:technicalValidationSummary,
      })
      await refreshTechnicalValidations()
      setMessage(`Technical validation recorded for execution #${validationExecutionId}`)
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
      <div className="headerTools">
        <div className="badge"><Activity size={18}/> v0.9-dev</div>
        <div className="apiKeyBox">
          <input type="password" placeholder="Session API key (optional)" value={apiKey} onChange={e=>setApiKey(e.target.value)}/>
          <button className="button" onClick={connectApiKey}>Apply key</button>
        </div>
      </div>
    </header>

    <section className="actions">
      <label className="button primary"><FileUp size={17}/> Import RVTools <input type="file" accept=".csv,.xlsx,.xlsm" onChange={upload}/></label>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(assess,'Assessment complete')}><ShieldAlert size={17}/> Assess</button>
      <button className="button" disabled={busy||!rows.length} onClick={()=>act(planWaves,'Basic migration waves generated')}><Layers3 size={17}/> Basic plan</button>
      <button className="button primary" disabled={busy||!rows.length} onClick={runOptimizer}><Layers3 size={17}/> Optimize waves</button>
      <button className="button" disabled={busy||!rows.length} onClick={checkReadiness}><ClipboardCheck size={17}/> Readiness</button>
      <button className="button" disabled={busy} onClick={()=>download('/api/v1/reports/migration-plan.csv','migration-plan.csv')}><Database size={17}/> Export CSV</button>
      <button className="button" disabled={busy} onClick={()=>download('/api/v1/reports/implementation-report.pdf','nutanix-implementation-report.pdf')}><FileText size={17}/> Implementation PDF</button>
      <button className="button" disabled={busy} onClick={()=>download('/api/v1/reports/evidence-bundle.zip','nutanix-migration-evidence-bundle.zip')}><Database size={17}/> Evidence bundle</button>
      <button className="button" disabled={busy||!rows.length} onClick={()=>download('/api/v1/reports/terraform-pack.zip','nutanix-terraform-pack.zip')}><FileText size={17}/> Terraform pack</button>
      <button className="button" disabled={busy||!rows.length} onClick={()=>download('/api/v1/reports/ansible-validation-pack.zip','nutanix-ansible-validation-pack.zip')}><ClipboardCheck size={17}/> Ansible validation</button>
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

    {optimizerResult && <section className="panel optimizerPanel">
      <div className="panelHead">
        <div><h2><Layers3 size={18}/> Dependency-aware wave optimizer</h2><p>Strategy: {optimizerResult.strategy} · constraints: {optimizerResult.constraints.max_vms} VMs / {optimizerResult.constraints.max_vcpu} vCPU / {optimizerResult.constraints.max_memory_gb} GB RAM / {optimizerResult.constraints.max_storage_gb} GB storage per wave.</p></div>
      </div>
      <div className="waveCards">
        {optimizerResult.waves.map((w:any)=><div className="waveCard" key={w.wave}>
          <div className="waveCardTop"><strong>Wave {w.wave}</strong><span>{w.vms} VMs</span></div>
          <div className="waveNumbers"><span>{w.vcpu} vCPU</span><span>{w.memory_gb} GB RAM</span><span>{Math.round(w.storage_gb/1024*10)/10} TB</span></div>
          <p>{w.workload_names.join(', ')}</p>
          {w.warnings?.map((x:string,i:number)=><div className="waveWarning" key={i}>{x}</div>)}
        </div>)}
      </div>
    </section>}

    <section className="panel prismPanel">
      <div className="panelHead">
        <div><h2><Waypoints size={18}/> Live Prism Central discovery</h2><p>Read-only GA v4 inventory discovery for registered clusters, AHV VMs and subnets, plus reconciliation against planned target networks.</p></div>
        <button className="button primary" disabled={busy} onClick={discoverPrism}>Discover Prism</button>
      </div>
      <div className="prismDiscoveryBody">
        {prismEnvironment ? <>
          <div className="prismStats">
            <Mini label="Clusters" value={prismEnvironment.clusters} tone="ok"/>
            <Mini label="VMs" value={prismEnvironment.vms} tone="ok"/>
            <Mini label="Subnets" value={prismEnvironment.subnets} tone="ok"/>
            <Mini label="Mapped targets" value={prismNetwork?.matched||0} tone={(prismNetwork?.missing||prismNetwork?.ambiguous)?'warn':'ok'}/>
          </div>
          {(prismEnvironment.cluster_inventory_truncated||prismEnvironment.vm_inventory_truncated||prismEnvironment.subnet_inventory_truncated) &&
            <div className="waveWarning">Discovery hit the configured inventory cap. Increase max_items or scope the query before treating counts as complete.</div>}
          <div className="networkReconcileList">
            {prismNetwork?.results?.map((item:any)=><div className="networkReconcileRow" key={item.target_network}>
              <div><strong>{item.target_network}</strong><span>{item.matches?.[0]?.ext_id||'No unique Prism subnet extId'}</span></div>
              <span className={`networkStatus ${item.status.toLowerCase()}`}>{item.status}</span>
            </div>)}
            {prismNetwork?.targets===0 && <p className="muted">No planned AHV target networks exist yet. Apply network mappings first, then rediscover Prism.</p>}
          </div>
        </> : <p className="muted">Configure Prism Central credentials in the API environment, then run discovery. The connector is read-only.</p>}
      </div>
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

    <section className="panel dependencyPanel">
      <div className="panelHead">
        <div><h2><GitBranch size={18}/> Application dependency graph</h2><p>Define upstream → downstream dependencies so service start/stop order is generated deterministically.</p></div>
      </div>
      <div className="dependencyLayout">
        <div className="dependencyForm">
          <label className="field"><span>Upstream workload</span><select value={upstreamId} onChange={e=>setUpstreamId(+e.target.value)}><option value={0}>Select workload</option>{rows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
          <label className="field"><span>Downstream workload</span><select value={downstreamId} onChange={e=>setDownstreamId(+e.target.value)}><option value={0}>Select workload</option>{rows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
          <button className="button primary" disabled={busy||!rows.length} onClick={addDependency}>Add dependency</button>
        </div>
        <div className="dependencySummary">
          <div className="readinessGrid">
            <Mini label="Edges" value={dependencies.length} tone="ok"/>
            <Mini label="Nodes" value={dependencyGraph?.nodes?.length||0} tone="ok"/>
            <Mini label="Cycle" value={dependencyGraph?.has_cycle?1:0} tone={dependencyGraph?.has_cycle?'bad':'ok'}/>
          </div>
          {dependencies.slice(0,8).map(d=>{
            const up=rows.find(w=>w.id===d.upstream_workload_id)?.name||d.upstream_workload_id
            const down=rows.find(w=>w.id===d.downstream_workload_id)?.name||d.downstream_workload_id
            return <div className="dependencyEdge" key={d.id}><strong>{up}</strong><span>→</span><strong>{down}</strong></div>
          })}
          {!dependencies.length&&<p className="muted">No dependencies recorded. Example: database → application → web tier.</p>}
        </div>
      </div>
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
            {a.status==='Approved' && <div className="approvalActions">
              <button className="button" disabled={busy} onClick={()=>download(`/api/v1/reports/approvals/${a.id}/cab-package.zip`,`nutanix-cab-${a.change_ticket||`approval-${a.id}`}-wave-${a.wave_number}.zip`)}><FileText size={15}/> CAB package</button>
            </div>}
          </div>)}
        </div>
      </div>
    </section>

    <section className="panel executionPanel">
      <div className="panelHead">
        <div><h2><Activity size={18}/> Migration execution evidence</h2><p>Record an approved Nutanix Move cutover as it happens. Values are operator-entered evidence, not automatically verified claims.</p></div>
      </div>
      <div className="executionLayout">
        <div className="executionForm">
          <label className="field"><span>Approved request</span><select value={executionApprovalId} onChange={e=>setExecutionApprovalId(+e.target.value)}><option value={0}>Select approved request</option>{approvals.filter(a=>a.status==='Approved'&&!executions.some(x=>x.approval_id===a.id)).map(a=><option key={a.id} value={a.id}>Wave {a.wave_number} · Approval #{a.id} · {a.change_ticket||'No ticket'}</option>)}</select></label>
          <Field label="Operator" value={executionOperator} onChange={setExecutionOperator}/>
          <Field label="Nutanix Move plan name" value={movePlanName} onChange={setMovePlanName}/>
          <Field label="Evidence reference" value={evidenceReference} onChange={setEvidenceReference}/>
          <button className="button primary" disabled={busy||!executionApprovalId} onClick={createExecutionRecord}>Create execution record</button>
        </div>
        <div className="executionEvidenceForm">
          <Field label="Measured cutover minutes" type="number" value={cutoverMinutes} onChange={(v:any)=>setCutoverMinutes(+v)}/>
          <label className="field"><span>Validation / UAT summary</span><textarea value={validationSummary} onChange={e=>setValidationSummary(e.target.value)} placeholder="Record actual guest, network, DNS and application validation evidence."/></label>
          <label className="field"><span>Rollback reason</span><textarea value={rollbackReason} onChange={e=>setRollbackReason(e.target.value)} placeholder="Required only when rollback is executed."/></label>
        </div>
      </div>
      <div className="executionList">
        {!executions.length&&<p className="muted">No execution evidence exists yet. An execution can only be created from an approved migration request.</p>}
        {executions.map(x=><div className="executionCard" key={x.id}>
          <div className="executionMeta">
            <strong>Execution #{x.id} · Wave {x.wave_number}</strong>
            <span>{x.change_ticket||'No change ticket'} · {x.move_plan_name||'Move plan not named'} · operator {x.operator}</span>
            {x.cutover_duration_minutes!==null&&<span>Measured cutover: {x.cutover_duration_minutes} min · UAT: {x.uat_status}</span>}
            {x.validation_summary&&<span>{x.validation_summary}</span>}
          </div>
          <div className={`executionStatus ${x.status.toLowerCase()}`}>{x.status}</div>
          <div className="executionActions">
            {x.status==='Planned'&&<button className="button primary" onClick={()=>moveExecution(x,'start')}>Start</button>}
            {x.status==='InProgress'&&<>
              <button className="button primary" onClick={()=>moveExecution(x,'complete')}>Complete</button>
              <button className="button" onClick={()=>moveExecution(x,'rollback')}>Rollback</button>
              <button className="button" onClick={()=>moveExecution(x,'fail')}>Fail</button>
            </>}
          </div>
        </div>)}
      </div>
    </section>

    <section className="panel validationPanel">
      <div className="panelHead">
        <div><h2><ClipboardCheck size={18}/> Technical validation evidence</h2><p>Record actual Ansible/Prism post-migration results. This is infrastructure evidence, not application-owner UAT.</p></div>
      </div>
      <div className="validationEvidenceLayout">
        <div className="validationEvidenceForm">
          <label className="field"><span>Migration execution</span><select value={validationExecutionId} onChange={e=>setValidationExecutionId(+e.target.value)}><option value={0}>Select execution</option>{executions.filter(x=>x.status!=='Planned').map(x=><option key={x.id} value={x.id}>Execution #{x.id} · Wave {x.wave_number} · {x.status}</option>)}</select></label>
          <label className="field"><span>Validation status</span><select value={validationStatus} onChange={e=>setValidationStatus(e.target.value)}><option>Passed</option><option>Partial</option><option>Failed</option></select></label>
          <label className="field"><span>Prism validation</span><select value={prismValidation} onChange={e=>setPrismValidation(e.target.value)}><option>Passed</option><option>Partial</option><option>Failed</option><option>NotRun</option></select></label>
          <label className="field"><span>Guest validation</span><select value={guestValidation} onChange={e=>setGuestValidation(e.target.value)}><option>Passed</option><option>Partial</option><option>Failed</option><option>NotRun</option></select></label>
          <Field label="Hosts total" type="number" value={validationHostsTotal} onChange={(v:any)=>setValidationHostsTotal(+v)}/>
          <Field label="Hosts passed" type="number" value={validationHostsPassed} onChange={(v:any)=>setValidationHostsPassed(+v)}/>
          <Field label="Hosts failed" type="number" value={validationHostsFailed} onChange={(v:any)=>setValidationHostsFailed(+v)}/>
          <Field label="Artifact SHA-256 (optional)" value={validationArtifactSha} onChange={setValidationArtifactSha}/>
          <label className="field validationSummaryField"><span>Technical summary</span><textarea value={technicalValidationSummary} onChange={e=>setTechnicalValidationSummary(e.target.value)} placeholder="Record actual Prism, Linux/Windows guest and infrastructure validation results."/></label>
          <button className="button primary" disabled={busy||!validationExecutionId} onClick={recordValidationEvidence}>Record technical validation</button>
        </div>
        <div className="validationEvidenceList">
          {!technicalValidations.length&&<p className="muted">No technical validation evidence recorded.</p>}
          {technicalValidations.map(v=><div className="validationEvidenceCard" key={v.id}>
            <div>
              <strong>Execution #{v.execution_id} · {v.tool}</strong>
              <span>{v.hosts_passed}/{v.hosts_total} hosts passed · {v.hosts_failed} failed · Prism {v.prism_validation} · Guest {v.guest_validation}</span>
              {v.summary&&<span>{v.summary}</span>}
              {v.artifact_sha256&&<span>Artifact SHA-256: {v.artifact_sha256.slice(0,16)}…</span>}
            </div>
            <div className={`validationStatus ${v.status.toLowerCase()}`}>{v.status}</div>
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
      <div className="sequenceStrip">
        <div><span>Service start order</span><strong>{runbook.service_start_order?.join(' → ')||'Not defined'}</strong></div>
        <div><span>Service stop order</span><strong>{runbook.service_stop_order?.join(' → ')||'Not defined'}</strong></div>
      </div>
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
