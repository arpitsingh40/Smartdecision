import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  Loader2, Lock, Zap, Activity, Clock, CheckCircle2,
  XCircle, Play, Inbox, ThumbsUp, ThumbsDown, BarChart3,
  Target, Shield, History, Wifi, Plus, ArrowRight, Gauge,
} from 'lucide-react';

// Business OS tab definitions
const TABS = [
  { id: 'ops', label: 'Ops', icon: Zap },
  { id: 'cockpit', label: 'Cockpit', icon: Gauge },
  { id: 'records', label: 'Records', icon: History },
  { id: 'tools', label: 'Tools', icon: Wifi },
];

// Labels for scheduled process runs
const processScheduleLabels = {
  morning_brief: '8 AM', midday_followup: '2 PM', evening_wrap: '7 PM',
  weekly_strategy: 'Monday', weekly_people: 'Friday',
  pipeline_health: 'Every 4h', tech_health: 'Every 6h',
};

// Business OS dashboard with tabbed views
export default function BusinessOSPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [tab, setTab] = useState('ops');
  const [data, setData] = useState(null);
  const [processes, setProcesses] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [running, setRunning] = useState(false);

  // Cockpit tab data
  const [cockpit, setCockpit] = useState(null);
  const [cockpitLoading, setCockpitLoading] = useState(false);

  // Records tab data
  const [records, setRecords] = useState(null);
  const [recordsLoading, setRecordsLoading] = useState(false);

  // Tools tab data
  const [tools, setTools] = useState(null);
  const [toolsLoading, setToolsLoading] = useState(false);

  // Fetch status, processes, and approvals
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [statusR, procR, approvalR] = await Promise.all([
        api.get('/business-os/status'),
        api.get('/business-os/processes'),
        api.get('/business-os/approvals'),
      ]);
      setData(statusR.data);
      setProcesses(procR.data);
      setApprovals(approvalR.data);
    } catch (e) {
      if (e?.response?.status === 403 || e?.response?.status === 404) setDenied(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { const id = setInterval(load, 30000); return () => clearInterval(id); }, [load]);

  // Lazy load tab content
  useEffect(() => {
    if (tab === 'cockpit' && !cockpit && !cockpitLoading) {
      setCockpitLoading(true);
      Promise.all([
        api.get('/org/cockpit'),
        api.get('/org'),
      ]).then(([cR, oR]) => setCockpit({ cockpit: cR.data, org: oR.data }))
        .catch(() => {})
        .finally(() => setCockpitLoading(false));
    }
    if (tab === 'records' && !records && !recordsLoading) {
      setRecordsLoading(true);
      Promise.all([
        api.get('/audit', { params: { limit: 30 } }),
        api.get('/audit/summary', { params: { hours: 24 } }),
      ]).then(([eR, sR]) => setRecords({ events: eR.data?.events || [], summary: sR.data }))
        .catch(() => {})
        .finally(() => setRecordsLoading(false));
    }
    if (tab === 'tools' && !tools && !toolsLoading) {
      setToolsLoading(true);
      api.get('/execution/connections')
        .then(r => {
          const conns = r.data?.connected_list || [];
          const avail = r.data?.top_available || [];
          setTools({ connected: conns, available: avail });
        })
        .catch(() => {})
        .finally(() => setToolsLoading(false));
    }
  }, [tab, cockpit, records, tools, cockpitLoading, recordsLoading, toolsLoading]);

  // Trigger a full business OS cycle
  const runCycle = async () => { setRunning(true); try { await api.post('/business-os/run'); await load(); } catch (_) {} finally { setRunning(false); } };
  // Approve or deny a pending approval
  const handleApproval = async (id, action) => {
    try { await api.post(`/business-os/approvals/${id}`, { action }); toast.success(action === 'approve' ? 'Approved' : 'Denied'); await load(); } catch (_) {}
  };
  // Start OAuth flow for a toolkit
  const connectTool = async (toolkit) => {
    try {
      const r = await api.post('/execution/connections/connect', { toolkit, redirect_uri: window.location.origin + '/app/business-os' });
      if (r.data?.auth_url) window.open(r.data.auth_url, '_blank');
      setTimeout(async () => { setTools(null); setToolsLoading(false); }, 5000);
    } catch (_) {}
  };

  if (loading && !data) {
    return (
      <div className="min-h-screen"><TopBar title="Business OS" backTo="/app" />
        <div className="max-w-5xl mx-auto px-4 py-10 space-y-4">
          <div className="h-8 w-48 animate-pulse rounded-md bg-surface-2" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-20 rounded-2xl animate-pulse bg-surface-2" />)}
          </div>
        </div>
      </div>);
  }
  if (denied) {
    return (
      <div className="min-h-screen"><TopBar title="Business OS" backTo="/app" />
        <div data-testid="business-os-denied" className="max-w-md mx-auto text-center py-24 px-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl border mb-4 text-muted"><Lock size={20} /></div>
          <h2 className="font-display text-xl">Workspace required</h2>
          <p className="text-sm text-muted mt-2">Business OS requires a workspace. Create one first.</p>
          <Button variant="secondary" className="rounded-xl mt-6" onClick={() => navigate('/app/team')}>Go to workspace</Button>
        </div>
      </div>);
  }

  const agents = data?.agents || {};
  const agentTypes = Object.keys(agents);
  const activeAgents = agentTypes.filter(t => agents[t]?.status === 'active').length;
  const totalDecisions = agentTypes.reduce((s, t) => s + (agents[t]?.decisions || 0), 0);
  const totalActions = agentTypes.reduce((s, t) => s + (agents[t]?.actions || 0), 0);
  const connectedTools = data?.connected_tools || [];
  const recentRuns = data?.recent_runs || [];
  const taskCounts = data?.tasks || {};
  const processList = processes?.processes || {};

  return (
    <div className="min-h-screen">
      <TopBar title="Business OS" backTo="/app" />
      <main data-testid="business-os-page" className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="font-display text-2xl">Business OS</h1>
            <p className="text-sm text-muted mt-1">Your company runs here. Agents, strategy, records, tools.</p>
          </div>
          <Button data-testid="business-os-run-cycle" className="rounded-xl" onClick={runCycle} disabled={running} size="sm">
            {running ? <Loader2 size={14} className="animate-spin mr-2" /> : <Play size={14} className="mr-2" />}
            Run cycle
          </Button>
        </div>

        {/* Tabs */}
        <div className="inline-flex items-center rounded-xl border border-hairline bg-surface p-0.5">
          {TABS.map(t => (
            <button key={t.id} data-testid={`bos-tab-${t.id}`} onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${tab === t.id ? 'bg-text text-background shadow-sm' : 'text-muted hover:text-text'}`}>
              <t.icon size={13} strokeWidth={1.75} /> {t.label}
            </button>
          ))}
        </div>

        {/* ============ OPS TAB ============ */}
        {tab === 'ops' && (
          <div className="space-y-6">
            {/* Tool status */}
            <div className={`rounded-2xl border px-5 py-3.5 ${connectedTools.length > 0 ? 'border-accent/20 bg-accent/[0.03]' : 'border-amber-200 bg-amber-50/50'}`}>
              <div className="flex items-center gap-2">
                {connectedTools.length > 0 ? (
                  <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" /></span>
                ) : <Wifi size={14} className="text-amber-600" />}
                <span className="text-sm font-medium">{connectedTools.length > 0 ? `${connectedTools.length} tools connected` : 'No tools connected'}</span>
                {connectedTools.length === 0 && <Button variant="secondary" size="sm" className="rounded-lg ml-auto text-xs" onClick={() => setTab('tools')}>Connect tools <ArrowRight size={12} className="ml-1" /></Button>}
              </div>
              {connectedTools.length > 0 && <div className="flex flex-wrap gap-1.5 mt-2">{connectedTools.map(t => <span key={t} className="text-[11px] px-2 py-0.5 rounded-full bg-surface border text-muted">{t}</span>)}</div>}
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Agents', value: `${activeAgents}/${agentTypes.length}`, sub: 'active' },
                { label: 'Decisions', value: totalDecisions, sub: 'autonomous' },
                { label: 'Actions', value: totalActions, sub: 'through tools' },
                { label: 'Learning', value: data?.learning?.total_learning_events || 0, sub: 'patterns learned' },
              ].map(s => (
                <div key={s.label} className="rounded-2xl border border-hairline bg-surface p-4">
                  <p className="text-[11px] text-muted uppercase tracking-wide">{s.label}</p>
                  <p className="font-display text-2xl mt-1">{s.value}</p>
                  <p className="text-[11px] text-muted mt-0.5">{s.sub}</p>
                </div>
              ))}
            </div>

            {/* Pending approvals */}
            {approvals?.pending?.length > 0 && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5">
                <div className="flex items-center gap-2 mb-3"><Inbox size={15} className="text-amber-600" /><h2 className="text-sm font-medium">Pending ({approvals.pending.length})</h2></div>
                <div className="space-y-2">
                  {approvals.pending.slice(0, 3).map(item => (
                    <div key={item.id} className="flex items-start justify-between gap-3 rounded-xl border bg-surface px-4 py-3">
                      <div className="min-w-0">
                        <span className="text-xs font-medium capitalize">{item.from_role || item.from_agent}</span>
                        <p className="text-sm mt-0.5">{item.summary}</p>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Button size="sm" className="rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs" onClick={() => handleApproval(item.id, 'approve')}><ThumbsUp size={12} className="mr-1"/>Approve</Button>
                        <Button size="sm" variant="ghost" className="rounded-lg text-xs text-red-600" onClick={() => handleApproval(item.id, 'deny')}><ThumbsDown size={12}/></Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Agents */}
            <div>
              <div className="flex items-center gap-2 mb-3"><Activity size={14} strokeWidth={1.75} /><h2 className="text-sm font-medium">Agents</h2></div>
              <div className="rounded-2xl border border-hairline divide-y">
                {agentTypes.map(t => {
                  const a = agents[t];
                  return (
                    <div key={t} className="flex items-center justify-between px-4 py-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{a?.role || t}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${a?.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-500'}`}>{a?.status || 'inactive'}</span>
                        </div>
                        <p className="text-[11px] text-muted mt-0.5">{a?.decisions || 0} decisions · {a?.actions || 0} actions · {a?.schedule || 'daily'}</p>
                      </div>
                      {a?.status === 'active' && <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Recent runs */}
            {recentRuns.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3"><Clock size={14} /><h2 className="text-sm font-medium">Recent Activity</h2></div>
                <div className="rounded-2xl border border-hairline divide-y">
                  {recentRuns.slice(0, 5).map(run => (
                    <div key={run.id} className="flex items-center justify-between px-4 py-2.5">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <CheckCircle2 size={13} className="text-accent shrink-0" />
                        <span className="text-sm truncate">{run.label || run.process_id || 'Cycle'}</span>
                      </div>
                      <span className="text-[11px] text-muted shrink-0 ml-3">{run.elapsed_s}s</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============ COCKPIT TAB ============ */}
        {tab === 'cockpit' && (
          <div className="space-y-6">
            {cockpitLoading ? (
              <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-20 rounded-2xl animate-pulse bg-surface-2" />)}</div>
            ) : cockpit ? (
              <>
                {/* North Star */}
                {cockpit.org?.north_star && (
                  <div className="rounded-2xl border border-hairline bg-surface p-5">
                    <div className="flex items-center gap-2 mb-3"><Target size={15} className="text-accent" /><h2 className="text-sm font-medium">North Star</h2><span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-accent/5 text-accent">Private to you</span></div>
                    <p className="text-sm text-text leading-relaxed">{cockpit.org.north_star}</p>
                    {cockpit.org.target && <p className="text-xs text-muted mt-2">Target: {cockpit.org.target} · Deadline: {cockpit.org.deadline || 'Not set'}</p>}
                    {cockpit.cockpit?.avg_alignment != null && (
                      <div className="mt-3 flex items-center gap-2">
                        <div className="flex-1 h-2 rounded-full bg-surface-2 overflow-hidden">
                          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${cockpit.cockpit.avg_alignment}%` }} />
                        </div>
                        <span className="text-xs font-medium text-accent">{cockpit.cockpit.avg_alignment}% aligned</span>
                      </div>
                    )}
                  </div>
                )}
                {/* Key stats */}
                {cockpit.cockpit && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: 'Decisions', value: cockpit.cockpit.total_decisions || 0 },
                      { label: 'Alignment', value: `${cockpit.cockpit.avg_alignment || 0}%` },
                      { label: 'Follow-through', value: `${cockpit.cockpit.follow_through_pct || 0}%` },
                      { label: 'Team', value: cockpit.cockpit.member_count || 0 },
                    ].map(s => (
                      <div key={s.label} className="rounded-2xl border border-hairline bg-surface p-4 text-center">
                        <p className="font-display text-2xl">{s.value}</p>
                        <p className="text-[11px] text-muted mt-1">{s.label}</p>
                      </div>
                    ))}
                  </div>
                )}
                {/* Per-member table */}
                {cockpit.cockpit?.per_member?.length > 0 && (
                  <div>
                    <h2 className="text-sm font-medium mb-3">Team</h2>
                    <div className="rounded-2xl border border-hairline divide-y">
                      {cockpit.cockpit.per_member.map(m => (
                        <div key={m.name} className="flex items-center justify-between px-4 py-3">
                          <span className="text-sm">{m.name}</span>
                          <div className="flex items-center gap-4 text-xs text-muted">
                            <span>{m.decisions || 0} decisions</span>
                            <span className="font-medium text-accent">{m.avg_alignment != null ? `${m.avg_alignment}%` : '—'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-16 px-6">
                <Target size={28} className="mx-auto mb-3 text-muted/40" />
                <p className="text-sm font-medium text-text">Set your North Star</p>
                <p className="text-xs text-muted mt-1.5 max-w-xs mx-auto">Define direction once. All agents align to it automatically.</p>
                <Button size="sm" className="rounded-lg mt-4" onClick={() => navigate('/app/team')}>Set North Star →</Button>
              </div>
            )}
          </div>
        )}

        {/* ============ RECORDS TAB ============ */}
        {tab === 'records' && (
          <div className="space-y-4">
            {recordsLoading ? (
              <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 rounded-xl animate-pulse bg-surface-2" />)}</div>
            ) : records ? (
              <>
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-muted">Last 24h: <span className="font-medium text-text">{records.summary?.total || 0} events</span></span>
                  {records.summary?.by_severity?.error > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-50 text-red-700">{records.summary.by_severity.error} errors</span>}
                </div>
                <div className="rounded-2xl border border-hairline divide-y">
                  {records.events.length === 0 ? (
                    <div className="py-12 text-center">
                      <History size={28} className="mx-auto mb-3 text-muted/40" />
                      <p className="text-sm font-medium text-text">Activity will appear here</p>
                      <p className="text-xs text-muted mt-1">Every decision, execution, and connection is logged automatically.</p>
                    </div>
                  ) : records.events.slice(0, 15).map(ev => {
                    const ts = ev.created_at ? new Date(ev.created_at).toLocaleString() : '';
                    return (
                      <div key={ev.id} className="flex items-start gap-3 px-4 py-3">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full border shrink-0 mt-0.5 ${ev.severity === 'error' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-slate-50 text-muted'}`}>{ev.event_type}</span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm">{ev.summary}</p>
                          <p className="text-[10px] text-muted mt-0.5">{ts}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : <div className="text-center py-16 text-sm text-muted">No records data available.</div>}
          </div>
        )}

        {/* ============ TOOLS TAB ============ */}
        {tab === 'tools' && (
          <div className="space-y-6">
            {toolsLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse bg-surface-2" />)}</div>
            ) : tools ? (
              <>
                {tools.connected?.length > 0 && (
                  <div>
                    <h2 className="text-sm font-medium mb-3 flex items-center gap-2"><Wifi size={14} className="text-emerald-600" /> Connected ({tools.connected.length})</h2>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {tools.connected.map(t => (
                        <div key={t.toolkit} className="rounded-2xl border border-emerald-200 bg-emerald-50/30 p-4 text-center">
                          <CheckCircle2 size={16} className="text-emerald-600 mx-auto mb-2" />
                          <p className="text-sm font-medium capitalize">{t.name || t.toolkit}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {tools.available?.length > 0 && (
                  <div>
                    <h2 className="text-sm font-medium mb-3">Available</h2>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {tools.available.slice(0, 8).map(t => (
                        <div key={t.toolkit} className="rounded-2xl border border-hairline bg-surface p-4 flex flex-col items-center text-center gap-2">
                          <span className="text-sm font-medium capitalize">{t.name || t.toolkit}</span>
                          <p className="text-[11px] text-muted">{t.tool_count || 0} tools</p>
                          <Button size="sm" variant="secondary" className="rounded-lg text-xs w-full" onClick={() => connectTool(t.toolkit)}>Connect</Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : <div className="text-center py-16 text-sm text-muted">No integrations — check your Composio connection.</div>}
          </div>
        )}

      </main>
    </div>
  );
}
