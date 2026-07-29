"use client";
import { useRef, useEffect, useState } from "react";
import type { Agent } from "@/types";

type Props = {
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
  agent: Agent;
  onSend: () => void;
  onFileClick: () => void;
  onFileDrop: (file: File) => void;
  uploadedFilename: string | null;
  onClearUpload: () => void;
};

export default function ChatInput({
  input, setInput, loading, agent, onSend, onFileClick, onFileDrop,
  uploadedFilename, onClearUpload,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [dragging, setDragging] = useState(false);
  const dragCounter = useRef(0);

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

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current++;
    if (e.dataTransfer.types.includes("Files")) setDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current <= 0) { dragCounter.current = 0; setDragging(false); }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    dragCounter.current = 0;
    const file = e.dataTransfer.files?.[0];
    if (file) onFileDrop(file);
  };

  return (
    <div
      className="border-t border-[#27272a]/50 shrink-0 bg-[#0a0a0f]/60 backdrop-blur-md relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag-drop overlay */}
      {dragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#18181b]/90 backdrop-blur-sm rounded-lg border-2 border-dashed border-[#6366F1]">
          <p className="text-sm font-medium text-[#f0f0f5]">Drop file to attach</p>
        </div>
      )}

      <div className="px-3 sm:px-6 py-4">
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
            className="text-[#52525b] hover:text-[#a1a1aa] px-3 py-2.5 text-xs border border-[#27272a] rounded-lg hover:border-[#3f3f46] transition-colors disabled:opacity-40 shrink-0 hidden sm:block">
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
    </div>
  );
}
