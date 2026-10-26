import type { HTMLAttributes, ReactNode } from 'react';

interface BentoGridProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

/** Magic UI Bento Grid layout adapted to the portal's plain CSS design. */
export function BentoGrid({
  children,
  className = '',
  ...props
}: BentoGridProps) {
  return (
    <div className={`bento-grid ${className}`} {...props}>
      {children}
    </div>
  );
}

interface BentoCardProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
}

export function BentoCard({
  children,
  className = '',
  ...props
}: BentoCardProps) {
  return (
    <article className={`bento-card ${className}`} {...props}>
      {children}
    </article>
  );
}
