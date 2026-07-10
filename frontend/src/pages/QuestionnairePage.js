import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, Compass, Wallet, Trophy, Mountain } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';
import { trackPixel } from '../lib/pixel';

const QUESTIONS = [
  {
    key: 'dream',
    icon: Compass,
    eyebrow: 'Question 1 of 4',
    title: 'What is the dream you are quietly chasing?',
    hint: 'Not the LinkedIn version — the one you only say out loud at 1 AM. Two or three lines is enough.',
    placeholder: "e.g. Build a calm, profitable studio of my own — so I never have to ask anyone for a raise again.",
  },
  {
    key: 'capacity',
    icon: Wallet,
    eyebrow: 'Question 2 of 4',
    title: 'What is your real capacity right now?',
    hint: 'Honest hours per week, money you can risk, energy you can spare. The engine plans around your reality, not an ideal one.',
    placeholder: "e.g. ~8 hours a week after my day job, ~₹50k I can lose, energy is low on weekdays / better on Saturdays.",
  },
  {
    key: 'advantage',
    icon: Trophy,
    eyebrow: 'Question 3 of 4',
    title: 'What is your unfair advantage?',
    hint: 'The skill, network, taste, or knowledge most people in your spot do not have. We will lean on this.',
    placeholder: "e.g. 6 years inside the industry, 200+ warm contacts on WhatsApp, I write copy faster than most.",
  },
  {
    key: 'potential',
    icon: Mountain,
    eyebrow: 'Question 4 of 4',
    title: 'What do you believe you could become — if you actually moved?',
    hint: 'The ceiling you can almost see, but never name. One line.',
    placeholder: "e.g. The go-to person for D2C brand stories in India within two years.",
  },
];

export default function QuestionnairePage() {
  const navigate = useNavigate();
  const { setUser, user, setCredits } = useAuth();
  const [answers, setAnswers] = useState({ dream: '', capacity: '', advantage: '', potential: '' });
  const [bonus, setBonus] = useState(100);
  const [completed, setCompleted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0); // 0..3

  useEffect(() => {
    api.get('/user/questionnaire').then((r) => {
      setBonus(r.data?.bonus_credits ?? 100);
      setCompleted(!!r.data?.completed);
      if (r.data?.answers) {
        setAnswers({
          dream: r.data.answers.dream || '',
          capacity: r.data.answers.capacity || '',
          advantage: r.data.answers.advantage || '',
          potential: r.data.answers.potential || '',
        });
      }
    }).catch(() => {});
  }, []);

  const current = QUESTIONS[step];
  const value = answers[current.key];
  const isLast = step === QUESTIONS.length - 1;
  const canNext = (value || '').trim().length >= 3;

  const next = async () => {
    if (!canNext) {
      toast.error('A few words is enough — just so the engine can plan around you.');
      return;
    }
    if (!isLast) {
      setStep((s) => s + 1);
      return;
    }
    if (busy) return;
    setBusy(true);
    try {
      const r = await api.post('/user/questionnaire', answers);
      if (typeof r.data?.credits === 'number' && setCredits) setCredits(r.data.credits);
      if (setUser && user) {
        try {
          const next = { ...user, credits: r.data.credits ?? user.credits, questionnaire_completed: true };
          localStorage.setItem('sdg_user', JSON.stringify(next));
          setUser(next);
        } catch (_e) { /* noop */ }
      }
      if (r.data?.first_completion) {
        trackPixel('CompleteRegistration', { value: 399, currency: 'INR' });
        toast.success(`+${r.data.credits_added} credits dropped in your wallet.`);
      } else {
        toast.message('Your answers are updated.');
      }
      navigate('/app/new');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not save. Try again.');
      setBusy(false);
    }
  };

  const Icon = current.icon;

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title="Unlock your free credits" backTo="/" />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div data-testid="questionnaire-page" className="mb-7">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.22em] uppercase text-[#b89165] font-semibold">
            <Sparkles size={12} />
            {completed ? 'Update your context' : `₹399 worth of credits — yours in 4 questions`}
          </span>
          <h1 className="font-display text-3xl sm:text-4xl mt-3 leading-tight">
            {completed ? 'Refine what the engine knows about you.' : 'Tell the engine who it’s working with.'}
          </h1>
          <p className="text-sm text-muted-foreground mt-3 leading-6">
            {completed
              ? 'You already claimed the bonus — answers below stay grounded in every thread.'
              : `Every plan we draft for you will be grounded in these 4 answers. Finish all four, and ${bonus} bonus credits land in your wallet.`}
          </p>
        </div>

        {/* progress */}
        <div data-testid="questionnaire-progress" className="flex items-center gap-2 mb-7">
          {QUESTIONS.map((q, i) => (
            <div key={q.key}
              className={`h-1 flex-1 rounded-full transition-all ${i <= step ? 'bg-foreground' : 'bg-foreground/10'}`}
            />
          ))}
        </div>

        <Card className="rounded-2xl border border-border/70 premium-lift">
          <CardContent className="p-7 sm:p-9">
            <div className="flex items-center gap-2 text-[11px] tracking-[0.22em] uppercase text-[#b89165] font-semibold mb-3">
              <Icon size={14} strokeWidth={2} /> {current.eyebrow}
            </div>
            <h2 data-testid="questionnaire-question-title" className="font-display text-2xl sm:text-[28px] leading-tight">
              {current.title}
            </h2>
            <p className="text-sm text-muted-foreground mt-3 leading-6">{current.hint}</p>
            <div className="mt-6 space-y-1.5">
              <Label htmlFor={`q-${current.key}`} className="text-xs sr-only">{current.title}</Label>
              <Textarea
                id={`q-${current.key}`}
                data-testid={`questionnaire-input-${current.key}`}
                value={value}
                onChange={(e) => setAnswers((a) => ({ ...a, [current.key]: e.target.value }))}
                placeholder={current.placeholder}
                className="rounded-xl min-h-[140px]"
                autoFocus
              />
            </div>
            <div className="mt-6 flex items-center justify-between gap-3">
              <button
                type="button"
                data-testid="questionnaire-back-btn"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0 || busy}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Back
              </button>
              <Button
                onClick={next}
                disabled={!canNext || busy}
                data-testid="questionnaire-next-btn"
                className="rounded-xl active:scale-[0.98] transition-transform"
              >
                {busy
                  ? 'Granting credits…'
                  : isLast
                    ? (completed ? 'Save changes' : `Unlock ${bonus} credits`)
                    : 'Next'}
                <ArrowRight size={15} strokeWidth={2} className="ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <p className="mt-6 text-[11px] text-muted-foreground/80 text-center max-w-md mx-auto">
          Your answers stay private. They are used only to ground the engine — never shared, never sold.
        </p>
      </main>
    </div>
  );
}
