import type { Agent } from "@/types";

type Props = { agent: Agent };

export default function EmptyState({ agent }: Props) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center gap-3 animate-fade-in">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ backgroundColor: agent.color + "20" }}
      >
        <div className="w-5 h-5 rounded-md" style={{ backgroundColor: agent.color }} />
      </div>
      <p className="text-base font-semibold text-[#f0f0f5]">{agent.name}</p>
      <p className="text-xs text-[#52525b] max-w-xs">{agent.placeholder}</p>
    </div>
  );
}
