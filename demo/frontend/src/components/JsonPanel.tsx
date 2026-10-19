export function JsonPanel({title,value}:{title:string;value:unknown}){return <details className="json-panel"><summary>{title}</summary><pre>{JSON.stringify(value,null,2)}</pre></details>}
