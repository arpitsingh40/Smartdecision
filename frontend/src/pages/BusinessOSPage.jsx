import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  Loader2, Lock, Zap, Activity, Clock, CheckCircle2,
  XCircle, AlertTriangle, Play, RefreshCw, Wrench,
  BarChart3, ArrowRight, ThumbsUp, ThumbsDown, Inbox, Shield
} from 'lucide-react';

const processScheduleLabels = {
  morning_brief: '8 AM daily',
  midday_followup: '2 PM daily',
  evening_wrap: '7 PM daily',
  weekly_strategy: 'Monday',
  weekly_people: 'Friday',
  pipeline_health: 'Every 4 hours',
  tech_health: 'Every 6 hours',
};

const statusBadge = (status) => {
  const map = {
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    running: 'bg-blue-50 text-blue-700 border-blue-200',
    failed: 'bg-red-50 text-red-700 border-red-200',
    active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
  };
  return map[status] || 'bg-slate-50 text-slate-600 border-slate-200';
};

export default function BusinessOSPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [data, setData] = useState(null);
  const [processes, setProcesses] = useState(null);
  const [running, setRunning] = useState(false);
  const [runningProcess, setRunningProcess] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [handlingApproval, setHandlingApproval] = useState(null);

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
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-poll every 30s
  useEffect(() => {
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  const runCycle = async () => {
    setRunning(true);
    try {
      await api.post('/business-os/run');
      await load();
    } catch (e) {
      /* api interceptor handles toast */
    } finally {
      setRunning(false);
    }
  };

  const runProcess = async (pid) => {
    setRunningProcess(pid);
    try {
      await api.post('/business-os/processes/run', { process_id: pid });
      await load();
    } catch (e) {
      /* api interceptor handles toast */
    } finally {
      setRunningProcess(null);
    }
  };

  const handleApproval = async (id, action) => {
    setHandlingApproval(id);
    try {
      await api.post(`/business-os/approvals/${id}`, { action });
      toast.success(action === 'approve' ? 'Approved — executing now' : 'Denied');
      await load();
    } catch (e) { /* handled */ }
    finally { setHandlingApproval(null); }
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopBar title="Business OS" backTo="/app" />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-6">
          <div className="space-y-2">
            <div className="h-4 w-28 animate-pulse rounded-md bg-primary/10" />
            <div className="h-8 w-64 animate-pulse rounded-md bg-primary/10" />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-2xl bg-primary/10" />
            ))}
          </div>
          <div className="h-48 animate-pulse rounded-2xl bg-primary/10" />
        </div>
      </div>
    );
  }

  if (denied || !data) {
    return (
      <div className="min-h-screen">
        <TopBar title="Business OS" backTo="/app" />
        <div data-testid="business-os-denied" className="max-w-md mx-auto text-center py-24 px-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl border mb-4 text-muted-foreground">
            <Lock size={20} />
          </div>
          <h2 className="font-display text-xl">Workspace required</h2>
          <p className="text-sm text-muted-foreground mt-2">
            Business OS requires a workspace. Create one first.
          </p>
          <Button variant="secondary" className="rounded-xl mt-6" onClick={() => navigate('/app/team')}>
            Go to workspace
          </Button>
        </div>
      </div>
    );
  }

  const agents = data.agents || {};
  const recentRuns = data.recent_runs || [];
  const tasks = data.tasks || {};
  const learning = data.learning || {};
  const connectedTools = data.connected_tools || [];
  const processList = processes?.processes || {};

  const agentTypes = Object.keys(agents);
  const activeAgents = agentTypes.filter(t => agents[t]?.status === 'active').length;
  const totalDecisions = agentTypes.reduce((s, t) => s + (agents[t]?.decisions || 0), 0);
  const totalActions = agentTypes.reduce((s, t) => s + (agents[t]?.actions || 0), 0);

  return (
    <div className="min-h-screen">
      <TopBar title="Business OS" backTo="/app" />
      <main data-testid="business-os-page" className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* Hero */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-xs text-muted-foreground tracking-wide uppercase">Autonomous Operations</p>
            <h1 className="font-display text-2xl mt-1">Business OS</h1>
            <p className="text-sm text-muted-foreground mt-1.5 max-w-xl">
              Your company runs on autopilot. Agents detect issues, execute through connected tools, verify outcomes, and learn.
            </p>
          </div>
          <Button
            data-testid="business-os-run-cycle"
            className="rounded-xl"
            onClick={runCycle}
            disabled={running}
          >
            {running ? <Loader2 size={16} className="animate-spin mr-2" /> : <Play size={16} className="mr-2" />}
            Run full cycle
          </Button>
        </div>

        {/* Pending Approvals Inbox */}
        {approvals?.pending?.length > 0 && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Inbox size={16} className="text-amber-600" />
              <h2 className="text-sm font-medium">Pending Approvals ({approvals.summary?.pending || approvals.pending.length})</h2>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-amber-100 text-amber-700">
                Needs your attention
              </span>
            </div>
            <div className="space-y-2">
              {approvals.pending.slice(0, 5).map((item) => (
                <div key={item.id} data-testid={`approval-${item.id}`}
                  className="flex items-start justify-between gap-4 rounded-xl border bg-white px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium capitalize">{item.from_role || item.from_agent?.replace('_agent', '')}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${item.severity === 'high' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                        {item.severity}
                      </span>
                    </div>
                    <p className="text-sm mt-1">{item.summary}</p>
                    {item.recommendation && (
                      <p className="text-xs text-muted-foreground mt-0.5">{item.recommendation}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      data-testid={`approve-${item.id}`}
                      size="sm"
                      className="rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                      onClick={() => handleApproval(item.id, 'approve')}
                      disabled={handlingApproval === item.id}
                    >
                      {handlingApproval === item.id ? <Loader2 size={12} className="animate-spin mr-1" /> : <ThumbsUp size={12} className="mr-1" />}
                      Approve
                    </Button>
                    <Button
                      data-testid={`deny-${item.id}`}
                      size="sm"
                      variant="ghost"
                      className="rounded-lg text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleApproval(item.id, 'deny')}
                      disabled={handlingApproval === item.id}
                    >
                      <ThumbsDown size={12} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tool status */}
        <div className={`rounded-2xl border p-4 ${connectedTools.length > 0 ? 'bg-emerald-50/50 border-emerald-200' : 'bg-amber-50/50 border-amber-200'}`}>
          <div className="flex items-center gap-2 text-sm">
            <Wrench size={15} className={connectedTools.length > 0 ? 'text-emerald-600' : 'text-amber-600'} />
            <span className="font-medium">
              {connectedTools.length > 0
                ? `${connectedTools.length} tools connected — autonomous execution is live`
                : 'No tools connected — connect tools to enable autonomous execution'}
            </span>
          </div>
          {connectedTools.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {connectedTools.map(t => (
                <span key={t} className="text-[11px] px-2 py-0.5 rounded-full bg-white border text-emerald-700">
                  {t}
                </span>
              ))}
            </div>
          )}
          {connectedTools.length === 0 && (
            <Button
              variant="secondary"
              size="sm"
              className="rounded-lg mt-2"
              onClick={() => navigate('/app/team')}
            >
              Connect tools <ArrowRight size={12} className="ml-1" />
            </Button>
          )}
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-2xl border bg-card p-4">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Agents</p>
            <p className="font-display text-2xl mt-1">{activeAgents}/{agentTypes.length}</p>
            <p className="text-[11px] text-muted-foreground mt-1">active agents running</p>
          </div>
          <div className="rounded-2xl border bg-card p-4">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Decisions</p>
            <p className="font-display text-2xl mt-1">{totalDecisions}</p>
            <p className="text-[11px] text-muted-foreground mt-1">autonomous decisions made</p>
          </div>
          <div className="rounded-2xl border bg-card p-4">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Actions</p>
            <p className="font-display text-2xl mt-1">{totalActions}</p>
            <p className="text-[11px] text-muted-foreground mt-1">actions taken through tools</p>
          </div>
          <div className="rounded-2xl border bg-card p-4">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Learning</p>
            <p className="font-display text-2xl mt-1">{learning.total_learning_events || 0}</p>
            <p className="text-[11px] text-muted-foreground mt-1">patterns learned</p>
          </div>
        </div>

        {/* Autonomous Processes */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap size={15} strokeWidth={1.75} />
              <h2 className="text-sm font-medium">Autonomous Processes</h2>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(processList).slice(0, 6).map(([pid, proc]) => (
              <div key={pid} data-testid={`business-os-process-${pid}`} className="rounded-2xl border bg-card p-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium">{proc.label}</h3>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full border text-muted-foreground">
                      {proc.schedule}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{proc.description}</p>
                </div>
                <Button
                  data-testid={`business-os-run-${pid}`}
                  variant="secondary"
                  size="sm"
                  className="rounded-lg mt-3 w-full"
                  onClick={() => runProcess(pid)}
                  disabled={runningProcess === pid}
                >
                  {runningProcess === pid
                    ? <Loader2 size={14} className="animate-spin mr-1.5" />
                    : <Play size={13} className="mr-1.5" />}
                  Run now
                </Button>
              </div>
            ))}
          </div>
        </section>

        {/* Agents */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Activity size={15} strokeWidth={1.75} />
            <h2 className="text-sm font-medium">Agents</h2>
          </div>
          <div className="rounded-2xl border divide-y">
            {agentTypes.map((t) => {
              const a = agents[t];
              const lastRun = a?.last_run ? new Date(a.last_run).toLocaleString() : 'Never';
              return (
                <div key={t} data-testid={`business-os-agent-${t}`} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{a?.role || t}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${statusBadge(a?.status)}`}>
                        {a?.status || 'inactive'}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {a?.decisions || 0} decisions · {a?.actions || 0} actions · {a?.alerts || 0} alerts · Last: {lastRun}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0 ml-3">
                    <span>{a?.schedule || 'daily'}</span>
                    {a?.status === 'active' && <CheckCircle2 size={14} className="text-emerald-500" />}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Recent runs */}
        {recentRuns.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Clock size={15} strokeWidth={1.75} />
              <h2 className="text-sm font-medium">Recent Activity</h2>
            </div>
            <div className="rounded-2xl border divide-y">
              {recentRuns.slice(0, 8).map((run) => {
                const ts = run.created_at ? new Date(run.created_at).toLocaleString() : '';
                const label = run.label || run.type || run.process_id || 'Cycle';
                const executed = run.executed_count ?? run.agents_executed ?? 0;
                const total = run.agent_count ?? run.agents_run ?? 0;
                return (
                  <div key={run.id} data-testid="business-os-run-row" className="flex items-center justify-between px-4 py-2.5">
                    <div className="flex items-center gap-3 min-w-0">
                      {run.status === 'failed'
                        ? <XCircle size={14} className="text-red-400 shrink-0" />
                        : <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />}
                      <span className="text-sm truncate">{label}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0 ml-3">
                      <span>{executed}/{total} executed</span>
                      <span>{run.elapsed_s}s</span>
                      <span className="hidden sm:inline">{ts}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Tasks summary */}
        {tasks.total > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 size={15} strokeWidth={1.75} />
              <h2 className="text-sm font-medium">Task Pipeline</h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
              {[
                { label: 'Proposed', key: 'proposed', color: 'bg-slate-100 text-slate-700' },
                { label: 'Approved', key: 'approved', color: 'bg-blue-100 text-blue-700' },
                { label: 'Executed', key: 'executed', color: 'bg-emerald-100 text-emerald-700' },
                { label: 'Manual', key: 'manual', color: 'bg-amber-100 text-amber-700' },
                { label: 'Failed', key: 'failed', color: 'bg-red-100 text-red-700' },
                { label: 'Verified', key: 'verified', color: 'bg-violet-100 text-violet-700' },
                { label: 'Rejected', key: 'rejected', color: 'bg-slate-100 text-slate-500' },
              ].map(({ label, key, color }) => (
                <div key={key} className="rounded-xl border bg-card px-3 py-2 text-center">
                  <p className={`text-[11px] tracking-wide ${color.split(' ')[0]} inline-block px-1.5 py-0.5 rounded`}>
                    {(tasks[key] || 0)}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">{label}</p>
                </div>
              ))}
            </div>
          </section>
        )}

      </main>
    </div>
  );
}
