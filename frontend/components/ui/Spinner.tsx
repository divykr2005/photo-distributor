export default function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="relative">
        <div className="w-10 h-10 rounded-full border-2 border-slate-700" />
        <div className="absolute top-0 left-0 w-10 h-10 rounded-full border-2 border-transparent border-t-violet-500 animate-spin" />
      </div>
    </div>
  );
}
