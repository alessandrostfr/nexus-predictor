import { Inbox } from 'lucide-react';

// Reusable empty state for shell screens that will be completed in later blocks.
export function EmptyPanel({ title, description }) {
  return (
    <article className="empty-panel">
      <span className="empty-panel-icon">
        <Inbox size={20} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  );
}
