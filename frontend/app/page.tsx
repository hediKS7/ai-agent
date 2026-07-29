"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const API = "";

const AGENTS = [
  { id: "general",  name: "General",      color: "#6366F1", placeholder: "Ask anything..." },
  { id: "bridger",  name: "Bridger",      color: "#8B5CF6", placeholder: "Who do you want to connect with?" },
  { id: "vibber",   name: "Vibber",       color: "#10B981", placeholder: "How are you feeling today?" },
  { id: "inspirer", name: "Inspirer",     color: "#F59E0B", placeholder: "What are you building?" },
];

type Message = { role: "user" | "assistant"; content: string };
type Conversation = { id: string; title: string; updated_at: string };
type AgentState = {
  conversations: Conversation[];
  activeConvId: string | null;
  messages: Message[];
};

const emptyAgentState = (): AgentState => ({
  conversations: [], activeConvId: null, messages: [],
});

// ── Shimmer Skeleton ────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="glass-card rounded-2xl rounded-bl-sm px-5 py-4 w-72">
        <div className="skeleton-line w-16" />
        <div className="skeleton-line w-full" />
        <div className="skeleton-line w-3/4" />
        <div className="skeleton-line w-1/2" />
      </div>
    </div>
  );
}

// ── Message Bubble ─────────────────────────────────────────────────────

function MessageBubble({ msg, agentColor, agentName, index }: {
  msg: Message; agentColor: string; agentName: string; index: number;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-slide-up`}
      style={{ animationDelay: `${index * 50}ms` }}>
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm ${
        isUser
          ? "rounded-br-sm text-[#09090b] font-medium"
          : "rounded-bl-sm glass-card"
      }`} style={isUser ? { backgroundColor: agentColor } : {}}>
        {!isUser && (
          <p className="text-[9px] font-mono tracking-widest mb-1.5 uppercase opacity-60"
            style={{ color: agentColor }}>{agentName}</p>
        )}
        {!isUser ? (
          <div className="markdown-body leading-relaxed">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ) : (
          <span className="text-sm leading-relaxed">{msg.content}</span>
        )}
      </div>
    </div>
  );
}

// ── Follow-up Panel ────────────────────────────────────────────────────

