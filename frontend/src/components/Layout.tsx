import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import {
  LayoutDashboard,
  GitBranch,
  Layers,
  Sparkles,
  Search,
  Bookmark,
  Settings,
  Bell,
  Plus,
  Command,
  ArrowUpRight,
  X,
  Compass,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview', hint: 'Analyze a paper · see the graph' },
  { to: '/graph', icon: GitBranch, label: 'Graph Explorer', hint: 'Free exploration of the graph' },
  { to: '/shared', icon: Layers, label: 'Shared Insights', hint: 'Concepts common across documents' },
  { to: '/originality', icon: Sparkles, label: 'Originality', hint: 'What is new and what is missing' },
  { to: '/gaps', icon: Search, label: 'Research Gaps', hint: 'Weak and missing connections' },
  { to: '/saved', icon: Bookmark, label: 'Saved Analyses', hint: 'Previously analyzed papers' },
  { to: '/settings', icon: Settings, label: 'Settings', hint: 'Configuration and API' },
];

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
  const [searchOpen, setSearchOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [query, setQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setNotifOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (searchOpen) setTimeout(() => searchRef.current?.focus(), 40);
  }, [searchOpen]);

  const filtered =
    query.trim().length === 0
      ? navItems
      : navItems.filter(
          (n) =>
            n.label.toLowerCase().includes(query.toLowerCase()) ||
            n.hint.toLowerCase().includes(query.toLowerCase()),
        );

  const go = (to: string) => {
    setSearchOpen(false);
    setQuery('');
    navigate(to);
  };

  return (
    <div className="h-screen flex bg-[var(--color-ink)] text-[var(--color-text)] overflow-hidden">
      {/* ---------- Left glass rail ---------- */}
      <aside className="w-[68px] shrink-0 flex flex-col items-center gap-1 py-3 px-2 m-3 mr-0 rounded-2xl glass z-20">
        <button
          onClick={() => go('/')}
          className="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-cobalt)] shadow-[0_8px_24px_-8px_var(--color-primary-glow)] group relative"
          title="Astrolabe"
        >
          <Compass size={20} className="text-[#04201c]" />
        </button>
        <div className="w-8 h-px bg-[var(--color-line)] my-2" />

        {navItems.map(({ to, icon: Icon, label }) => (
          <div key={to} className="relative group">
            <NavLink
              to={to}
              title={label}
              className={({ isActive }) =>
                `w-11 h-11 flex items-center justify-center rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)] shadow-[0_0_20px_-6px_var(--color-primary-glow)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)]'
                }`
              }
            >
              <Icon size={19} strokeWidth={1.8} />
            </NavLink>
            {/* Tooltip */}
            <span className="pointer-events-none absolute left-[52px] top-1/2 -translate-y-1/2 whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium glass-chip opacity-0 translate-x-[-4px] group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 z-30">
              {label}
            </span>
          </div>
        ))}

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

            {/* Search */}
            <button
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 flex-1 max-w-md px-3.5 h-9 rounded-xl glass-chip text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text)] hover:border-[var(--color-primary-glow)] transition-colors"
            >
              <Search size={15} />
              <span className="flex-1 text-left truncate">Search the observatory…</span>
              <kbd className="hidden md:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-[var(--color-surface-3)] text-[10px] font-mono text-[var(--color-text-faint)]">
                <Command size={10} /> K
              </kbd>
            </button>

            <div className="flex items-center gap-2">
              {/* Write */}
              <button
                onClick={() => go('/')}
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

        {/* Search command menu */}
        {searchOpen && (
          <div className="fixed inset-0 z-40 flex items-start justify-center pt-[16vh] px-4">
            <div
              className="absolute inset-0 bg-black/55 backdrop-blur-sm"
              onClick={() => setSearchOpen(false)}
            />
            <div className="relative w-full max-w-lg rounded-2xl glass p-2 animate-pop">
              <div className="flex items-center gap-2 px-3 border-b border-[var(--color-border)] pb-2">
                <Search size={16} className="text-[var(--color-text-faint)]" />
                <input
                  ref={searchRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search pages, topics, papers…"
                  className="flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-[var(--color-text-faint)]"
                />
                <button
                  onClick={() => setSearchOpen(false)}
                  className="p-1.5 rounded-lg text-[var(--color-text-faint)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)]"
                >
                  <X size={15} />
                </button>
              </div>
              <div className="pt-2 space-y-1 max-h-72 overflow-y-auto">
                {filtered.map(({ to, icon: Icon, label, hint }) => (
                  <button
                    key={to}
                    onClick={() => go(to)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[var(--color-surface-3)] transition-colors group"
                  >
                    {
                      <span className="w-8 h-8 rounded-lg flex items-center justify-center bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] group-hover:text-[var(--color-primary)] group-hover:bg-[var(--color-primary-soft)] transition-colors">
                        <Icon size={16} />
                      </span>
                    }
                    <span className="flex-1 text-left">
                      <span className="block text-sm font-medium">{label}</span>
                      <span className="block text-xs text-[var(--color-text-faint)]">{hint}</span>
                    </span>
                    <ArrowUpRight
                      size={14}
                      className="text-[var(--color-text-faint)] opacity-0 group-hover:opacity-100 transition-opacity"
                    />
                  </button>
                ))}
                {filtered.length === 0 && (
                  <div className="px-3 py-6 text-center text-sm text-[var(--color-text-faint)]">
                    No results for “{query}”
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ---------- Page content ---------- */}
        <main className="flex-1 min-h-0 overflow-y-auto p-4 md:p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}