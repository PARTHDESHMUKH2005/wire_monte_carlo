"use client";

export default function Error({ reset }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#050508]">
      <div className="text-center">
        <div className="text-8xl font-bold text-[rgba(255,82,82,0.1)] mb-4">!</div>
        <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
        <p className="text-[rgba(255,255,255,0.4)] mb-8">An unexpected error occurred.</p>
        <button onClick={() => reset()} className="btn-primary inline-block">Try Again</button>
      </div>
    </div>
  );
}
