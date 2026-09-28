export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function getWorkloads(){
  const r = await fetch(`${API}/api/v1/workloads`); if(!r.ok) throw new Error(await r.text()); return r.json()
}
export async function uploadInventory(file: File){
  const form = new FormData(); form.append('file', file)
  const r = await fetch(`${API}/api/v1/imports/rvtools`, {method:'POST', body:form}); if(!r.ok) throw new Error(await r.text()); return r.json()
}
export async function assess(){ const r=await fetch(`${API}/api/v1/assessments/run`,{method:'POST'}); if(!r.ok) throw new Error(await r.text()); return r.json() }
export async function planWaves(){ const r=await fetch(`${API}/api/v1/waves/plan`,{method:'POST'}); if(!r.ok) throw new Error(await r.text()); return r.json() }
