import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Loader2, CheckCircle2, Clock, Upload, MessageCircle, AlertTriangle, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  pending: 'bg-muted text-muted-foreground border-border/60',
  in_progress: 'bg-blue-50 text-blue-700 border-blue-200',
  awaiting_review: 'bg-amber-50 text-amber-700 border-amber-200',
  done: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  blocked: 'bg-red-50 text-red-700 border-red-200',
  needs_clarification: 'bg-orange-50 text-orange-700 border-orange-200',
};

const fmtDate = (iso) => {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }); }
  catch { return ''; }
};

const TaskCard = ({ task, onUpdate, busy }) => {
  const [expanded, setExpanded] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) {
      toast.error('File too large. Keep under 8 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setFile({ name: f.name, type: f.type, data: reader.result });
    reader.readAsDataURL(f);
  };

  const submitProof = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const base64 = file.data.split(',')[1];
      await api.patch(`/org/tasks/${task.id}`, {
        status: 'awaiting_review',
        proof_files: [{ name: file.name, type: file.type, data: base64, uploaded_at: new Date().toISOString() }],
      });
      toast.success('Proof submitted. AI is reviewing it now.');
      setFile(null);
      onUpdate();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not submit proof.');
    } finally { setUploading(false); }
  };

  const changeStatus = async (status) => {
    try {
      await api.patch(`/org/tasks/${task.id}`, { status });
      toast.success(`Task marked as ${status}.`);
      onUpdate();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not update status.');
    }
  };

  const askAboutTask = async () => {
    const msg = prompt('Ask SmartDecision about this task:');
    if (!msg) return;
    try {
      const r = await api.post('/brain/task-clarify', { task_id: task.id, question: msg });
      toast.success(r.data.answer);
    } catch (e) {
      toast.error('Could not get clarity right now.');
    }
  };

  const due = task.due_at ? new Date(task.due_at) : null;
  const overdue = due && due.getTime() < Date.now() && task.status !== 'done';

  return (
    <div className={`rounded-xl border bg-background px-4 py-3 ${overdue ? 'border-amber-200' : 'border-border/70'}`}>
      <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_COLORS[task.status] || 'bg-muted text-muted-foreground'}`}>
              {task.status.replace(/_/g, ' ')}
            </span>
            {overdue && <span className="text-[10px] text-amber-600 flex items-center gap-1"><Clock size={10} /> Overdue</span>}
            <span className="text-[10px] text-muted-foreground">{task.department_function}</span>
          </div>
          <p className="text-sm font-medium mt-1">{task.title}</p>
          {expanded && task.description && (
            <p className="text-xs text-muted-foreground mt-1.5 leading-5">{task.description}</p>
          )}
        </div>
        {expanded ? <ChevronUp size={16} className="text-muted-foreground shrink-0 mt-1" /> : <ChevronDown size={16} className="text-muted-foreground shrink-0 mt-1" />}
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/60 space-y-3">
          {task.founder_context && (
            <div className="rounded-lg border border-border/60 bg-[hsl(var(--accent))]/30 px-3 py-2 space-y-0.5">
              {task.founder_context.split('\n').map((line, i) => (
                <p key={i} className={`text-[11px] leading-5 ${i === 0 ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                  {line}
                </p>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock size={12} /> Due: {fmtDate(task.due_at)}
            {task.ai_review?.status !== 'pending' && (
              <Badge className={`rounded-lg text-[10px] font-normal ${task.ai_review?.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : task.ai_review?.status === 'flagged' ? 'bg-amber-50 text-amber-700' : ''}`}>
                AI: {task.ai_review?.status}
              </Badge>
            )}
          </div>

          {task.status === 'pending' && (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => changeStatus('in_progress')} className="rounded-lg h-8 px-3 text-xs">Start working</Button>
              <Button size="sm" variant="secondary" onClick={askAboutTask} className="rounded-lg h-8 px-3 text-xs border border-border/70">
                <MessageCircle size={12} className="mr-1" /> Ask about this
              </Button>
            </div>
          )}

          {task.status === 'in_progress' && (
            <div className="space-y-3">
              {!file ? (
                <div>
                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/70 bg-background text-xs cursor-pointer hover:bg-[hsl(var(--accent))]/40 transition-colors">
                    <Upload size={12} /> Upload proof (image/file)
                    <input type="file" accept="image/*,.pdf,.docx,.xlsx,.csv,.txt" className="hidden" onChange={handleFile} />
                  </label>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-[hsl(var(--accent))]/30 px-3 py-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText size={13} className="text-muted-foreground shrink-0" />
                    <span className="text-xs truncate">{file.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" onClick={submitProof} disabled={uploading} className="rounded-lg h-7 px-2.5 text-[11px]">
                      {uploading ? <Loader2 className="animate-spin" size={11} /> : 'Submit proof'}
                    </Button>
                    <button onClick={() => setFile(null)} className="text-muted-foreground hover:text-foreground text-xs">Change</button>
                  </div>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={askAboutTask} className="rounded-lg h-8 px-3 text-xs border border-border/70">
                  <MessageCircle size={12} className="mr-1" /> Ask about this
                </Button>
              </div>
            </div>
          )}

          {task.status === 'awaiting_review' && (
            <div className="flex items-center gap-2 text-xs">
              <Loader2 className="animate-spin" size={12} />
              AI is reviewing your proof...
              <Button size="sm" variant="secondary" onClick={askAboutTask} className="rounded-lg h-7 px-2.5 text-[11px] border border-border/70">
                <MessageCircle size={11} className="mr-1" /> Ask
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default function MyTasksPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get('/org/tasks/mine');
      setTasks(r.data.tasks || []);
    } catch (e) {
      if (e?.response?.status === 403) navigate('/app');
    } finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { load(); }, [load]);

  const filtered = filter === 'all' ? tasks : tasks.filter((t) => t.status === filter);
  const pending = tasks.filter((t) => t.status === 'pending').length;
  const inProgress = tasks.filter((t) => t.status === 'in_progress').length;
  const overdue = tasks.filter((t) => t.due_at && new Date(t.due_at).getTime() < Date.now() && t.status !== 'done').length;

  return (
    <div className="min-h-screen">
      <TopBar title="My Tasks" backTo="/app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-24 pt-4 space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 justify-center text-sm text-muted-foreground py-24">
            <Loader2 className="animate-spin" size={16} /> Loading your tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-24">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl border mb-4 text-muted-foreground"><CheckCircle2 size={20} /></div>
            <h2 className="font-display text-xl">No tasks yet</h2>
            <p className="text-sm text-muted-foreground mt-2">Your tasks will appear here once the founder generates the weekly plan.</p>
            <Button variant="secondary" className="rounded-xl mt-6" onClick={() => navigate('/app/brain')}>Open Brain</Button>
          </div>
        ) : (
          <>
            {/* summary */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-xl bg-[hsl(var(--accent))]/50 px-3 py-2">
                <div className="text-lg font-display">{tasks.length}</div>
                <div className="text-[10px] text-muted-foreground">Total</div>
              </div>
              <div className="rounded-xl bg-blue-50 px-3 py-2">
                <div className="text-lg font-display text-blue-600">{pending}</div>
                <div className="text-[10px] text-muted-foreground">Pending</div>
              </div>
              <div className="rounded-xl bg-emerald-50 px-3 py-2">
                <div className="text-lg font-display text-emerald-600">{inProgress}</div>
                <div className="text-[10px] text-muted-foreground">Active</div>
              </div>
              {overdue > 0 ? (
                <div className="rounded-xl bg-amber-50 px-3 py-2">
                  <div className="text-lg font-display text-amber-600">{overdue}</div>
                  <div className="text-[10px] text-muted-foreground">Overdue</div>
                </div>
              ) : (
                <div className="rounded-xl bg-[hsl(var(--accent))]/50 px-3 py-2">
                  <div className="text-lg font-display text-muted-foreground">0</div>
                  <div className="text-[10px] text-muted-foreground">Overdue</div>
                </div>
              )}
            </div>

            {/* filter tabs */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {['all', 'pending', 'in_progress', 'awaiting_review'].map((f) => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${filter === f ? 'bg-foreground text-background' : 'bg-[hsl(var(--accent))]/50 text-muted-foreground hover:text-foreground border border-border/60'}`}>
                  {f === 'all' ? 'All' : f.replace(/_/g, ' ')}
                  {f !== 'all' && <span className="ml-1 text-[10px] opacity-60">({tasks.filter((t) => t.status === f).length})</span>}
                </button>
              ))}
            </div>

            {/* task list */}
            <div className="space-y-2">
              {filtered.map((task) => (
                <TaskCard key={task.id} task={task} onUpdate={load} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
