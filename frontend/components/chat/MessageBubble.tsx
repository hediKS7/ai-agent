"use client";
import ReactMarkdown from "react-markdown";
import type { Message } from "@/types";

type Props = {
  msg: Message;
  agentColor: string;
  agentName: string;
  index: number;
};

export default function MessageBubble({ msg, agentColor, agentName, index }: Props) {
  const isUser = msg.role === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-slide-up`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? "rounded-br-sm text-[#09090b] font-medium"
            : "rounded-bl-sm glass-card"
        }`}
        style={isUser ? { backgroundColor: agentColor } : {}}
      >
        {!isUser && (
          <p
            className="text-[9px] font-mono tracking-widest mb-1.5 uppercase opacity-60"
            style={{ color: agentColor }}
          >
            {agentName}
          </p>
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
