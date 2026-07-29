"use client";

import { AGENTS } from "@/lib/agents";
import type { AgentId, Conversation } from "@/lib/types";

type SidebarProps = {
  open: boolean;
  selectedAgentId: AgentId;
  conversations: Conversation[];
  activeConversationId: string | null;
  dueCount: (agentId: AgentId) => number;
  onClose: () => void;
  onSelectAgent: (id: AgentId) => void;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
};

export function Sidebar(props: SidebarProps) {
  const { open, selectedAgentId, conversations, activeConversationId, dueCount, onClose, onSelectAgent, onNewConversation, onSelectConversation, onDeleteConversation } = props;
  if (!open) return null;
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand__mark"><i /><i /><i /></span>
        <span><strong>nexus</strong><small>intelligence workspace</small></span>
        <button className="sidebar__close" onClick={onClose} aria-label="Close sidebar">&times;</button>
      </div>
      <div className="sidebar__section">
        <p className="sidebar__eyebrow">Your spaces</p>
        {AGENTS.map((agent) => {
          const isActive = agent.id === selectedAgentId;
          const count = dueCount(agent.id);
          return <button key={agent.id} className={"agent-item " + (isActive ? "agent-item--active" : "")} style={isActive ? { "--agent": agent.color } as React.CSSProperties : undefined} onClick={() => onSelectAgent(agent.id)}>
            <span className="agent-item__dot" style={{ backgroundColor: agent.color }} />
            <span><strong>{agent.name}</strong><small>{agent.descriptor}</small></span>
            {count > 0 && <b>{count}</b>}
          </button>;
        })}
      </div>
      <div className="sidebar__history-head"><p className="sidebar__eyebrow">Recent conversations</p><button onClick={onNewConversation}>New chat <span>+</span></button></div>
      <nav className="conversation-list" aria-label="Conversation history">
        {conversations.length ? conversations.map((conversation) => <div key={conversation.id} className={"conversation " + (activeConversationId === conversation.id ? "conversation--active" : "")}>
          <button onClick={() => onSelectConversation(conversation.id)}><span>{conversation.title}</span><small>{new Date(conversation.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></button>
          <button className="conversation__delete" onClick={() => onDeleteConversation(conversation.id)} aria-label={"Delete " + conversation.title}>&times;</button>
        </div>) : <p className="sidebar__empty">Your conversations will appear here.</p>}
      </nav>
      <div className="sidebar__footer"><span className="status-dot" /> All systems operational</div>
    </aside>
  );
}
