import { useNavigate } from 'react-router-dom';

const FOOTER_LINKS = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Features', href: '#features' },
  { label: 'Testimonials', href: '#testimonials' },
];

export default function Footer() {
  const navigate = useNavigate();

  return (
    <footer className="bg-[#0a0b0f] border-t border-white/[0.05]">
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-14 py-12 sm:py-16">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-8">
          <div className="flex items-center gap-2.5">
            <svg width="18" height="18" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5" stroke="#b89165" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              <path d="M9 21 L11 22.7 L9 24.4" stroke="#b89165" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
            <span className="text-xs tracking-[0.32em] font-semibold uppercase text-white/60">SmartDecigen</span>
          </div>

          <div className="flex items-center gap-6">
            {FOOTER_LINKS.map((l) => (
              <a key={l.href} href={l.href}
                className="text-xs text-white/40 hover:text-white/70 transition-colors">
                {l.label}
              </a>
            ))}
            <button onClick={() => navigate('/auth')}
              className="text-xs text-white/40 hover:text-white/70 transition-colors">
              Sign in
            </button>
          </div>

          <div className="text-xs text-white/30">
            &copy; {new Date().getFullYear()} SmartDecigen. All rights reserved.
          </div>
        </div>
      </div>
    </footer>
  );
}
