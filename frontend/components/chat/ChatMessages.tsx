"use client";
import { useEffect, useRef } from "react";
import type { Message, Agent } from "@/types";
import MessageBubble from "./MessageBubble";
import EmptyState from "./EmptyState";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

type Props = {
  messages: Message[];
  loading: boolean;
  agent: Agent;
};

export default function ChatMessages({ messages, loading, agent }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 max-w-2xl mx-auto w-full">
      {messages.length === 0 && !loading && <EmptyState agent={agent} />}

      {messages.map((m, i) => (
        <MessageBubble key={i} msg={m} agentColor={agent.color} agentName={agent.name} index={i} />
      ))}

      {loading && <LoadingSkeleton />}
      <div ref={bottomRef} />
    </div>
  );
}
