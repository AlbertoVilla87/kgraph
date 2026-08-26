import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  Layers,
  Sparkles,
  Search,
  Bookmark,
  Settings,
  HelpCircle,
  Moon,
  Sun,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/graph', icon: GitBranch, label: 'Graph Explorer' },
  { to: '/shared', icon: Layers, label: 'Shared Insights' },
  { to: '/originality', icon: Sparkles, label: 'Originality' },
  { to: '/gaps', icon: Search, label: 'Research Gaps' },
  { to: '/saved', icon: Bookmark, label: 'Saved Analyses' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className="flex h-screen bg-[var(--color-bg)]">
      {/* Sidebar */}
      <aside className="w-16 bg-[var(--color-sidebar)] flex flex-col items-center py-4 gap-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${
                isActive
                  ? 'bg-[var(--color-sidebar-active)] text-white'
                  : 'text-gray-400 hover:bg-[var(--color-sidebar-hover)] hover:text-white'
              }`
            }
            title={label}
          >
            <Icon size={18} />
          </NavLink>
        ))}
        <div className="flex-1" />
        <button
          className="w-10 h-10 flex items-center justify-center rounded-lg text-gray-400 hover:bg-[var(--color-sidebar-hover)] hover:text-white"
          title="Help"
        >
          <HelpCircle size={18} />
        </button>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 border-b border-[var(--color-border)] bg-[var(--color-card)] flex items-center px-6 justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] flex items-center justify-center">
              <GitBranch size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-[var(--color-text)] leading-none">
                ArXiv Graph Explorer
              </h1>
              <p className="text-[10px] text-[var(--color-text-secondary)]">
                Discover topics. Reveal connections. Find research gaps.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100"
              title="Toggle dark mode"
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600">
              U
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
