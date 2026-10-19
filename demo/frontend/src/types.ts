export type Action = 'ESCALATE'|'DO_NOT_ESCALATE';
export type ExecutionMode = 'live_model_mcp'|'deterministic'|'replay';
export interface DemoCase {case_id:string;display_name:string;age:number;sex:string;presenting_complaint:string;symptom_duration:string;vitals:Record<string,unknown>;history:string[];medications:string[];allergies:string[];ecg:Record<string,unknown>;labs:Record<string,unknown>;additional_assessments:Record<string,unknown>;timeline:string[];available_tools:string[];expected_action:Action;primary_attack_target:string;dataset_origin:string;notes:string}
export interface PipelineRun {run_id:string;case_id:string;condition:string;provenance_type:string;tools:unknown[];attack_delta?:{path:string;clean:string;attacked:string};sender:Record<string,unknown>;mediator:{raw:string;parsed:Record<string,unknown>;sha256:string};receiver:{decision:Action;score:number;raw_output:string};expected_action:Action;correct:boolean;runtime_seconds:number}
export interface EvidenceCard {title:string;status:string;provenance_type:string;artifact:string;details:Record<string,unknown>}
export interface StatusRow {capability:string;status:string}
export interface ReplayBundle {case_id:string;provenance_type:string;clean:PipelineRun;attacked:PipelineRun;rescue:Record<string,unknown>;content_sha256:string}
