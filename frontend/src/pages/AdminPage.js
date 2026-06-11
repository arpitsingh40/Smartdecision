import { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, Users, Activity, Globe, Coins } from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';

const fmt = (n) => (n ?? 0).toLocaleString('en-IN');
const fmtDur = (s) => {
  if (!s || s < 60) return `${s || 0}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
};
const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

const Stat = ({ label, value, sub, testId }) => (
  <div data-testid={testId} className="bg-white border border-border/70 rounded-xl px-4 py-3.5">
    <p className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
    <p className="font-mono-plex text-xl mt-1">{value}</p>
    {sub && <p className="text-[11px] text-muted-foreground mt-0.5">{sub}</p>}
  </div>
);

const SectionTitle = ({ icon: Icon, children }) => (
  <h2 className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground mt-8 mb-3">
    {Icon && <Icon size={13} strokeWidth={1.75} />} {children}
  </h2>
);

const Th = ({ children, right }) => (
  <th className={`px-3 py-2 text-[10px] uppercase tracking-[0.1em] font-medium text-muted-foreground ${right ? 'text-right' : 'text-left'}`}>{children}</th>
);
const Td = ({ children, right, mono, className = '' }) => (
  <td className={`px-3 py-2.5 text-[13px] ${right ? 'text-right' : ''} ${mono ? 'font-mono-plex text-xs' : ''} ${className}`}>{children}</td>
);

const Pager = ({ page, pages, onPage }) => pages > 1 ? (
  <div className="flex items-center justify-end gap-3 mt-3 text-xs text-muted-foreground">
    <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="disabled:opacity-30 hover:text-foreground">← Prev</button>
    <span className="font-mono-plex">{page} / {pages}</span>
    <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="disabled:opacity-30 hover:text-foreground">Next →</button>
  </div>
) : null;

// ---------------------------------------------------------------- Overview
function Overview() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/overview').then((r) => setD(r.data)).catch(() => {}); }, []);
  if (!d) return <p className="text-sm text-muted-foreground mt-8">Loading…</p>;
  return (
    <div data-testid="admin-overview">
      <SectionTitle icon={Users}>Users</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Stat testId="stat-users-total" label="Total users" value={fmt(d.users.total)} />
        <Stat label="New · 7 days" value={fmt(d.users.new_7d)} />
        <Stat label="Active · 24h" value={fmt(d.users.active_24h)} />
      </div>
      <SectionTitle icon={Activity}>Engine</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat testId="stat-questions" label="Questions asked" value={fmt(d.engine.questions_total)} sub={`${fmt(d.engine.questions_7d)} this week`} />
        <Stat label="Normal turns" value={fmt(d.engine.turns_normal)} />
        <Stat label="Ultra turns" value={fmt(d.engine.turns_ultra)} />
        <Stat label="Tokens in / out" value={`${fmt(d.tokens.input_total)} / ${fmt(d.tokens.output_total)}`} />
      </div>
      <SectionTitle icon={Coins}>Credits & revenue</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat testId="stat-credits-issued" label="Credits issued" value={fmt(d.credits.issued_total)} sub={`${fmt(d.credits.issued_free)} free · ${fmt(d.credits.issued_paid)} paid`} />
        <Stat label="Credits spent" value={fmt(d.credits.spent)} />
        <Stat label="Outstanding" value={fmt(d.credits.outstanding)} />
        <Stat testId="stat-revenue" label="Revenue" value={`₹${fmt(d.revenue.total_inr)}`} sub={`${fmt(d.revenue.purchases)} purchases`} />
      </div>
      <SectionTitle icon={Globe}>Traffic</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat testId="stat-sessions" label="Sessions" value={fmt(d.traffic.sessions_total)} sub={`${fmt(d.traffic.sessions_7d)} this week`} />
        <Stat label="Unique IPs" value={fmt(d.traffic.unique_ips)} />
        <Stat label="Avg session" value={fmtDur(d.traffic.avg_session_s)} />
        <Stat label="Active now" value={fmt(d.traffic.active_now)} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Users + drilldown
function UserDetail({ userId, onBack }) {
  const [d, setD] = useState(null);
  useEffect(() => { api.get(`/admin/users/${userId}/activity`).then((r) => setD(r.data)).catch(() => {}); }, [userId]);
  if (!d) return <p className="text-sm text-muted-foreground mt-8">Loading…</p>;
  const u = d.user;
  return (
    <div data-testid="admin-user-detail" className="mt-6">
      <button data-testid="user-detail-back" onClick={onBack} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft size={13} /> All users
      </button>
      <div className="mt-4 bg-white border border-border/70 rounded-xl p-5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="font-display text-xl">{u.name || u.email}</h2>
          <span className="text-xs text-muted-foreground">{u.email}</span>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1.5 mt-3 text-xs text-muted-foreground">
          <span>Country: <span className="text-foreground">{u.country || 'Unknown'}{u.city && u.city !== u.country ? ` · ${u.city}` : ''}</span></span>
          <span>Questions: <span className="font-mono-plex text-foreground">{fmt(u.questions_asked)}</span></span>
          <span>Credits: <span className="font-mono-plex text-foreground">{fmt(u.credits)}</span></span>
          <span>Issued free/paid: <span className="font-mono-plex text-foreground">{fmt(u.credits_issued_free)} / {fmt(u.credits_issued_paid)}</span></span>
          <span>Tokens in/out: <span className="font-mono-plex text-foreground">{fmt(u.tokens_in)} / {fmt(u.tokens_out)}</span></span>
          <span>Joined: <span className="text-foreground">{fmtDate(u.created_at)}</span></span>
        </div>
      </div>
      <SectionTitle>Questions & engine replies</SectionTitle>
      {d.threads.length === 0 && <p className="text-sm text-muted-foreground">No goals opened yet.</p>}
      {d.threads.map((t) => (
        <div key={t.thread_id} className="bg-white border border-border/70 rounded-xl p-4 mb-3">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-sm font-medium">{t.goal}</p>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">{t.status}</span>
          </div>
          <div className="mt-2 space-y-3">
            {t.qa.length === 0 && <p className="text-xs text-muted-foreground">No turns yet.</p>}
            {t.qa.map((m, i) => (
              <div key={i} className="border-l-2 border-border pl-3">
                <p className="text-[13px]"><span className="text-muted-foreground">Q · </span>{m.question}</p>
                <p className="text-[13px] mt-1 text-muted-foreground"><span>A · </span>{m.reply}</p>
                <p className="font-mono-plex text-[10px] text-muted-foreground/70 mt-1">{m.intent || ''} {m.at ? `· ${fmtDate(m.at)}` : ''}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
      <SectionTitle>Credit ledger</SectionTitle>
      <div className="bg-white border border-border/70 rounded-xl overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-border/70"><tr><Th>Type</Th><Th right>Credits</Th><Th>Detail</Th><Th>When</Th></tr></thead>
          <tbody>
            {d.ledger.map((e) => (
              <tr key={e.id} className="border-b border-border/40 last:border-0">
                <Td>{e.type.replace('_', ' ')}</Td>
                <Td right mono className={e.credits > 0 ? 'text-[hsl(var(--success))]' : ''}>{e.credits > 0 ? `+${e.credits}` : e.credits}</Td>
                <Td mono>{e.amount_inr ? `₹${e.amount_inr}` : e.mode || e.reason || '—'}</Td>
                <Td mono>{fmtDate(e.at)}</Td>
              </tr>
            ))}
            {d.ledger.length === 0 && <tr><Td className="text-muted-foreground" colSpan={4}>No movements yet.</Td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UsersTab() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(null);
  const load = useCallback(() => {
    api.get('/admin/users', { params: { page, limit: 25, q } }).then((r) => setData(r.data)).catch(() => {});
  }, [page, q]);
  useEffect(() => { load(); }, [load]);
  if (selected) return <UserDetail userId={selected} onBack={() => setSelected(null)} />;
  return (
    <div data-testid="admin-users" className="mt-6">
      <input data-testid="admin-users-search" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }}
        placeholder="Search email, name or country…"
        className="w-full sm:w-80 bg-white border border-border/70 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))]" />
      <div className="mt-4 bg-white border border-border/70 rounded-xl overflow-x-auto">
        <table className="w-full" data-testid="admin-users-table">
          <thead className="border-b border-border/70">
            <tr><Th>User</Th><Th>Country</Th><Th right>Questions</Th><Th right>Credits</Th><Th right>Tokens in/out</Th><Th>Joined</Th></tr>
          </thead>
          <tbody>
            {(data?.items || []).map((u) => (
              <tr key={u.id} data-testid="admin-user-row" onClick={() => setSelected(u.id)}
                className="border-b border-border/40 last:border-0 cursor-pointer hover:bg-secondary/60 transition-colors">
                <Td>
                  <span className="font-medium">{u.name || '—'}</span>
                  <span className="block text-[11px] text-muted-foreground">{u.email}{u.is_admin ? ' · founder' : ''}</span>
                </Td>
                <Td>{u.country || 'Unknown'}</Td>
                <Td right mono>{fmt(u.questions_asked)}</Td>
                <Td right mono>{fmt(u.credits)}</Td>
                <Td right mono>{fmt(u.tokens_in)} / {fmt(u.tokens_out)}</Td>
                <Td mono>{fmtDate(u.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager page={page} pages={data?.pages || 1} onPage={setPage} />
    </div>
  );
}

// ---------------------------------------------------------------- Traffic
function TrafficTab() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  useEffect(() => { api.get('/admin/traffic', { params: { page, limit: 25 } }).then((r) => setData(r.data)).catch(() => {}); }, [page]);
  if (!data) return <p className="text-sm text-muted-foreground mt-8">Loading…</p>;
  const s = data.summary;
  return (
    <div data-testid="admin-traffic" className="mt-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Sessions" value={fmt(s.sessions_total)} />
        <Stat label="Unique IPs" value={fmt(s.unique_ips)} />
        <Stat label="Avg time spent" value={fmtDur(s.avg_session_s)} />
        <Stat label="Active now" value={fmt(s.active_now)} />
      </div>
      <div className="mt-4 bg-white border border-border/70 rounded-xl overflow-x-auto">
        <table className="w-full" data-testid="admin-traffic-table">
          <thead className="border-b border-border/70">
            <tr><Th>IP</Th><Th>City</Th><Th>Country</Th><Th>User</Th><Th right>Time spent</Th><Th>Started</Th></tr>
          </thead>
          <tbody>
            {data.items.map((t) => (
              <tr key={t.session_id} className="border-b border-border/40 last:border-0">
                <Td mono>{t.ip || '—'}</Td>
                <Td>{t.city}</Td>
                <Td>{t.country}</Td>
                <Td className="text-[12px]">{t.user_email || <span className="text-muted-foreground">visitor</span>}</Td>
                <Td right mono>{fmtDur(t.duration_s)}</Td>
                <Td mono>{fmtDate(t.started_at)}</Td>
              </tr>
            ))}
            {data.items.length === 0 && <tr><Td className="text-muted-foreground" colSpan={6}>No sessions yet.</Td></tr>}
          </tbody>
        </table>
      </div>
      <Pager page={page} pages={data.pages} onPage={setPage} />
    </div>
  );
}

// ---------------------------------------------------------------- Usage
function UsageTab() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  useEffect(() => { api.get('/admin/usage', { params: { page, limit: 25 } }).then((r) => setData(r.data)).catch(() => {}); }, [page]);
  if (!data) return <p className="text-sm text-muted-foreground mt-8">Loading…</p>;
  const s = data.summary;
  return (
    <div data-testid="admin-usage" className="mt-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat testId="usage-credits-issued" label="Credits issued" value={fmt(s.credits.issued_total)} sub={`${fmt(s.credits.issued_free)} free · ${fmt(s.credits.issued_paid)} paid`} />
        <Stat label="Credits spent / outstanding" value={`${fmt(s.credits.spent)} / ${fmt(s.credits.outstanding)}`} />
        <Stat testId="usage-tokens" label="Input / output tokens" value={`${fmt(s.tokens.input_total)} / ${fmt(s.tokens.output_total)}`} />
        <Stat label="Revenue" value={`₹${fmt(s.revenue.total_inr)}`} sub={`${fmt(s.turns.normal)} normal · ${fmt(s.turns.ultra)} ultra turns`} />
      </div>
      <div className="mt-4 bg-white border border-border/70 rounded-xl overflow-x-auto">
        <table className="w-full" data-testid="admin-usage-table">
          <thead className="border-b border-border/70">
            <tr><Th>User</Th><Th right>Questions</Th><Th right>Free issued</Th><Th right>Paid issued</Th><Th right>Balance</Th><Th right>Tokens in/out</Th></tr>
          </thead>
          <tbody>
            {data.items.map((u) => (
              <tr key={u.id} className="border-b border-border/40 last:border-0">
                <Td><span className="text-[12px]">{u.email}</span></Td>
                <Td right mono>{fmt(u.questions_asked)}</Td>
                <Td right mono>{fmt(u.credits_issued_free)}</Td>
                <Td right mono>{fmt(u.credits_issued_paid)}</Td>
                <Td right mono>{fmt(u.credits)}</Td>
                <Td right mono>{fmt(u.tokens_in)} / {fmt(u.tokens_out)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager page={page} pages={data.pages} onPage={setPage} />
    </div>
  );
}

// ---------------------------------------------------------------- page
const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'Users' },
  { id: 'traffic', label: 'Traffic' },
  { id: 'usage', label: 'Usage' },
];

export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState('overview');
  if (user && !user.is_admin) {
    return (
      <div className="min-h-screen">
        <TopBar title="Founder OS" backTo="/" />
        <main className="max-w-2xl mx-auto px-4 pt-16 text-center">
          <p data-testid="admin-denied" className="text-sm text-muted-foreground">This area is reserved for the founder.</p>
        </main>
      </div>
    );
  }
  return (
    <div className="min-h-screen pb-16">
      <TopBar title="Founder OS" backTo="/" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div data-testid="admin-tabs" className="inline-flex items-center rounded-xl border border-border/70 bg-white p-0.5">
          {TABS.map((t) => (
            <button key={t.id} data-testid={`admin-tab-${t.id}`} onClick={() => setTab(t.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs transition-colors ${tab === t.id ? 'bg-[hsl(var(--accent))] text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
              {t.label}
            </button>
          ))}
        </div>
        {tab === 'overview' && <Overview />}
        {tab === 'users' && <UsersTab />}
        {tab === 'traffic' && <TrafficTab />}
        {tab === 'usage' && <UsageTab />}
      </main>
    </div>
  );
}
