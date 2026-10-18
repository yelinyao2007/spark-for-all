export interface Quiz { kind:string; question:string; options:string[] }
export interface Topic { topic:string; understanding:string; strategy:string; attempts:number; completed_quizzes:number; correct_checks:number; self_reported:boolean; quiz:Quiz|null }
export interface State { grade:number; current_topic:string|null; topics:Record<string,Topic>; interactions:number }
export interface Source { id:string; title:string; url:string; snippet:string; retrieved_at:string }
export interface Reply { explanation:string; state:State; sources:Source[]; warnings:string[]; visual:string; mode:string }
export async function api<T>(path:string,method='GET',body?:unknown):Promise<T> {
  const response = await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(200000)})
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'暂时无法完成，请稍后再试。')
  return data
}
