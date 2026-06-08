import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Card({ title, className, children }: CardProps) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white shadow-card p-5 ${className ?? ""}`}
    >
      {title ? <h3 className="text-base font-semibold mb-3 text-ink-900">{title}</h3> : null}
      {children}
    </section>
  );
}
