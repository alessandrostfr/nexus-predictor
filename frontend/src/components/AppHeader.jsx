import { Activity, Sparkles } from 'lucide-react';

// Top navigation for tablet and desktop. Mobile uses BottomNavigation.
export function AppHeader({ activeView, navItems, selectedYear, onViewChange }) {
  return (
    <header className="app-header">
      <button className="brand-button" type="button" onClick={() => onViewChange('dashboard')}>
        <span className="brand-mark">
          <Sparkles size={18} />
        </span>
        <span>
          <strong>Nexus Predictor</strong>
          <small>Dashboard MVP</small>
        </span>
      </button>

      <nav className="desktop-nav" aria-label="Primary navigation">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;

          return (
            <button
              key={item.id}
              type="button"
              className={isActive ? 'nav-button nav-button-active' : 'nav-button'}
              onClick={() => onViewChange(item.id)}
              aria-pressed={isActive}
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="header-status" aria-label="Current roadmap block">
        <Activity size={15} />
        Block 7 · {selectedYear}
      </div>
    </header>
  );
}
