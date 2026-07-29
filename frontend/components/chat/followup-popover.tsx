"use client";

import type { Commitment, Followup } from "@/lib/types";

export function FollowupPopover({ followups, commitments, onDismiss, onResolve, onClose }: { followups: Followup[]; commitments: Commitment[]; onDismiss: (id: string) => void; onResolve: (id: string) => void; onClose: () => void }) {
  return <section className="reminders" aria-label="Due reminders"><header><div><p>Attention queue</p><span>Things worth returning to</span></div><button onClick={onClose} aria-label="Close reminders">×</button></header>{followups.length === 0 && commitments.length === 0 ? <p className="reminders__empty">You’re all caught up.</p> : <div className="reminders__list">{followups.map((item) => <article key={item.id}><span className="reminder__kind">{item.followup_type.replaceAll("_", " ")}</span><p>{item.context?.contact_name && <strong>{item.context.contact_name} · </strong>}{item.context?.context || "A follow-up is due."}</p><button onClick={() => onDismiss(item.id)}>Dismiss</button></article>)}{commitments.map((item) => <article key={item.id}><span className="reminder__kind reminder__kind--amber">Commitment</span><p>{item.description}</p><small>Due {new Date(item.deadline).toLocaleDateString()}</small><button onClick={() => onResolve(item.id)}>Mark complete</button></article>)}</div>}</section>;
}
