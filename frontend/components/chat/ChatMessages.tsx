"use client";
import { useEffect, useRef } from "react";
import type { Message, Agent } from "@/types";
import MessageBubble from "./MessageBubble";
import EmptyState from "./EmptyState";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import TypingIndicator from "@/components/ui/TypingIndicator";

type Props = {
  messages: Message[];
  loading: boolean;
  agent: Agent;
  streaming?: boolean;
};

export default function ChatMessages({ messages, loading, agent, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, streaming]);

  return (
    <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-6 space-y-4 max-w-2xl mx-auto w-full">
      {messages.length === 0 && !loading && <EmptyState agent={agent} />}

      {messages.map((m, i) => (
        <MessageBubble key={i} msg={m} agentColor={agent.color} agentName={agent.name} index={i} />
      ))}

      {streaming && <TypingIndicator />}
      {loading && !streaming && <LoadingSkeleton />}
      <div ref={bottomRef} />
    </div>
  );
}
