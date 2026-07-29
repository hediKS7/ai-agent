"use client";
import { useEffect, useState } from "react";

type ToastProps = {
  message: string;
  type?: "error" | "success" | "info";
  onClose: () => void;
  duration?: number;
};

export default function Toast({ message, type = "info", onClose, duration = 4000 }: ToastProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const colors = {
    error: "border-red-500/40 text-red-300",
    success: "border-emerald-500/40 text-emerald-300",
    info: "border-[#6366F1]/40 text-[#a1a1aa]",
  };

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl border backdrop-blur-md bg-[#18181b]/90 text-sm transition-all duration-300 ${
        colors[type]
      } ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
    >
      <div className="flex items-center gap-3">
        <span>{message}</span>
        <button onClick={() => { setVisible(false); setTimeout(onClose, 300); }}
          className="opacity-60 hover:opacity-100 transition-opacity">✕</button>
      </div>
    </div>
  );
}
