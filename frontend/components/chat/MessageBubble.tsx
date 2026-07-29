"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Message } from "@/types";

type Props = {
  msg: Message;
  agentColor: string;
  agentName: string;
  index: number;
};

function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const code = String(children).replace(/\n$/, "");
  const lang = match?.[1] || "text";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative group my-3">
      <div className="flex items-center justify-between bg-[#18181b] rounded-t-lg border border-[#27272a] border-b-0 px-4 py-1.5">
        <span className="text-[10px] font-mono text-[#52525b] uppercase">{lang}</span>
        <button
          onClick={handleCopy}
          className="text-[10px] font-mono text-[#52525b] hover:text-[#f0f0f5] transition-colors opacity-0 group-hover:opacity-100"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={lang}
        PreTag="div"
        customStyle={{ margin: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0, fontSize: "0.8rem" }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

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
            <ReactMarkdown components={{ code: CodeBlock }}>
              {msg.content}
            </ReactMarkdown>
          </div>
        ) : (
          <span className="text-sm leading-relaxed">{msg.content}</span>
        )}
      </div>
    </div>
  );
}