function FollowupPanel({ followups, commitments, onDismiss, onResolve, onClose }: {
  followups: any[]; commitments: any[]; onDismiss: (id: string) => void;
  onResolve: (id: string) => void; onClose: () => void;
}) {
  return (
    <div className="absolute right-0 top-8 w-72 glass-card rounded-xl shadow-2xl z-50 p-3 space-y-2 max-h-80 overflow-y-auto animate-fade-in">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[9px] font-mono text-[#52525b] uppercase tracking-widest">Follow-ups</p>
        <button onClick={onClose} className="text-[#52525b] hover:text-[#f0f0f5] text-xs">✕</button>
      </div>
      {followups.length === 0 && commitments.length === 0 && (
        <p className="text-xs text-[#52525b] py-2">Nothing due right now.</p>
      )}
      {followups.map((f: any) => (
        <div key={f.id} className="bg-[#09090b] rounded-lg px-3 py-2 border border-[#27272a]">
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            <span className={`font-mono text-[9px] uppercase mr-1 ${
              f.agent_type === "bridger" ? "text-[#8B5CF6]"
                : f.agent_type === "vibber" ? "text-[#10B981]"
                : "text-[#F59E0B]"
            }`}>
              {f.followup_type === "intro_checkin" ? "Intro" : f.followup_type === "relationship_checkin" ? "Check-in" : f.agent_type}
            </span>
            {f.context?.contact_name && <span className="font-medium text-[#f0f0f5]">{f.context.contact_name}</span>}
            {f.context?.context || ""}
          </p>
          <button onClick={() => onDismiss(f.id)}
            className="mt-1 text-[9px] font-mono text-[#52525b] hover:text-[#f0f0f5] transition-colors">dismiss</button>
        </div>
      ))}
      {commitments.length > 0 && (
        <>
          <p className="text-[9px] font-mono text-[#52525b] uppercase tracking-widest pt-1">Overdue commitments</p>
          {commitments.map((c: any) => (
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

// ── Main Chat ──────────────────────────────────────────────────────────

function ChatPage({ userId, username }: {
  userId: string; username: string;
}) {
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
  const [followups, setFollowups] = useState<any[]>([]);
  const [commitments, setCommitments] = useState<any[]>([]);
  const [showFollowups, setShowFollowups] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedCode, setUploadedCode] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);

  const selectedAgent = AGENTS.find(a => a.id === selectedAgentId)!;
  const agentState = agentStates[selectedAgentId];

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [agentStates, loading]);

  useEffect(() => { loadConversations(selectedAgentId); }, [selectedAgentId]);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await axios.get(`${API}/followups/${userId}`);
        setFollowups(res.data.followups || []);
        setCommitments(res.data.commitments || []);
      } catch {}
    };
    poll();
    const id = setInterval(poll, 30000);
    return () => clearInterval(id);
  }, [userId]);

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

  const updateAgentState = (id: string, patch: Partial<AgentState>) =>
    setAgentStates(prev => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  const loadConversations = async (agentId: string) => {
    try {
      const res = await axios.get(`${API}/chat/conversations/${userId}?agent_type=${agentId}`);
      updateAgentState(agentId, { conversations: res.data.conversations });
    } catch {}
  };

  const loadMessages = async (agentId: string, convId: string) => {
    try {
      const res = await axios.get(`${API}/chat/conversations/${userId}/${convId}/messages`);
      updateAgentState(agentId, {
        messages: res.data.messages.map((m: any) => ({ role: m.role, content: m.content })),
        activeConvId: convId,
      });
    } catch {}
  };

  const newConversation = () => {
    updateAgentState(selectedAgentId, { messages: [], activeConvId: null });
    setInput("");
  };

  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/chat/conversations/${convId}`);
      const cur = agentStates[selectedAgentId];
      const updated = cur.conversations.filter(c => c.id !== convId);
      const patch: Partial<AgentState> = { conversations: updated };
      if (cur.activeConvId === convId) { patch.messages = []; patch.activeConvId = null; }
      updateAgentState(selectedAgentId, patch);
    } catch {}
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await axios.post(`${API}/upload`, fd);
      setUploadedCode(res.data.content);
      setUploadedFilename(res.data.filename);
      setInput(`Analyze this code: ${res.data.filename}`);
    } catch (err: any) { alert(err.response?.data?.detail || "Upload failed."); }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    const cur = agentStates[selectedAgentId];
    updateAgentState(selectedAgentId, { messages: [...cur.messages, userMsg] });
    setInput("");
    setLoading(true);
    try {
      const res = await axios.post(`${API}/chat`, {
        message: userMsg.content, user_id: userId, agent_type: selectedAgentId,
        conversation_id: cur.activeConvId || undefined, code_context: uploadedCode || undefined,
      });
      const assistantMsg: Message = { role: "assistant", content: res.data.response || "No response." };
      if (selectedAgentId === "bridger" && ttsEnabled)
        setTimeout(() => speak(res.data.response || ""), 300);
      const newId = res.data.conversation_id || cur.activeConvId;
      updateAgentState(selectedAgentId, {
        messages: [...agentStates[selectedAgentId].messages, assistantMsg],
        activeConvId: newId || null,
      });
      await loadConversations(selectedAgentId);
    } catch {
      updateAgentState(selectedAgentId, {
        messages: [...agentStates[selectedAgentId].messages,
          { role: "assistant", content: "Connection error. Check that the backend is running." }]
      });
    } finally { setLoading(false); setUploadedCode(null); setUploadedFilename(null); }
  };

  const dismissFollowup = async (id: string) => {
    try { await axios.post(`${API}/followups/triggered`, { followup_id: id }); setFollowups(p => p.filter(f => f.id !== id)); } catch {}
  };
  const resolveCommitment = async (id: string) => {
    try { await axios.post(`${API}/followups/resolve-commitment`, { commitment_id: id }); setCommitments(p => p.filter(c => c.id !== id)); } catch {}
  };

  const totalDue = followups.length + commitments.length;

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-radial">
      {/* SIDEBAR */}
      {sidebarOpen && (
        <aside className="w-56 shrink-0 flex flex-col glass-sidebar z-10">
          <div className="px-4 py-4 border-b border-[#27272a]/50 flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#6366F1] to-[#8B5CF6]" />
            <div>
              <p className="text-sm font-semibold text-[#f0f0f5]">AI Agent</p>
              <p className="text-[8px] font-mono text-[#52525b] tracking-widest">{username}</p>
            </div>
          </div>
          <div className="px-3 py-2 space-y-0.5">
            {AGENTS.map(agent => {
              const cnt = followups.filter((f: any) => f.agent_type === agent.id).length + (agent.id === "inspirer" ? commitments.length : 0);
              return (
                <button key={agent.id} onClick={() => setSelectedAgentId(agent.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
                    selectedAgentId === agent.id
                      ? "text-[#09090b] shadow-sm" : "text-[#71717a] hover:text-[#f0f0f5] hover:bg-[#18181b]/50"
                  }`}
                  style={selectedAgentId === agent.id ? { backgroundColor: agent.color } : {}}>
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    selectedAgentId === agent.id ? "" : "opacity-60"
                  }`} style={{ backgroundColor: selectedAgentId === agent.id ? "#09090b" : agent.color }} />
                  <span className="flex-1 truncate">{agent.name}</span>
                  {cnt > 0 && (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-[#F59E0B] text-[#09090b] font-bold">{cnt}</span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="px-3 py-1">
            <button onClick={newConversation}
              className="w-full text-left px-3 py-1.5 text-xs text-[#52525b] hover:text-[#f0f0f5] hover:bg-[#18181b]/50 rounded-lg transition-colors">
              + New conversation
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-3 space-y-0.5 pb-4">
            {agentState.conversations.length === 0 && (
              <p className="text-[10px] text-[#3f3f46] px-3 py-2">No conversations yet</p>
            )}
            {agentState.conversations.map(conv => (
              <div key={conv.id} onClick={() => loadMessages(selectedAgentId, conv.id)}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors text-xs ${
                  agentState.activeConvId === conv.id
                    ? "bg-[#18181b]/70 text-[#f0f0f5]" : "text-[#71717a] hover:bg-[#18181b]/50 hover:text-[#f0f0f5]"
                }`}>
                <span className="flex-1 truncate">{conv.title}</span>
                <span className="text-[9px] text-[#52525b] shrink-0">{formatDate(conv.updated_at)}</span>
                <button onClick={e => deleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-[#52525b] hover:text-red-400 text-xs shrink-0">✕</button>
              </div>
            ))}
          </div>

        </aside>
      )}

      {/* MAIN */}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="h-12 border-b border-[#27272a]/50 px-4 flex items-center gap-3 shrink-0 bg-[#0a0a0f]/40 backdrop-blur-md">
          <button onClick={() => setSidebarOpen(o => !o)}
            className="text-[#52525b] hover:text-[#f0f0f5] transition-colors text-sm w-5">
            {sidebarOpen ? "←" : "→"}
          </button>
          <div className="w-2.5 h-2.5 rounded-full ring-2 ring-[#27272a]/30" style={{ backgroundColor: selectedAgent.color }} />
          <span className="text-sm font-semibold">{selectedAgent.name}</span>
          <div className="ml-auto flex items-center gap-2">
            {totalDue > 0 && (
              <div className="relative">
                <button onClick={() => setShowFollowups(o => !o)}
                  className="text-[10px] font-mono px-2 py-1 rounded-lg border border-[#27272a] text-[#F59E0B] hover:text-[#f0f0f5] transition-colors">
                  {totalDue} due
                </button>
                {showFollowups && (
                  <FollowupPanel followups={followups} commitments={commitments}
                    onDismiss={dismissFollowup} onResolve={resolveCommitment}
                    onClose={() => setShowFollowups(false)} />
                )}
              </div>
            )}
            {selectedAgentId === "bridger" && (
              <div className="flex items-center gap-1.5">
                {speaking && (
                  <button onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); }}
                    className="text-[10px] font-mono text-[#8B5CF6] border border-[#8B5CF6] px-2 py-0.5 rounded-lg animate-pulse">stop</button>
                )}
                <button onClick={() => setTtsEnabled(p => !p)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border transition-colors ${
                    ttsEnabled ? "text-[#09090b] border-[#8B5CF6]" : "text-[#52525b] border-[#27272a] hover:text-[#f0f0f5]"
                  }`} style={ttsEnabled ? { backgroundColor: "#8B5CF6" } : {}}>{ttsEnabled ? "voice on" : "voice off"}</button>
              </div>
            )}
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <main className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 max-w-2xl mx-auto w-full">
              {agentState.messages.length === 0 && !loading && (
                <div className="h-full flex flex-col items-center justify-center text-center gap-3 animate-fade-in">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: selectedAgent.color + "20" }}>
                    <div className="w-5 h-5 rounded-md" style={{ backgroundColor: selectedAgent.color }} />
                  </div>
                  <p className="text-base font-semibold text-[#f0f0f5]">{selectedAgent.name}</p>
                  <p className="text-xs text-[#52525b] max-w-xs">{selectedAgent.placeholder}</p>
                </div>
              )}

              {agentState.messages.map((m, i) => (
                <MessageBubble key={i} msg={m} agentColor={selectedAgent.color}
                  agentName={selectedAgent.name} index={i} />
              ))}

              {loading && <LoadingSkeleton />}
              <div ref={bottomRef} />
            </div>

            {uploadedFilename && (
              <div className="max-w-2xl mx-auto w-full px-6 pb-1">
                <div className="flex items-center gap-2 glass-card rounded-lg px-3 py-1.5 text-xs font-mono text-[#71717a] animate-fade-in">
                  <span>📄</span><span>{uploadedFilename}</span>
                  <button onClick={() => { setUploadedCode(null); setUploadedFilename(null); setInput(""); }}
                    className="ml-auto hover:text-[#f0f0f5] transition-colors">✕</button>
                </div>
              </div>
            )}

            <div className="border-t border-[#27272a]/50 px-6 py-4 shrink-0 bg-[#0a0a0f]/60 backdrop-blur-md">
              <div className="max-w-2xl mx-auto flex gap-2">
                <input ref={fileInputRef} type="file" accept=".py,.js,.ts,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.html,.css,.json,.yaml,.sh,.txt,.md"
                  onChange={handleFileUpload} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()} disabled={loading}
                  className="text-[#52525b] hover:text-[#a1a1aa] px-3 py-2.5 text-xs border border-[#27272a] rounded-lg hover:border-[#3f3f46] transition-colors disabled:opacity-40">attach</button>
                <input className="flex-1 bg-[#18181b]/80 border border-[#27272a] rounded-lg px-4 py-2.5 text-sm text-[#f0f0f5] outline-none transition-all placeholder:text-[#52525b] focus:border-[#52525b] focus:bg-[#18181b]"
                  value={input} onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && send()}
                  placeholder={selectedAgent.placeholder} disabled={loading} />
                <button onClick={send} disabled={loading}
                  className="px-4 py-2.5 rounded-lg text-sm font-medium text-[#09090b] transition-all hover:brightness-110 disabled:opacity-40"
                  style={{ backgroundColor: selectedAgent.color }}>
                  Send
                </button>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

// ── Root ───────────────────────────────────────────────────────────────

const DEFAULT_USER_ID = "988367fd-3496-401a-8c7c-3336a3523079";

export default function Home() {
  return <ChatPage userId={DEFAULT_USER_ID} username="vistasyintern" />;
}
