export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="glass-card rounded-2xl rounded-bl-sm px-5 py-4">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#6366F1] pulse-dot" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 rounded-full bg-[#6366F1] pulse-dot" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 rounded-full bg-[#6366F1] pulse-dot" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}
