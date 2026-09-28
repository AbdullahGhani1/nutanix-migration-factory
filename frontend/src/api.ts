export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function jsonOrThrow(r: Response){
  if(!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function getWorkloads(){
  return jsonOrThrow(await fetch(`${API}/api/v1/workloads`))
}

export async function uploadInventory(file: File){
  const form = new FormData()
  form.append('file', file)
  return jsonOrThrow(await fetch(`${API}/api/v1/imports/rvtools`, {method:'POST', body:form}))
}

export async function assess(){
  return jsonOrThrow(await fetch(`${API}/api/v1/assessments/run`,{method:'POST'}))
}

export async function planWaves(){
  return jsonOrThrow(await fetch(`${API}/api/v1/waves/plan`,{method:'POST'}))
}

export async function applyNetworkMapping(rules: {source:string; target:string}[]){
  return jsonOrThrow(await fetch(`${API}/api/v1/planning/network-map`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({rules}),
  }))
}

export async function getReadiness(){
  return jsonOrThrow(await fetch(`${API}/api/v1/planning/readiness`))
}

export async function getRunbook(wave:number){
  return jsonOrThrow(await fetch(`${API}/api/v1/planning/waves/${wave}/runbook`))
}

export async function getTargetClusters(){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/clusters`))
}

export async function createTargetCluster(payload:any){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/clusters`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function evaluateWaveCapacity(wave:number, headroom=20){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/waves/${wave}/evaluate?headroom_percent=${headroom}`))
}

export async function reconcilePrismClusters(){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/prism-reconcile`))
}


export async function getApprovals(){
  return jsonOrThrow(await fetch(`${API}/api/v1/approvals`))
}

export async function requestWaveApproval(wave:number, payload:any){
  return jsonOrThrow(await fetch(`${API}/api/v1/approvals/waves/${wave}/request`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function decideApproval(id:number, payload:any){
  return jsonOrThrow(await fetch(`${API}/api/v1/approvals/${id}/decision`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}


export async function updateTargetCluster(id:number, payload:any){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/clusters/${id}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function deleteTargetCluster(id:number){
  return jsonOrThrow(await fetch(`${API}/api/v1/capacity/clusters/${id}`, {
    method:'DELETE',
  }))
}
