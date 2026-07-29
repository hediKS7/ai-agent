import axios from "axios";
import type { AgentId, ChatResponse, Commitment, Conversation, Followup, Message } from "./types";

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
  timeout: 120_000,
});

export const api = {
  async conversations(userId: string, agentType: AgentId) {
    const { data } = await client.get<{ conversations: Conversation[] }>(`/chat/conversations/${userId}`, { params: { agent_type: agentType } });
    return data.conversations;
  },
  async messages(userId: string, conversationId: string) {
    const { data } = await client.get<{ messages: Message[] }>(`/chat/conversations/${userId}/${conversationId}/messages`);
    return data.messages;
  },
  async sendChat(input: { message: string; userId: string; agentType: AgentId; conversationId?: string; codeContext?: string }) {
    const { data } = await client.post<ChatResponse>("/chat", {
      message: input.message,
      user_id: input.userId,
      agent_type: input.agentType,
      conversation_id: input.conversationId,
      code_context: input.codeContext,
    });
    return data;
  },
  deleteConversation(conversationId: string) {
    return client.delete(`/chat/conversations/${conversationId}`);
  },
  async upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    const { data } = await client.post<{ filename: string; content: string }>("/upload", form);
    return data;
  },
  async dueItems(userId: string) {
    const { data } = await client.get<{ followups: Followup[]; commitments: Commitment[] }>(`/followups/${userId}`);
    return data;
  },
  dismissFollowup(followupId: string) {
    return client.post("/followups/triggered", { followup_id: followupId });
  },
  resolveCommitment(commitmentId: string) {
    return client.post("/followups/resolve-commitment", { commitment_id: commitmentId });
  },
};
