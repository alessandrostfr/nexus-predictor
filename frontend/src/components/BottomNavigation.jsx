// Fixed mobile navigation. It keeps the MVP easy to use with one hand.
export function BottomNavigation({ activeView, navItems, onViewChange }) {
  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeView === item.id;

        return (
          <button
            key={item.id}
            type="button"
            className={isActive ? 'bottom-nav-button bottom-nav-button-active' : 'bottom-nav-button'}
            onClick={() => onViewChange(item.id)}
            aria-pressed={isActive}
          >
            <Icon size={18} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
