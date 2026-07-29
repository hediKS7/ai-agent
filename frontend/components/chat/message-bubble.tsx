"use client";

import ReactMarkdown from "react-markdown";
import type { Agent, Message } from "@/lib/types";

export function MessageBubble({ message, agent, onCopy }: { message: Message; agent: Agent; onCopy: (content: string) => void }) {
  const isUser = message.role === "user";
  return (
    <article className={`message ${isUser ? "message--user" : "message--assistant"}`}>
      {!isUser && <div className="message__avatar" style={{ backgroundColor: agent.color }}>{agent.name.slice(0, 1)}</div>}
      <div className="message__content">
        {!isUser && <p className="message__label">{agent.name}</p>}
        <div className={`message__bubble ${isUser ? "message__bubble--user" : "message__bubble--assistant"}`} style={isUser ? { borderColor: `${agent.color}66` } : undefined}>
          {isUser ? <p>{message.content}</p> : <div className="markdown"><ReactMarkdown>{message.content}</ReactMarkdown></div>}
        </div>
        {!isUser && <button className="message__action" onClick={() => onCopy(message.content)}>Copy response</button>}
      </div>
    </article>
  );
}
