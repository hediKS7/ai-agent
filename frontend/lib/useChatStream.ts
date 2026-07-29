"use client";
import { useCallback, useRef } from "react";

const API = "";

type StreamCallbacks = {
  onToken: (token: string, conversationId?: string) => void;
  onDone: (conversationId: string) => void;
  onError: (error: string) => void;
};

export function useChatStream() {
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const stream = useCallback(async (
    params: {
      message: string;
      user_id: string;
      agent_type: string;
      conversation_id?: string;
      code_context?: string;
    },
    callbacks: StreamCallbacks
  ) => {
    stop();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
        signal: controller.signal,
      });

      if (!response.ok) {
        callbacks.onError(`Server error: ${response.status}`);
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                callbacks.onToken(data.token, data.conversation_id);
              }
              if (data.done) {
                callbacks.onDone(data.conversation_id || "");
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      callbacks.onError(err instanceof Error ? err.message : "Stream failed");
    } finally {
      abortRef.current = null;
    }
  }, [stop]);

  return { stream, stop };
}
