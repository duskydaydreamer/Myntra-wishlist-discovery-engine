export default function DatasetCaveat() {
  return (
    <aside className="relative z-20 border-b border-[#2b2033] bg-[#140e1b]/90 px-4 py-2.5 backdrop-blur-xl" aria-label="Dataset scope">
      <div className="mx-auto flex max-w-[1440px] items-start justify-center gap-2 font-mono text-[10px] uppercase leading-5 tracking-[0.06em] text-[#8f8296] sm:items-center">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0 text-[#ff6f91] sm:mt-0">
          <circle cx="12" cy="12" r="9" />
          <path strokeLinecap="round" d="M12 10.5v5M12 7.5h.01" />
        </svg>
        <p>
          <span className="font-bold text-[#d7cbdc]">Dataset Scope · </span>
          Findings reflect this analyzed public dataset and should not be generalized to all Myntra users.
        </p>
      </div>
    </aside>
  );
}
