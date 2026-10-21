// @vitest-environment jsdom
import {render, screen, fireEvent, cleanup} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {PipelineView} from './PipelineView';
import type {PipelineRun} from '../types';

afterEach(cleanup);
const callbacks=()=>({onClean:vi.fn(),onAttack:vi.fn(),onRescue:vi.fn(),onInduction:vi.fn(),onReset:vi.fn()});
describe('pipeline interaction',()=>{
  it('runs rescue and induction without prerequisites in the UI',()=>{
    const actions=callbacks();
    render(<PipelineView view="CAUSAL ANALYSIS" busy="" error="" {...actions}/>);
    fireEvent.click(screen.getByText('Run Clean-Message Rescue'));
    fireEvent.click(screen.getByText('Run Attacked-Message Induction'));
    expect(actions.onRescue).toHaveBeenCalledOnce();
    expect(actions.onInduction).toHaveBeenCalledOnce();
  });
  it('shows boolean attack values and all evidence layers',()=>{
    const run={provenance_type:'TEST FIXTURE',attack_delta:{path:'risk_flag',clean:true,attacked:false},
      raw_fhir_mcp_data:[],clean_evidence:{risk_flag:true},attacked_evidence:{risk_flag:false},
      sender:{},mediator:{sha256:'test'},receiver:{decision:'DO_NOT_ESCALATE',score:-1,raw_output:'B'}} as unknown as PipelineRun;
    render(<PipelineView view="ATTACK LAB" attack={run} busy="" error="" {...callbacks()}/>);
    expect(screen.getByText('true')).toBeTruthy();
    expect(screen.getByText('false')).toBeTruthy();
    expect(screen.getByText('1. Unchanged raw FHIR resources')).toBeTruthy();
    expect(screen.getByText('3. Attacked evidence (risk_flag only)')).toBeTruthy();
  });
});
