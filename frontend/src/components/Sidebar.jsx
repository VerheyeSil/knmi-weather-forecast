export default function Sidebar({ views, activeView, onSelect, collapsed, onToggleCollapsed }) {
  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar-header">
        {!collapsed && <span className="sidebar-title">KNMI data</span>}
        <button
          className="sidebar-toggle"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>

      <nav className="sidebar-nav">
        {views.map((v) => (
          <button
            key={v.id}
            className={`sidebar-nav-item ${v.id === activeView ? "is-active" : ""} ${
              !v.available ? "is-disabled" : ""
            }`}
            onClick={() => v.available && onSelect(v.id)}
            disabled={!v.available}
            title={collapsed ? v.label : undefined}
          >
            <span className="sidebar-nav-dot" />
            {!collapsed && (
              <span className="sidebar-nav-label">
                {v.label}
                {!v.available && <em className="sidebar-nav-soon">coming soon</em>}
              </span>
            )}
          </button>
        ))}
      </nav>
    </aside>
  );
}