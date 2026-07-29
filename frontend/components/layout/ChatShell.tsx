"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import type { Message, Followup, Commitment } from "@/types";
import { AGENTS, emptyAgentState } from "@/types";
import type { AgentState } from "@/types";
import { fetchConversations, fetchMessages, fetchFollowups, sendMessage, deleteConversation, uploadFile, dismissFollowup, resolveCommitment } from "@/lib/api";
import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";

type Props = {
  userId: string;
  username: string;
};

export default function ChatShell({ userId, username }: Props) {
  const [selectedAgentId, setSelectedAgentId] = useState("general");
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>({
    general: emptyAgentState(), bridger: emptyAgentState(),
    vibber: emptyAgentState(), inspirer: emptyAgentState(),
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [showFollowups, setShowFollowups] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedCode, setUploadedCode] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);

  const selectedAgent = AGENTS.find(a => a.id === selectedAgentId)!;
  const agentState = agentStates[selectedAgentId];

  // Load conversations when agent changes
  useEffect(() => {
    fetchConversations(userId, selectedAgentId).then(conversations => {
      setAgentStates(prev => ({ ...prev, [selectedAgentId]: { ...prev[selectedAgentId], conversations } }));
    });
  }, [userId, selectedAgentId]);

  // Poll follow-ups
  useEffect(() => {
    const poll = async () => {
      try {
        const data = await fetchFollowups(userId);
        setFollowups(data.followups);
        setCommitments(data.commitments);
      } catch { /* ignore */ }
    };
    poll();
    const id = setInterval(poll, 30000);
    return () => clearInterval(id);
  }, [userId]);

  const updateAgentState = (id: string, patch: Partial<AgentState>) =>
    setAgentStates(prev => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  const handleSelectConversation = async (agentId: string, convId: string) => {
    try {
      const messages = await fetchMessages(userId, convId);
      updateAgentState(agentId, {
        messages: messages.map(m => ({ role: m.role as "user" | "assistant", content: m.content })),
        activeConvId: convId,
      });
    } catch { /* ignore */ }
  };

  const handleNewConversation = () => {
    updateAgentState(selectedAgentId, { messages: [], activeConvId: null });
    setInput("");
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteConversation(convId);
      const cur = agentStates[selectedAgentId];
      const updated = cur.conversations.filter(c => c.id !== convId);
      const patch: Partial<AgentState> = { conversations: updated };
      if (cur.activeConvId === convId) { patch.messages = []; patch.activeConvId = null; }
      updateAgentState(selectedAgentId, patch);
    } catch { /* ignore */ }
  };

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const clean = text.replace(/[#*`_~>]/g, "").replace(/\n+/g, " ").trim();
    if (!clean) return;
    const utt = new SpeechSynthesisUtterance(clean);
    utt.rate = 0.92; utt.pitch = 1.0; utt.lang = "en-US";
    utt.onstart = () => setSpeaking(true);
    utt.onend = () => setSpeaking(false);
    utt.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utt);
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const data = await uploadFile(file);
      setUploadedCode(data.content);
      setUploadedFilename(data.filename);
      setInput(`Analyze this code: ${data.filename}`);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Upload failed.");
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    const cur = agentStates[selectedAgentId];
    const updatedMessages = [...cur.messages, userMsg];
    updateAgentState(selectedAgentId, { messages: updatedMessages, activeConvId: cur.activeConvId });
    setInput("");
    setLoading(true);
    try {
      const res = await sendMessage({
        message: userMsg.content, user_id: userId, agent_type: selectedAgentId,
        conversation_id: cur.activeConvId || undefined, code_context: uploadedCode || undefined,
      });
      const assistantMsg: Message = { role: "assistant", content: res.response || "No response." };
      if (selectedAgentId === "bridger" && ttsEnabled)
        setTimeout(() => speak(res.response || ""), 300);
      const newId = res.conversation_id || cur.activeConvId;
      updateAgentState(selectedAgentId, {
        messages: [...updatedMessages, assistantMsg],
        activeConvId: newId || null,
      });
      fetchConversations(userId, selectedAgentId).then(conversations => {
        updateAgentState(selectedAgentId, { conversations });
      });
    } catch {
      updateAgentState(selectedAgentId, {
        messages: [...updatedMessages, { role: "assistant", content: "Connection error. Check that the backend is running." }],
      });
    } finally { setLoading(false); setUploadedCode(null); setUploadedFilename(null); }
  };

  const handleDismissFollowup = async (id: string) => {
    try { await dismissFollowup(id); setFollowups(p => p.filter(f => f.id !== id)); } catch { /* ignore */ }
  };

  const handleResolveCommitment = async (id: string) => {
    try { await resolveCommitment(id); setCommitments(p => p.filter(c => c.id !== id)); } catch { /* ignore */ }
  };

  const totalDue = followups.length + commitments.length;

  const followupCounts: Record<string, number> = {};
  for (const agent of AGENTS) {
    followupCounts[agent.id] = followups.filter(f => f.agent_type === agent.id).length;
  }
  followupCounts.inspirer = (followupCounts.inspirer || 0) + commitments.length;

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-radial">
      <input
        ref={fileInputRef}
        type="file"
        accept=".py,.js,.ts,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.html,.css,.json,.yaml,.sh,.txt,.md"
        onChange={handleFileUpload}
        className="hidden"
      />

      {sidebarOpen && (
        <Sidebar
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          agentStates={agentStates}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          username={username}
          followupCounts={followupCounts}
        />
      )}

      <div className="flex flex-col flex-1 min-w-0">
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(o => !o)}
          agent={selectedAgent}
          totalDue={totalDue}
          showFollowups={showFollowups}
          onToggleFollowups={() => setShowFollowups(o => !o)}
          followups={followups}
          commitments={commitments}
          onDismissFollowup={handleDismissFollowup}
          onResolveCommitment={handleResolveCommitment}
          selectedAgentId={selectedAgentId}
          ttsEnabled={ttsEnabled}
          onToggleTts={() => setTtsEnabled(p => !p)}
          speaking={speaking}
          onStopSpeaking={() => { window.speechSynthesis.cancel(); setSpeaking(false); }}
        />

        <div className="flex-1 flex overflow-hidden">
          <main className="flex-1 flex flex-col overflow-hidden">
            <ChatMessages messages={agentState.messages} loading={loading} agent={selectedAgent} />
            <ChatInput
              input={input}
              setInput={setInput}
              loading={loading}
              agent={selectedAgent}
              onSend={handleSend}
              onFileClick={() => fileInputRef.current?.click()}
              uploadedFilename={uploadedFilename}
              onClearUpload={() => { setUploadedCode(null); setUploadedFilename(null); setInput(""); }}
            />
          </main>
        </div>
      </div>
    </div>
  );
}
