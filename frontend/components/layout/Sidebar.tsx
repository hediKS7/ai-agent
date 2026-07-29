"use client";
import { useState } from "react";
import { AGENTS } from "@/types";
import type { AgentState, Agent as AgentType } from "@/types";

type Props = {
  selectedAgentId: string;
  onSelectAgent: (id: string) => void;
  agentStates: Record<string, AgentState>;
  onSelectConversation: (agentId: string, convId: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (convId: string, e: React.MouseEvent) => void;
  username: string;
  followupCounts: Record<string, number>;
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

export default function Sidebar({
  selectedAgentId, onSelectAgent, agentStates, onSelectConversation,
  onNewConversation, onDeleteConversation, username, followupCounts,
}: Props) {
  const [search, setSearch] = useState("");
  const agentState = agentStates[selectedAgentId];

  const filteredConversations = agentState.conversations.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <aside className="w-56 shrink-0 flex flex-col glass-sidebar z-10">
      <div className="px-4 py-4 border-b border-[#27272a]/50 flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#6366F1] to-[#8B5CF6]" />
        <div>
          <p className="text-sm font-semibold text-[#f0f0f5]">AI Agent</p>
          <p className="text-[8px] font-mono text-[#52525b] tracking-widest">{username}</p>
        </div>
      </div>

      {/* Agent tabs */}
      <div className="px-3 py-2 space-y-0.5">
        {AGENTS.map((agent) => {
          const cnt = followupCounts[agent.id] || 0;
          return (
            <button
              key={agent.id}
              onClick={() => onSelectAgent(agent.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
                selectedAgentId === agent.id
                  ? "text-[#09090b] shadow-sm"
                  : "text-[#71717a] hover:text-[#f0f0f5] hover:bg-[#18181b]/50"
              }`}
              style={selectedAgentId === agent.id ? { backgroundColor: agent.color } : {}}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  selectedAgentId === agent.id ? "" : "opacity-60"
                }`}
                style={{ backgroundColor: selectedAgentId === agent.id ? "#09090b" : agent.color }}
              />
              <span className="flex-1 truncate">{agent.name}</span>
              {cnt > 0 && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-[#F59E0B] text-[#09090b] font-bold">
                  {cnt}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* New conversation */}
      <div className="px-3 py-1">
        <button
          onClick={onNewConversation}
          className="w-full text-left px-3 py-1.5 text-xs text-[#52525b] hover:text-[#f0f0f5] hover:bg-[#18181b]/50 rounded-lg transition-colors"
        >
          + New conversation
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-1">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search..."
          className="w-full bg-[#18181b]/60 border border-[#27272a] rounded-lg px-3 py-1.5 text-xs text-[#f0f0f5] outline-none placeholder:text-[#52525b] focus:border-[#52525b] transition-colors"
        />
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-3 space-y-0.5 pb-4">
        {filteredConversations.length === 0 && (
          <p className="text-[10px] text-[#3f3f46] px-3 py-2">
            {search ? "No matches" : "No conversations yet"}
          </p>
        )}
        {filteredConversations.map((conv) => (
          <div
            key={conv.id}
            onClick={() => onSelectConversation(selectedAgentId, conv.id)}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors text-xs ${
              agentState.activeConvId === conv.id
                ? "bg-[#18181b]/70 text-[#f0f0f5]"
                : "text-[#71717a] hover:bg-[#18181b]/50 hover:text-[#f0f0f5]"
            }`}
          >
            <span className="flex-1 truncate">{conv.title}</span>
            <span className="text-[9px] text-[#52525b] shrink-0">{formatDate(conv.updated_at)}</span>
            <button
              onClick={e => onDeleteConversation(conv.id, e)}
              className="opacity-0 group-hover:opacity-100 text-[#52525b] hover:text-red-400 text-xs shrink-0"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
