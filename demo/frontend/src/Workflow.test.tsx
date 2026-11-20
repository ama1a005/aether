// @vitest-environment jsdom
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import App from './App';
import {api} from './api';

vi.mock('./api',()=>({api:{cases:vi.fn(),tools:vi.fn()}}));
vi.mock('./components/CaseWorkspace',()=>({CaseWorkspace:()=> <p>Source record</p>}));
afterEach(()=>{cleanup();vi.resetAllMocks()});

it('requires successful evidence retrieval before advancing and displays failures',async()=>{
 vi.mocked(api.cases).mockResolvedValue([{case_id:'DEMO-PAT-001',display_name:'Record 1'}] as any);
 vi.mocked(api.tools).mockRejectedValueOnce(new Error('Service unavailable')).mockResolvedValueOnce({source:'PTB-XL'});
 render(<App/>);
 await screen.findByText('Source record');
 fireEvent.click(screen.getByRole('button',{name:/Continue to retrieve evidence/}));
 const next=screen.getByRole('button',{name:/Continue to run the agents/}) as HTMLButtonElement;
 expect(next.disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Retrieve record evidence'}));
 expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('Service unavailable'));
 expect(next.disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Retrieve record evidence'}));
 await waitFor(()=>expect(next.disabled).toBe(false));
 expect(screen.queryByRole('alert')).toBeNull();
 expect(api.tools).toHaveBeenLastCalledWith('DEMO-PAT-001','mock_deterministic');
});
