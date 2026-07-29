"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import type { Message, Followup, Commitment } from "@/types";
import { AGENTS, emptyAgentState } from "@/types";
import type { AgentState } from "@/types";
import { fetchConversations, fetchMessages, fetchFollowups, deleteConversation, uploadFile, dismissFollowup, resolveCommitment } from "@/lib/api";
import { useChatStream } from "@/lib/useChatStream";
import Toast from "@/components/ui/Toast";
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
  const [streamingText, setStreamingText] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [showFollowups, setShowFollowups] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedCode, setUploadedCode] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" | "info" } | null>(null);
  const streamingTextRef = useRef("");
  const convIdRef = useRef<string | null>(null);

  const { stream, stop } = useChatStream();
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
    setMobileSidebarOpen(false);
    try {
      const messages = await fetchMessages(userId, convId);
      updateAgentState(agentId, {
        messages: messages.map(m => ({ role: m.role as "user" | "assistant", content: m.content })),
        activeConvId: convId,
      });
    } catch { /* ignore */ }
  };

  const handleNewConversation = () => {
    stop();
    setMobileSidebarOpen(false);
    updateAgentState(selectedAgentId, { messages: [], activeConvId: null });
    setStreamingText("");
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

  const handleFileUpload = async (file: File) => {
    try {
      const data = await uploadFile(file);
      setUploadedCode(data.content);
      setUploadedFilename(data.filename);
      setInput(`Analyze this code: ${data.filename}`);
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || "Upload failed.", type: "error" });
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await handleFileUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileDrop = async (file: File) => {
    await handleFileUpload(file);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: "user", content: input };
    const cur = agentStates[selectedAgentId];
    const updatedMessages = [...cur.messages, userMsg];
    updateAgentState(selectedAgentId, { messages: updatedMessages, activeConvId: cur.activeConvId });
    setInput("");
    setLoading(true);
    setStreamingText("");
    streamingTextRef.current = "";
    convIdRef.current = null;

    stream({
      message: userMsg.content, user_id: userId, agent_type: selectedAgentId,
      conversation_id: cur.activeConvId || undefined, code_context: uploadedCode || undefined,
    }, {
      onToken: (token, convId) => {
        streamingTextRef.current = token;
        setStreamingText(token);
        if (convId && !convIdRef.current) {
          convIdRef.current = convId;
          updateAgentState(selectedAgentId, { activeConvId: convId });
        }
      },
      onDone: (convId) => {
        const finalText = streamingTextRef.current;
        setLoading(false);
        setUploadedCode(null);
        setUploadedFilename(null);

        setAgentStates(prev => {
          const cur = prev[selectedAgentId];
          const assistantMsg: Message = { role: "assistant", content: finalText };
          return { ...prev, [selectedAgentId]: { ...cur, messages: [...cur.messages, assistantMsg], activeConvId: convId || cur.activeConvId } };
        });
        setStreamingText("");

        if (selectedAgentId === "bridger" && ttsEnabled && finalText) {
          setTimeout(() => speak(finalText), 300);
        }

        fetchConversations(userId, selectedAgentId).then(conversations => {
          updateAgentState(selectedAgentId, { conversations });
        });
      },
      onError: (error) => {
        setLoading(false);
        setStreamingText("");
        setAgentStates(prev => {
          const cur = prev[selectedAgentId];
          return { ...prev, [selectedAgentId]: { ...cur, messages: [...cur.messages, { role: "assistant" as const, content: `Error: ${error}` }] } };
        });
        setToast({ message: error, type: "error" });
      },
    });
  };

  const handleDismissFollowup = async (id: string) => {
    try { await dismissFollowup(id); setFollowups(p => p.filter(f => f.id !== id)); } catch { /* ignore */ }
  };

  const handleResolveCommitment = async (id: string) => {
    try { await resolveCommitment(id); setCommitments(p => p.filter(c => c.id !== id)); } catch { /* ignore */ }
  };

  const handleToggleSidebar = () => {
    if (window.innerWidth < 768) {
      setMobileSidebarOpen(o => !o);
    } else {
      setSidebarOpen(o => !o);
    }
  };

  const totalDue = followups.length + commitments.length;

  const followupCounts: Record<string, number> = {};
  for (const agent of AGENTS) {
    followupCounts[agent.id] = followups.filter(f => f.agent_type === agent.id).length;
  }
  followupCounts.inspirer = (followupCounts.inspirer || 0) + commitments.length;

  const displayedMessages = streamingText
    ? [...agentState.messages, { role: "assistant" as const, content: streamingText }]
    : agentState.messages;

  const isStreaming = loading && !!streamingText;

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-radial">
      <input
        ref={fileInputRef}
        type="file"
        accept=".py,.js,.ts,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.html,.css,.json,.yaml,.sh,.txt,.md"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Desktop sidebar */}
      {sidebarOpen && (
        <div className="hidden md:flex">
          <Sidebar
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
            agentStates={agentStates}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            onDeleteConversation={handleDeleteConversation}
            username={username}
            followupCounts={followupCounts}
            mobileOpen={false}
            onMobileClose={() => setMobileSidebarOpen(false)}
          />
        </div>
      )}

      {/* Mobile sidebar */}
      <Sidebar
        selectedAgentId={selectedAgentId}
        onSelectAgent={setSelectedAgentId}
        agentStates={agentStates}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        username={username}
        followupCounts={followupCounts}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <Header
          sidebarOpen={sidebarOpen || mobileSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
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
            <ChatMessages messages={displayedMessages} loading={loading && !streamingText} streaming={isStreaming} agent={selectedAgent} />
            <ChatInput
              input={input}
              setInput={setInput}
              loading={loading}
              agent={selectedAgent}
              onSend={handleSend}
              onFileClick={() => fileInputRef.current?.click()}
              onFileDrop={handleFileDrop}
              uploadedFilename={uploadedFilename}
              onClearUpload={() => { setUploadedCode(null); setUploadedFilename(null); setInput(""); }}
            />
          </main>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
