"use client";
import { useRef, useEffect } from "react";
import type { Agent } from "@/types";

type Props = {
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
  agent: Agent;
  onSend: () => void;
  onFileClick: () => void;
  uploadedFilename: string | null;
  onClearUpload: () => void;
};

export default function ChatInput({
  input, setInput, loading, agent, onSend, onFileClick,
  uploadedFilename, onClearUpload,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-[#27272a]/50 px-6 py-4 shrink-0 bg-[#0a0a0f]/60 backdrop-blur-md">
      {uploadedFilename && (
        <div className="max-w-2xl mx-auto w-full pb-2">
          <div className="flex items-center gap-2 glass-card rounded-lg px-3 py-1.5 text-xs font-mono text-[#71717a] animate-fade-in">
            <span>📄</span><span className="truncate">{uploadedFilename}</span>
            <button onClick={onClearUpload}
              className="ml-auto hover:text-[#f0f0f5] transition-colors shrink-0">✕</button>
          </div>
        </div>
      )}
      <div className="max-w-2xl mx-auto flex gap-2 items-end">
        <button onClick={onFileClick} disabled={loading}
          className="text-[#52525b] hover:text-[#a1a1aa] px-3 py-2.5 text-xs border border-[#27272a] rounded-lg hover:border-[#3f3f46] transition-colors disabled:opacity-40 shrink-0">
          attach
        </button>
        <textarea
          ref={textareaRef}
          rows={1}
          className="flex-1 bg-[#18181b]/80 border border-[#27272a] rounded-lg px-4 py-2.5 text-sm text-[#f0f0f5] outline-none transition-all placeholder:text-[#52525b] focus:border-[#52525b] focus:bg-[#18181b] resize-none"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={agent.placeholder}
          disabled={loading}
        />
        <button onClick={onSend} disabled={loading || !input.trim()}
          className="px-4 py-2.5 rounded-lg text-sm font-medium text-[#09090b] transition-all hover:brightness-110 disabled:opacity-40 shrink-0"
          style={{ backgroundColor: agent.color }}>
          Send
        </button>
      </div>
    </div>
  );
}
