import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';

export default function HeroSection() {
  const navigate = useNavigate();
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center bg-[#0f1117] overflow-hidden pt-20">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_#b89165/8%,_transparent_60%)]" />
      <div className="relative max-w-4xl mx-auto px-6 sm:px-10 text-center">
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl text-white tracking-tight leading-[1.1]">
          From knowing to{' '}
          <span className="bg-gradient-to-r from-[#b89165] to-[#c9a86b] bg-clip-text text-transparent">doing</span>
        </h1>
        <p className="mt-6 text-lg sm:text-xl text-white/50 max-w-2xl mx-auto leading-relaxed">
          SmartDecigen turns your business instincts into an operating system — goal-anchored deep discussions, decision science, and autonomous execution.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Button onClick={() => navigate('/auth')}
            className="rounded-xl h-12 px-8 text-base font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-lg shadow-[#b89165]/20">
            Start your journey
          </Button>
          <Button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
            variant="outline" className="rounded-xl h-12 px-8 text-base border-white/10 text-white/60 hover:text-white/90">
            See how it works
          </Button>
        </div>
      </div>
    </section>
  );
}
