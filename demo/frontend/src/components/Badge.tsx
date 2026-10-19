export function Badge({children,tone='blue'}:{children:React.ReactNode;tone?:'blue'|'green'|'amber'|'red'|'grey'}){return <span className={`badge ${tone}`}>{children}</span>}
