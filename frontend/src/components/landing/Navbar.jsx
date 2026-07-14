import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';

const NAV_LINKS = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Testimonials', href: '#testimonials' },
];

export default function Navbar() {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
        scrolled
          ? 'bg-[#0f1117]/80 backdrop-blur-2xl border-b border-white/[0.06] shadow-lg shadow-black/20'
          : 'bg-[#0f1117]/40 backdrop-blur-sm'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="flex items-center justify-between h-16 sm:h-20">
          <button onClick={() => navigate('/')} className="flex items-center gap-2.5">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5" stroke="#b89165" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              <path d="M9 21 L11 22.7 L9 24.4" stroke="#b89165" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
            <span className="text-sm tracking-[0.32em] font-semibold uppercase text-white/90">SmartDecigen</span>
          </button>

          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href}
                className="text-sm text-white/60 hover:text-white/90 transition-colors">
                {l.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/auth')}
              className="text-sm text-white/70 hover:text-white/90 transition-colors px-3 py-2">
              Sign in
            </button>
            <Button onClick={() => navigate('/auth')}
              className="rounded-xl h-10 px-5 text-sm font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-lg shadow-[#b89165]/20">
              Get started
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
