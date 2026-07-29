export type AgentId = "general" | "bridger" | "vibber" | "inspirer";

export type Agent = {
  id: AgentId;
  name: string;
  descriptor: string;
  color: string;
  tint: string;
  placeholder: string;
};

export type Message = {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

export type Conversation = {
  id: string;
  title: string;
  updated_at: string;
};

export type Followup = {
  id: string;
  agent_type: AgentId;
  followup_type: string;
  context?: { contact_name?: string; context?: string };
};

export type Commitment = {
  id: string;
  description: string;
  deadline: string;
};

export type ChatResponse = {
  response: string;
  conversation_id?: string;
  intent?: string;
  agent_type?: AgentId;
  plan?: string[];
};

export type AgentWorkspaceState = {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
};
