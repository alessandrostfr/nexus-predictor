import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import type { ReactNode } from 'react';

export function StatusPill({ tone = 'info', children }: { tone?: 'info' | 'ok' | 'warning' | 'danger'; children: ReactNode }) {
  const Icon = tone === 'ok' ? CheckCircle2 : tone === 'warning' || tone === 'danger' ? AlertTriangle : Info;
  const className = tone === 'ok' ? 'badge acid' : tone === 'warning' ? 'badge orange' : tone === 'danger' ? 'badge pink' : 'badge cyan';

  return (
    <span className={className}>
      <Icon size={14} />
      {children}
    </span>
  );
}
