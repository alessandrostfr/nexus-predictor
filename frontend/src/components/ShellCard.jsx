// Generic glass card used across the dashboard shell.
export function ShellCard({ eyebrow, title, description, children, className = '' }) {
  return (
    <section className={`shell-card ${className}`.trim()}>
      {eyebrow ? <span className="shell-card-eyebrow">{eyebrow}</span> : null}
      {title ? <h2>{title}</h2> : null}
      {description ? <p>{description}</p> : null}
      {children}
    </section>
  );
}
