export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const KEY_STORAGE = 'migration-factory-api-key'

export function setSessionApiKey(value:string){
  if(value) sessionStorage.setItem(KEY_STORAGE, value)
  else sessionStorage.removeItem(KEY_STORAGE)
}

export function hasSessionApiKey(){
  return Boolean(sessionStorage.getItem(KEY_STORAGE))
}

async function apiFetch(path:string, init:RequestInit = {}){
  const headers = new Headers(init.headers || {})
  const apiKey = sessionStorage.getItem(KEY_STORAGE)
  if(apiKey) headers.set('X-API-Key', apiKey)
  return fetch(`${API}${path}`, {...init, headers})
}

async function jsonOrThrow(r: Response){
  if(!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function getWorkloads(){
  return jsonOrThrow(await apiFetch('/api/v1/workloads'))
}

export async function uploadInventory(file: File){
  const form = new FormData()
  form.append('file', file)
  return jsonOrThrow(await apiFetch('/api/v1/imports/rvtools', {method:'POST', body:form}))
}

export async function assess(){
  return jsonOrThrow(await apiFetch('/api/v1/assessments/run',{method:'POST'}))
}

export async function planWaves(){
  return jsonOrThrow(await apiFetch('/api/v1/waves/plan',{method:'POST'}))
}

export async function applyNetworkMapping(rules: {source:string; target:string}[]){
  return jsonOrThrow(await apiFetch('/api/v1/planning/network-map', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({rules}),
  }))
}

export async function getReadiness(){
  return jsonOrThrow(await apiFetch('/api/v1/planning/readiness'))
}

export async function getRunbook(wave:number){
  return jsonOrThrow(await apiFetch(`/api/v1/planning/waves/${wave}/runbook`))
}

export async function getTargetClusters(){
  return jsonOrThrow(await apiFetch('/api/v1/capacity/clusters'))
}

export async function createTargetCluster(payload:any){
  return jsonOrThrow(await apiFetch('/api/v1/capacity/clusters', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function evaluateWaveCapacity(wave:number, headroom=20){
  return jsonOrThrow(await apiFetch(`/api/v1/capacity/waves/${wave}/evaluate?headroom_percent=${headroom}`))
}

export async function reconcilePrismClusters(){
  return jsonOrThrow(await apiFetch('/api/v1/capacity/prism-reconcile'))
}

export async function getApprovals(){
  return jsonOrThrow(await apiFetch('/api/v1/approvals'))
}

export async function requestWaveApproval(wave:number, payload:any){
  return jsonOrThrow(await apiFetch(`/api/v1/approvals/waves/${wave}/request`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function decideApproval(id:number, payload:any){
  return jsonOrThrow(await apiFetch(`/api/v1/approvals/${id}/decision`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function updateTargetCluster(id:number, payload:any){
  return jsonOrThrow(await apiFetch(`/api/v1/capacity/clusters/${id}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function deleteTargetCluster(id:number){
  return jsonOrThrow(await apiFetch(`/api/v1/capacity/clusters/${id}`, {
    method:'DELETE',
  }))
}

export async function getDependencies(){
  return jsonOrThrow(await apiFetch('/api/v1/dependencies'))
}

export async function createDependency(payload:any){
  return jsonOrThrow(await apiFetch('/api/v1/dependencies', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),
  }))
}

export async function getDependencyGraph(){
  return jsonOrThrow(await apiFetch('/api/v1/dependencies/graph'))
}

export async function optimizeWaves(params?:{
  max_vms?:number; max_vcpu?:number; max_memory_gb?:number;
  max_storage_gb?:number; strategy?:'pilot_first'|'risk_first';
}){
  const q = new URLSearchParams()
  q.set('max_vms', String(params?.max_vms ?? 20))
  q.set('max_vcpu', String(params?.max_vcpu ?? 160))
  q.set('max_memory_gb', String(params?.max_memory_gb ?? 512))
  q.set('max_storage_gb', String(params?.max_storage_gb ?? 5000))
  q.set('strategy', params?.strategy ?? 'pilot_first')
  return jsonOrThrow(await apiFetch(`/api/v1/optimizer/waves?${q.toString()}`, {method:'POST'}))
}

export async function downloadAuthenticated(path:string, filename:string){
  const response = await apiFetch(path)
  if(!response.ok) throw new Error(await response.text())
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
