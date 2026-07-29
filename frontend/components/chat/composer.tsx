"use client";

import { useRef, useState } from "react";

type Attachment = { filename: string; content: string } | null;

export function Composer({ placeholder, accent, disabled, attachment, onAttach, onRemoveAttachment, onSend }: {
  placeholder: string; accent: string; disabled: boolean; attachment: Attachment;
  onAttach: (file: File) => Promise<void>; onRemoveAttachment: () => void; onSend: (message: string) => void;
}) {
  const [message, setMessage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const send = () => { if (message.trim() && !disabled) { onSend(message.trim()); setMessage(""); } };
  return (
    <div className="composer-wrap">
      <div className="composer">
        {attachment && <div className="attachment"><span>Code context · {attachment.filename}</span><button onClick={onRemoveAttachment} aria-label="Remove attachment">×</button></div>}
        <textarea value={message} disabled={disabled} rows={1} placeholder={placeholder} aria-label="Message" onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} />
        <div className="composer__footer">
          <input ref={fileInput} type="file" className="sr-only" accept=".py,.js,.ts,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.html,.css,.json,.yaml,.yml,.sh,.txt,.md" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onAttach(file); event.currentTarget.value = ""; }} />
          <button className="icon-button" onClick={() => fileInput.current?.click()} disabled={disabled} aria-label="Attach a code or text file">Attach</button>
          <span className="composer__hint">Enter to send · Shift + Enter for a new line</span>
          <button className="send-button" style={{ backgroundColor: accent }} disabled={disabled || !message.trim()} onClick={send}>{disabled ? "Thinking…" : "Send"}<span aria-hidden>↑</span></button>
        </div>
      </div>
    </div>
  );
}
