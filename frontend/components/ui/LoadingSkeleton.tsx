export default function LoadingSkeleton() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="glass-card rounded-2xl rounded-bl-sm px-5 py-4 w-72">
        <div className="skeleton-line w-16" />
        <div className="skeleton-line w-full" />
        <div className="skeleton-line w-3/4" />
        <div className="skeleton-line w-1/2" />
      </div>
    </div>
  );
}
