export type Message = { role: "user" | "assistant"; content: string };

export type Conversation = { id: string; title: string; updated_at: string };

export type Agent = {
  id: string;
  name: string;
  color: string;
  placeholder: string;
};

export type AgentState = {
  conversations: Conversation[];
  activeConvId: string | null;
  messages: Message[];
};

export type Followup = {
  id: string;
  agent_type: string;
  followup_type: string;
  context: Record<string, unknown> | null;
  due_at: string;
};

export type Commitment = {
  id: string;
  description: string;
  deadline: string;
};

export const AGENTS: Agent[] = [
  { id: "general",  name: "General",      color: "#6366F1", placeholder: "Ask anything..." },
  { id: "bridger",  name: "Bridger",      color: "#8B5CF6", placeholder: "Who do you want to connect with?" },
  { id: "vibber",   name: "Vibber",       color: "#10B981", placeholder: "How are you feeling today?" },
  { id: "inspirer", name: "Inspirer",     color: "#F59E0B", placeholder: "What are you building?" },
];

export const DEFAULT_USER_ID = "988367fd-3496-401a-8c7c-3336a3523079";

export const emptyAgentState = (): AgentState => ({
  conversations: [], activeConvId: null, messages: [],
});
