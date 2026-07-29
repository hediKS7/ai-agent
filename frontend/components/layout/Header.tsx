"use client";
import type { Agent } from "@/types";
import FollowupPanel from "@/components/chat/FollowupPanel";
import type { Followup, Commitment } from "@/types";

type Props = {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  agent: Agent;
  totalDue: number;
  showFollowups: boolean;
  onToggleFollowups: () => void;
  followups: Followup[];
  commitments: Commitment[];
  onDismissFollowup: (id: string) => void;
  onResolveCommitment: (id: string) => void;
  selectedAgentId: string;
  ttsEnabled: boolean;
  onToggleTts: () => void;
  speaking: boolean;
  onStopSpeaking: () => void;
};

export default function Header({
  sidebarOpen, onToggleSidebar, agent, totalDue, showFollowups,
  onToggleFollowups, followups, commitments, onDismissFollowup, onResolveCommitment,
  selectedAgentId, ttsEnabled, onToggleTts, speaking, onStopSpeaking,
}: Props) {
  return (
    <header className="h-12 border-b border-[#27272a]/50 px-4 flex items-center gap-3 shrink-0 bg-[#0a0a0f]/40 backdrop-blur-md">
      <button
        onClick={onToggleSidebar}
        className="text-[#52525b] hover:text-[#f0f0f5] transition-colors text-sm w-5"
      >
        {sidebarOpen ? "←" : "→"}
      </button>
      <div className="w-2.5 h-2.5 rounded-full ring-2 ring-[#27272a]/30" style={{ backgroundColor: agent.color }} />
      <span className="text-sm font-semibold">{agent.name}</span>
      <div className="ml-auto flex items-center gap-2">
        {totalDue > 0 && (
          <div className="relative">
            <button
              onClick={onToggleFollowups}
              className="text-[10px] font-mono px-2 py-1 rounded-lg border border-[#27272a] text-[#F59E0B] hover:text-[#f0f0f5] transition-colors"
            >
              {totalDue} due
            </button>
            {showFollowups && (
              <FollowupPanel
                followups={followups}
                commitments={commitments}
                onDismiss={onDismissFollowup}
                onResolve={onResolveCommitment}
                onClose={onToggleFollowups}
              />
            )}
          </div>
        )}
        {selectedAgentId === "bridger" && (
          <div className="flex items-center gap-1.5">
            {speaking && (
              <button
                onClick={onStopSpeaking}
                className="text-[10px] font-mono text-[#8B5CF6] border border-[#8B5CF6] px-2 py-0.5 rounded-lg animate-pulse"
              >
                stop
              </button>
            )}
            <button
              onClick={onToggleTts}
              className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border transition-colors ${
                ttsEnabled
                  ? "text-[#09090b] border-[#8B5CF6]"
                  : "text-[#52525b] border-[#27272a] hover:text-[#f0f0f5]"
              }`}
              style={ttsEnabled ? { backgroundColor: "#8B5CF6" } : {}}
            >
              {ttsEnabled ? "voice on" : "voice off"}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
