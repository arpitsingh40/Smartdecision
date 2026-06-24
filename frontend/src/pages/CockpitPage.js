import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import {
  Target, Loader2, TrendingUp, CheckCircle2, Users, Activity, AlertTriangle, Lock, Gauge, Clock, Award,
} from 'lucide-react';

const fmtLeft = (iso) => {
  if (!iso) return '';
  const ms = new Date(iso).getTime() - Date.now();
  if (ms < 0) return 'overdue';
  const m = Math.round(ms / 60000);
  const d = Math.floor(m / 1440); const h = Math.floor((m % 1440) / 60);
  return d > 0 ? `${d}d ${h}h left` : `${h || 1}h left`;
};

const Stat = ({ icon: Icon, label, value, sub }) => (
  <div className="rounded-2xl border bg-card p-4">
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
      <Icon size={13} strokeWidth={1.75} /> {label}
    </div>
    <div className="font-display text-2xl leading-none">{value}</div>
    {sub ? <div className="text-[11px] text-muted-foreground mt-1">{sub}</div> : null}
  </div>
);

const alignColor = (s) => (s == null ? 'text-muted-foreground' : s >= 70 ? 'text-emerald-600' : s >= 40 ? 'text-amber-600' : 'text-red-600');

export default function CockpitPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get('/org/cockpit');
      setData(r.data);
    } catch (e) {
      if (e?.response?.status === 403 || e?.response?.status === 404) setDenied(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopBar title="Founder Cockpit" backTo="/team" />
        <div className="flex items-center gap-2 justify-center text-sm text-muted-foreground py-24">
          <Loader2 className="animate-spin" size={16} /> Loading your cockpit…
        </div>
      </div>
    );
  }

  if (denied || !data) {
    return (
      <div className="min-h-screen">
        <TopBar title="Founder Cockpit" backTo="/" />
        <div data-testid="cockpit-denied" className="max-w-md mx-auto text-center py-24 px-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl border mb-4 text-muted-foreground"><Lock size={20} /></div>
          <h2 className="font-display text-xl">This is the founder&apos;s private view</h2>
          <p className="text-sm text-muted-foreground mt-2">Only the workspace owner can open the cockpit.</p>
          <Button variant="secondary" className="rounded-xl mt-6" onClick={() => navigate('/brain')}>Go to Decision Brain</Button>
        </div>
      </div>
    );
  }

  const ns = data.north_star || {};
  const a = data.alignment || {};
  const ex = data.execution || {};
  const t = data.totals || {};
  const scored = a.scored || 0;
  const pct = (n) => (scored ? Math.round((100 * n) / scored) : 0);

  return (
    <div className="min-h-screen">
      <TopBar title="Founder Cockpit" backTo="/team" />
      <main data-testid="cockpit-page" className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 pt-4 space-y-6">

        {/* North Star */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2"><Target size={16} strokeWidth={1.75} /><h3 className="font-medium text-sm">North Star</h3></div>
            <span className="inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full border bg-background text-muted-foreground"><Lock size={11} /> Private</span>
          </div>
          {ns.north_star ? (
            <>
              <p data-testid="cockpit-northstar" className="font-display text-xl sm:text-2xl mt-1">{ns.north_star}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {ns.target ? ns.target : ''}{ns.target && ns.deadline ? ' · ' : ''}{ns.deadline ? `by ${ns.deadline}` : ''}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground mt-1">
              No North Star set yet. <button className="underline" onClick={() => navigate('/team')}>Set it on your Team page</button> so every decision is steered toward it.
            </p>
          )}
        </section>

        {/* top stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat icon={Activity} label="Decisions" value={t.decisions ?? 0} sub={`${t.last_7d ?? 0} in last 7 days`} />
          <div className="rounded-2xl border bg-card p-4">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><Gauge size={13} strokeWidth={1.75} /> Avg alignment</div>
            <div className={`font-display text-2xl leading-none ${alignColor(a.avg)}`} data-testid="cockpit-avg-alignment">{a.avg == null ? '—' : a.avg}</div>
            <div className="text-[11px] text-muted-foreground mt-1">{scored} scored</div>
          </div>
          <Stat icon={CheckCircle2} label="Follow-through" value={ex.follow_through_pct == null ? '—' : `${ex.follow_through_pct}%`} sub={`${ex.done ?? 0} done · ${ex.dropped ?? 0} dropped`} />
          <Stat icon={Users} label="Team" value={t.members ?? 0} sub="members" />
        </div>

        {/* alignment distribution */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center gap-2 mb-4"><TrendingUp size={16} strokeWidth={1.75} /><h3 className="font-medium text-sm">How on-strategy the team is deciding</h3></div>
          {scored === 0 ? (
            <p className="text-xs text-muted-foreground">No scored decisions yet. As your team uses the brain, this fills in.</p>
          ) : (
            <div className="space-y-3">
              {[['On strategy', a.high, 'bg-emerald-500'], ['Partly', a.medium, 'bg-amber-500'], ['Off strategy', a.low, 'bg-red-500']].map(([label, n, color]) => (
                <div key={label} className="flex items-center gap-3">
                  <span className="w-24 text-xs text-muted-foreground shrink-0">{label}</span>
                  <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                    <div className={`h-full ${color}`} style={{ width: `${pct(n || 0)}%` }} />
                  </div>
                  <span className="w-10 text-xs text-right tabular-nums">{n || 0}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* drift radar */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center gap-2 mb-4"><AlertTriangle size={16} strokeWidth={1.75} className="text-amber-600" /><h3 className="font-medium text-sm">Drift radar — decisions pulling sideways</h3></div>
          {(!data.drift || data.drift.length === 0) ? (
            <p className="text-xs text-muted-foreground">Nothing off-strategy. The team is pulling in your direction.</p>
          ) : (
            <div className="space-y-3">
              {data.drift.map((d) => (
                <div key={d.id} data-testid="cockpit-drift-item" className="rounded-xl border bg-background px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground truncate">{d.user_name || 'Member'}</span>
                    <span className={`text-xs font-medium ${alignColor(d.strategic_alignment?.score)}`}>{d.strategic_alignment?.score ?? '—'}/100</span>
                  </div>
                  <p className="text-sm mt-1 truncate" title={d.question}>{d.question}</p>
                  {d.strategic_alignment?.reason ? <p className="text-xs text-muted-foreground mt-1">{d.strategic_alignment.reason}</p> : null}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* in-flight actions — live timers */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2"><Clock size={16} strokeWidth={1.75} /><h3 className="font-medium text-sm">In flight — what the team is doing now</h3></div>
            {(ex.overdue ?? 0) > 0 && (
              <span data-testid="cockpit-overdue" className="text-xs text-amber-600 inline-flex items-center gap-1"><AlertTriangle size={12} /> {ex.overdue} overdue</span>
            )}
          </div>
          {(!data.active_actions || data.active_actions.length === 0) ? (
            <p className="text-xs text-muted-foreground">No commitments in flight. When the team commits to a move, the countdown shows here.</p>
          ) : (
            <div className="space-y-2">
              {data.active_actions.map((a) => (
                <div key={a.id} data-testid="cockpit-active-action" className="flex items-center justify-between gap-3 rounded-xl border bg-background px-4 py-2.5">
                  <div className="min-w-0">
                    <div className="text-xs text-muted-foreground truncate">{a.user_name}</div>
                    <p className="text-sm truncate" title={a.action}>{a.action}</p>
                  </div>
                  <span className={`shrink-0 text-xs font-mono-plex inline-flex items-center gap-1 ${a.overdue ? 'text-amber-600' : 'text-[hsl(var(--ring))]'}`}>
                    <Clock size={12} /> {fmtLeft(a.due_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* achieved — results feed */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center gap-2 mb-4"><Award size={16} strokeWidth={1.75} className="text-emerald-600" /><h3 className="font-medium text-sm">Achieved — the dream coming true</h3></div>
          {(!data.results || data.results.length === 0) ? (
            <p className="text-xs text-muted-foreground">No results logged yet. As the team finishes commitments and logs what happened, the wins land here.</p>
          ) : (
            <div className="space-y-3">
              {data.results.map((r) => (
                <div key={r.id} data-testid="cockpit-result-item" className="rounded-xl border bg-background px-4 py-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <CheckCircle2 size={13} className="text-emerald-600" /> {r.user_name}
                  </div>
                  {r.action ? <p className="text-sm mt-1 truncate" title={r.action}>{r.action}</p> : null}
                  <p className="text-sm text-foreground mt-1">{r.result}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* per-member */}
        <section className="rounded-2xl border bg-card p-6">
          <div className="flex items-center gap-2 mb-4"><Users size={16} strokeWidth={1.75} /><h3 className="font-medium text-sm">By teammate</h3></div>
          <div className="divide-y">
            <div className="flex items-center text-[11px] uppercase tracking-wide text-muted-foreground pb-2">
              <span className="flex-1">Member</span>
              <span className="w-20 text-right">Decisions</span>
              <span className="w-20 text-right">Alignment</span>
              <span className="w-16 text-right">Done</span>
            </div>
            {(data.per_member || []).map((m) => (
              <div key={m.user_id} data-testid="cockpit-member-row" className="flex items-center py-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{m.name || m.email}{m.role === 'owner' ? ' (you)' : ''}</div>
                  <div className="text-xs text-muted-foreground truncate">{m.email}</div>
                </div>
                <span className="w-20 text-right text-sm tabular-nums">{m.decisions}</span>
                <span className={`w-20 text-right text-sm tabular-nums ${alignColor(m.avg_alignment)}`}>{m.avg_alignment == null ? '—' : m.avg_alignment}</span>
                <span className="w-16 text-right text-sm tabular-nums">{m.done}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
