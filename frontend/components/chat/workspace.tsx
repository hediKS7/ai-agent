"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getAgent } from "@/lib/agents";
import { api } from "@/lib/api";
import type { AgentId, AgentWorkspaceState, Commitment, Followup, Message } from "@/lib/types";
import { Composer } from "./composer";
import { FollowupPopover } from "./followup-popover";
import { MessageBubble } from "./message-bubble";
import { Sidebar } from "./sidebar";

const emptyWorkspace = (): AgentWorkspaceState => ({ conversations: [], activeConversationId: null, messages: [] });
const initialWorkspaces = (): Record<AgentId, AgentWorkspaceState> => ({ general: emptyWorkspace(), bridger: emptyWorkspace(), vibber: emptyWorkspace(), inspirer: emptyWorkspace() });

export function ChatWorkspace({ userId, username, onLogout }: { userId: string; username: string; onLogout: () => void }) {
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId>("general");
  const [workspaces, setWorkspaces] = useState<Record<AgentId, AgentWorkspaceState>>(initialWorkspaces);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachment, setAttachment] = useState<{ filename: string; content: string } | null>(null);
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [remindersOpen, setRemindersOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const workspace = workspaces[selectedAgentId];
  const agent = getAgent(selectedAgentId);

  const patchWorkspace = useCallback((agentId: AgentId, patch: Partial<AgentWorkspaceState>) => {
    setWorkspaces((current) => ({ ...current, [agentId]: { ...current[agentId], ...patch } }));
  }, []);
  const loadConversations = useCallback(async (agentId: AgentId) => {
    try { patchWorkspace(agentId, { conversations: await api.conversations(userId, agentId) }); }
    catch { setError("Could not load conversations. Check that the API is available."); }
  }, [patchWorkspace, userId]);
  const refreshDueItems = useCallback(async () => {
    try { const due = await api.dueItems(userId); setFollowups(due.followups); setCommitments(due.commitments); }
    catch { /* reminders must not interrupt chat */ }
  }, [userId]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadConversations(selectedAgentId), 0);
    return () => window.clearTimeout(initialLoad);
  }, [loadConversations, selectedAgentId]);
  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refreshDueItems(), 0);
    const timer = window.setInterval(() => void refreshDueItems(), 30_000);
    return () => { window.clearTimeout(initialRefresh); window.clearInterval(timer); };
  }, [refreshDueItems]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [workspace.messages, loading]);
  useEffect(() => { if (!userMenuOpen) return; const handler = (event: MouseEvent) => { if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) setUserMenuOpen(false); }; window.setTimeout(() => document.addEventListener("click", handler), 0); return () => document.removeEventListener("click", handler); }, [userMenuOpen]);

  const selectConversation = async (conversationId: string) => {
    try { patchWorkspace(selectedAgentId, { activeConversationId: conversationId, messages: await api.messages(userId, conversationId) }); setError(null); }
    catch { setError("Could not open this conversation. Please try again."); }
  };
  const newConversation = () => { patchWorkspace(selectedAgentId, { activeConversationId: null, messages: [] }); setAttachment(null); setError(null); };
  const deleteConversation = async (conversationId: string) => {
    try {
      await api.deleteConversation(conversationId);
      const current = workspaces[selectedAgentId];
      patchWorkspace(selectedAgentId, { conversations: current.conversations.filter((item) => item.id !== conversationId), ...(current.activeConversationId === conversationId ? { activeConversationId: null, messages: [] } : {}) });
    } catch { setError("Could not delete this conversation. Please try again."); }
  };
  const attachFile = async (file: File) => {
    try { setAttachment(await api.upload(file)); setError(null); }
    catch { setError("That file could not be uploaded. Use a supported UTF-8 code or text file."); }
  };
  const copy = async (content: string) => {
    try { await navigator.clipboard.writeText(content); }
    catch { setError("Copy is not available in this browser."); }
  };
  const speak = (content: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(content.replace(/[#*_~>]/g, " ").replace(/\s+/g, " ")));
  };
  const send = async (content: string) => {
    const agentId = selectedAgentId;
    const current = workspaces[agentId];
    const userMessage: Message = { role: "user", content };
    patchWorkspace(agentId, { messages: [...current.messages, userMessage] });
    setLoading(true); setError(null);
    try {
      const response = await api.sendChat({ message: content, userId, agentType: agentId, conversationId: current.activeConversationId ?? undefined, codeContext: attachment?.content });
      patchWorkspace(agentId, { messages: [...current.messages, userMessage, { role: "assistant", content: response.response || "No response received." }], activeConversationId: response.conversation_id ?? current.activeConversationId });
      setAttachment(null);
      await loadConversations(agentId);
      if (agentId === "bridger" && ttsEnabled) speak(response.response);
    } catch {
      patchWorkspace(agentId, { messages: [...current.messages, userMessage, { role: "assistant", content: "I could not reach the AI service. Check that the backend is running, then try again." }] });
      setError("Message delivery failed.");
    } finally { setLoading(false); }
  };
  const dueCount = useMemo(() => (agentId: AgentId) => followups.filter((item) => item.agent_type === agentId).length + (agentId === "inspirer" ? commitments.length : 0), [commitments.length, followups]);
  const totalDue = followups.length + commitments.length;

  const body = <section className="chat-shell">
    <div className="conversation-pane">
      {workspace.messages.length === 0 && !loading ? <section className="welcome"><span className="welcome__orb" /><p className="eyebrow">{agent.name} space</p><h1>{agent.descriptor}</h1><p>Start with a question, a rough thought, or a piece of code. This conversation will stay in its own focused space.</p><div className="prompt-chips">{["Help me think this through", "Give me a clear next step", "What should I explore?"].map((prompt) => <button key={prompt} onClick={() => void send(prompt)}>{prompt}<span>&rarr;</span></button>)}</div></section> : <div className="messages">{workspace.messages.map((message, index) => <MessageBubble key={message.role + "-" + index + "-" + message.content.slice(0, 12)} message={message} agent={agent} onCopy={(content) => void copy(content)} />)}{loading && <div className="thinking"><span /><span /><span /> {agent.name} is thinking</div>}<div ref={bottomRef} /></div>}
    </div>
    {error && <div className="error-banner" role="status"><span>!</span>{error}<button onClick={() => setError(null)} aria-label="Dismiss error">&times;</button></div>}
    <Composer placeholder={agent.placeholder} accent={agent.color} disabled={loading} attachment={attachment} onAttach={attachFile} onRemoveAttachment={() => setAttachment(null)} onSend={(message) => void send(message)} />
  </section>;

  return <main className="workspace" style={{ "--accent": agent.color } as React.CSSProperties}>
    <header className="topbar">
      <div className="topbar__left"><button className="topbar__brand" onClick={() => setSidebarOpen((prev) => !prev)} aria-label="Toggle sidebar"><span className="brand__mark"><i /><i /><i /></span><strong>RICHOUT</strong></button><span className="topbar__agent-dot" /><div><p>{agent.name}</p><span>{agent.descriptor}</span></div></div>
      <div className="topbar__actions">
        {selectedAgentId === "bridger" && <button className={"voice-toggle " + (ttsEnabled ? "voice-toggle--on" : "")} onClick={() => setTtsEnabled((enabled) => !enabled)}>{ttsEnabled ? "Voice on" : "Voice off"}</button>}
        <div className="reminders-anchor"><button className="reminder-button" onClick={() => setRemindersOpen((open) => !open)}>Focus {totalDue > 0 && <b>{totalDue}</b>}</button>{remindersOpen && <FollowupPopover followups={followups} commitments={commitments} onClose={() => setRemindersOpen(false)} onDismiss={(id) => { void api.dismissFollowup(id); setFollowups((items) => items.filter((item) => item.id !== id)); }} onResolve={(id) => { void api.resolveCommitment(id); setCommitments((items) => items.filter((item) => item.id !== id)); }} />}</div>
        <div className="user-anchor" ref={userMenuRef}><button className="user-chip" onClick={() => setUserMenuOpen((prev) => !prev)} title={username} aria-label="User menu">{username.slice(0, 1).toUpperCase()}</button>{userMenuOpen && <div className="user-menu"><div className="user-menu__header"><strong>{username}</strong></div><button className="user-menu__item" onClick={() => setUserMenuOpen(false)}>Profile settings</button><button className="user-menu__item user-menu__item--danger" onClick={() => { setUserMenuOpen(false); onLogout(); }}>Sign out</button></div>}</div>
      </div>
    </header>
    <div className="workspace__body">
      <Sidebar open={sidebarOpen} selectedAgentId={selectedAgentId} conversations={workspace.conversations} activeConversationId={workspace.activeConversationId} dueCount={dueCount} onToggle={() => setSidebarOpen((prev) => !prev)} onSelectAgent={(id) => { setSelectedAgentId(id); setError(null); }} onNewConversation={newConversation} onSelectConversation={selectConversation} onDeleteConversation={deleteConversation} />
      {body}
    </div>
  </main>;
}
