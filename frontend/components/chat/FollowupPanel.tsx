import type { Followup, Commitment } from "@/types";

type Props = {
  followups: Followup[];
  commitments: Commitment[];
  onDismiss: (id: string) => void;
  onResolve: (id: string) => void;
  onClose: () => void;
};

export default function FollowupPanel({ followups, commitments, onDismiss, onResolve, onClose }: Props) {
  return (
    <div className="absolute right-0 top-8 w-72 glass-card rounded-xl shadow-2xl z-50 p-3 space-y-2 max-h-80 overflow-y-auto animate-fade-in">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[9px] font-mono text-[#52525b] uppercase tracking-widest">Follow-ups</p>
        <button onClick={onClose} className="text-[#52525b] hover:text-[#f0f0f5] text-xs">✕</button>
      </div>
      {followups.length === 0 && commitments.length === 0 && (
        <p className="text-xs text-[#52525b] py-2">Nothing due right now.</p>
      )}
      {followups.map((f) => (
        <div key={f.id} className="bg-[#09090b] rounded-lg px-3 py-2 border border-[#27272a]">
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            <span className={`font-mono text-[9px] uppercase mr-1 ${
              f.agent_type === "bridger" ? "text-[#8B5CF6]"
                : f.agent_type === "vibber" ? "text-[#10B981]"
                : "text-[#F59E0B]"
            }`}>
              {f.followup_type === "intro_checkin" ? "Intro" : f.followup_type === "relationship_checkin" ? "Check-in" : f.agent_type}
            </span>
            {!!f.context?.contact_name && <span className="font-medium text-[#f0f0f5]">{String(f.context.contact_name)}</span>}
            {f.context?.context ? String(f.context.context) : ""}
          </p>
          <button onClick={() => onDismiss(f.id)}
            className="mt-1 text-[9px] font-mono text-[#52525b] hover:text-[#f0f0f5] transition-colors">dismiss</button>
        </div>
      ))}
      {commitments.length > 0 && (
        <>
          <p className="text-[9px] font-mono text-[#52525b] uppercase tracking-widest pt-1">Overdue commitments</p>
          {commitments.map((c) => (
            <div key={c.id} className="bg-[#09090b] rounded-lg px-3 py-2 border border-[#27272a]">
              <p className="text-xs text-[#a1a1aa]">{c.description}</p>
              <p className="text-[9px] text-[#52525b] mt-0.5">deadline: {new Date(c.deadline).toLocaleDateString()}</p>
              <button onClick={() => onResolve(c.id)}
                className="mt-1 text-[9px] font-mono text-[#10B981] hover:text-[#f0f0f5] transition-colors">mark done</button>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
