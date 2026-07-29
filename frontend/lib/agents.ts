import type { Agent } from "./types";

export const AGENTS: Agent[] = [
  { id: "general", name: "General", descriptor: "Your everyday thinking partner", color: "#8b8cff", tint: "#8b8cff", placeholder: "Ask anything…" },
  { id: "bridger", name: "Bridger", descriptor: "Build relationships that matter", color: "#c084fc", tint: "#c084fc", placeholder: "Who do you want to connect with?" },
  { id: "vibber", name: "Vibber", descriptor: "Make room for how you feel", color: "#4ade80", tint: "#4ade80", placeholder: "How are you feeling today?" },
  { id: "inspirer", name: "Inspirer", descriptor: "Turn ideas into momentum", color: "#fbbf24", tint: "#fbbf24", placeholder: "What are you building?" },
];

export const getAgent = (id: Agent["id"]) => AGENTS.find((agent) => agent.id === id) ?? AGENTS[0];
