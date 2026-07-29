import axios from "axios";
import type { Conversation, Followup, Commitment } from "@/types";

const API = "";

export async function fetchConversations(userId: string, agentType: string): Promise<Conversation[]> {
  const res = await axios.get(`${API}/chat/conversations/${userId}?agent_type=${agentType}`);
  return res.data.conversations || [];
}

export async function fetchMessages(userId: string, convId: string): Promise<{ role: string; content: string }[]> {
  const res = await axios.get(`${API}/chat/conversations/${userId}/${convId}/messages`);
  return res.data.messages || [];
}

export async function fetchFollowups(userId: string): Promise<{ followups: Followup[]; commitments: Commitment[] }> {
  const res = await axios.get(`${API}/followups/${userId}`);
  return { followups: res.data.followups || [], commitments: res.data.commitments || [] };
}

export async function sendMessage(params: {
  message: string;
  user_id: string;
  agent_type: string;
  conversation_id?: string;
  code_context?: string;
}) {
  const res = await axios.post(`${API}/chat`, params);
  return res.data as {
    response: string;
    intent: string;
    agent_type: string;
    conversation_id: string;
    plan: unknown[];
  };
}

export async function deleteConversation(convId: string) {
  await axios.delete(`${API}/chat/conversations/${convId}`);
}

export async function dismissFollowup(id: string) {
  await axios.post(`${API}/followups/triggered`, { followup_id: id });
}

export async function resolveCommitment(id: string) {
  await axios.post(`${API}/followups/resolve-commitment`, { commitment_id: id });
}

export async function uploadFile(file: File): Promise<{ filename: string; content: string }> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await axios.post(`${API}/upload`, fd);
  return res.data;
}
