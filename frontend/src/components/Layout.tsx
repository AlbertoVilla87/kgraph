import { Outlet, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Bell, Plus, ArrowUpRight, Compass } from 'lucide-react';

const notifications = [
  {
    title: 'Analysis complete',
    body: 'Attention Is All You Need · 18 topics mapped',
    time: '2m',
    tone: 'var(--color-primary)',
  },
  {
    title: '3 new references shared',
    body: 'GNN line of works now connect to Transformer',
    time: '1h',
    tone: 'var(--color-violet)',
  },
  {
    title: 'Research gap detected',
    body: 'Attention × Long-term memory: no evidence found',
    time: '3h',
    tone: 'var(--color-amber)',
  },
];

export default function Layout() {
  const navigate = useNavigate();
  const [notifOpen, setNotifOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setNotifOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="h-screen flex bg-[var(--color-ink)] text-[var(--color-text)] overflow-hidden">
      {/* ---------- Left glass rail ---------- */}
      <aside className="w-[68px] shrink-0 flex flex-col items-center gap-1 py-3 px-2 m-3 mr-0 rounded-2xl glass z-20">
        <button
          onClick={() => navigate('/')}
          className="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-cobalt)] shadow-[0_8px_24px_-8px_var(--color-primary-glow)] group relative"
          title="Astrolabe"
        >
          <Compass size={20} className="text-[#04201c]" />
        </button>
        <div className="w-8 h-px bg-[var(--color-line)] my-2" />

        <div className="flex-1" />

        <button className="w-11 h-11 flex items-center justify-center rounded-xl text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] transition-colors" title="Help">
          <ArrowUpRight size={19} strokeWidth={1.8} />
        </button>
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--color-violet)] to-[var(--color-rose)] flex items-center justify-center text-xs font-semibold text-white">
          AV
        </div>
      </aside>

      {/* ---------- Main column ---------- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* ---------- Floating command bar ---------- */}
        <header className="pr-4 pl-4 pt-3 pb-2 z-20">
          <div className="glass rounded-2xl h-14 px-4 flex items-center justify-between gap-4">
            {/* Masthead */}
            <div className="flex items-center gap-3 min-w-0">
              <div className="hidden sm:block leading-none">
                <span className="font-display text-[17px] font-semibold tracking-tight">
                  Astrolabe
                </span>
                <span className="block text-[9px] uppercase tracking-[0.22em] text-[var(--color-text-faint)] font-mono mt-0.5">
                  citation observatory
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Write */}
              <button
                onClick={() => navigate('/')}
                className="btn-primary hidden sm:flex items-center gap-1.5 px-4 h-9 text-sm"
              >
                <Plus size={15} strokeWidth={2.4} />
                New Analysis
              </button>

              {/* Notifications */}
              <div className="relative">
                <button
                  onClick={() => setNotifOpen((v) => !v)}
                  className={`relative w-9 h-9 rounded-xl flex items-center justify-center transition-colors ${
                    notifOpen
                      ? 'text-[var(--color-text)] bg-[var(--color-surface-3)]'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)]'
                  }`}
                  title="Notifications"
                >
                  <Bell size={17} strokeWidth={1.8} />
                  <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[var(--color-primary)] pulse-dot" />
                </button>

                {notifOpen && (
                  <>
                    <div className="fixed inset-0 z-20" onClick={() => setNotifOpen(false)} />
                    <div className="absolute right-0 top-11 w-80 rounded-2xl glass-chip p-2 z-30 animate-pop">
                      <div className="flex items-center justify-between px-3 py-2">
                        <span className="text-sm font-semibold">Notifications</span>
                        <span className="data-label">3 new</span>
                      </div>
                      <div className="space-y-1">
                        {notifications.map((n) => (
                          <button
                            key={n.title}
                            className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[var(--color-surface-3)] transition-colors"
                          >
                            <div className="flex items-center gap-2 text-sm font-medium">
                              <span
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ background: n.tone }}
                              />
                              <span className="truncate">{n.title}</span>
                              <span className="ml-auto text-[10px] text-[var(--color-text-faint)]">
                                {n.time}
                              </span>
                            </div>
                            <div className="text-xs text-[var(--color-text-secondary)] mt-0.5 pl-4">
                              {n.body}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* ---------- Page content ---------- */}
        <main className="flex-1 min-h-0 overflow-y-auto p-4 md:p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}