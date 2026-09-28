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
