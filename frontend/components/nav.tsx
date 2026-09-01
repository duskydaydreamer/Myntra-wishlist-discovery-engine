'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type Theme = 'light' | 'dark';

const links = [
  {
    href: "/dashboard",
    label: "Discovery Pulse",
    description: "Overview",
    icon: <><path d="M4 18V9" /><path d="M10 18V5" /><path d="M16 18v-7" /><path d="M3 18h16" /></>,
  },
  {
    href: "/evidence",
    label: "Evidence Explorer",
    description: "Customer evidence",
    icon: <><path d="M4.5 7.5h15v11h-15z" /><path d="M7 4.5h10v3" /><path d="M8 11h8M8 14.5h5" /></>,
  },
  {
    href: "/query",
    label: "Query Interface",
    description: "Ask the evidence",
    icon: <><circle cx="10.5" cy="10.5" r="5.5" /><path d="m15 15 4 4" /></>,
  },
];

function Brand() {
  return (
    <Link href="/dashboard" className="flex items-center gap-3 rounded-lg">
      <span className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-[13px] bg-gradient-to-br from-[#ff3f6c] via-[#f2558d] to-[#ff8a5c] text-base font-black italic text-white shadow-[0_10px_28px_rgba(255,63,108,.28)]">
        M
        <span className="absolute inset-x-1 bottom-1 h-px bg-white/45" />
      </span>
      <span>
        <span className="nav-brand-title block text-[13px] font-bold leading-4 tracking-[0.01em]">MYNTRA</span>
        <span className="nav-brand-subtitle block text-[9px] font-semibold uppercase leading-4 tracking-[0.14em]">Wishlist intelligence</span>
      </span>
    </Link>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const applyTheme = (nextTheme: Theme) => {
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem('discovery-pulse-theme', nextTheme);
  };

  useEffect(() => {
    if (!isOpen) return;
    const close = (event: KeyboardEvent) => event.key === 'Escape' && setIsOpen(false);
    const main = document.getElementById('main-content');
    const mobileHeader = document.querySelector('[data-mobile-nav-header]');
    const previousOverflow = document.body.style.overflow;
    (document.querySelector('[data-nav-close]') as HTMLButtonElement | null)?.focus();
    main?.setAttribute('inert', '');
    main?.setAttribute('aria-hidden', 'true');
    mobileHeader?.setAttribute('inert', '');
    mobileHeader?.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', close);
    return () => {
      window.removeEventListener('keydown', close);
      main?.removeAttribute('inert');
      main?.removeAttribute('aria-hidden');
      mobileHeader?.removeAttribute('inert');
      mobileHeader?.removeAttribute('aria-hidden');
      document.body.style.overflow = previousOverflow;
      (mobileHeader?.querySelector('[data-nav-open]') as HTMLButtonElement | null)?.focus();
    };
  }, [isOpen]);

  return (
    <>
      <header data-mobile-nav-header className="app-mobile-header sticky top-0 z-40 flex h-16 items-center justify-between border-b px-4 backdrop-blur-xl lg:hidden">
        <Brand />
        <button
          data-nav-open
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Open navigation"
          aria-expanded={isOpen}
          className="nav-icon-button grid h-11 w-11 place-items-center rounded-xl border transition"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
            <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
      </header>

      <nav
        aria-label="Primary navigation"
        className={`app-sidebar fixed inset-y-0 left-0 z-50 flex w-[min(88vw,288px)] flex-col border-r px-3 pb-4 pt-5 shadow-2xl transition-transform duration-200 lg:visible lg:w-[240px] lg:translate-x-0 lg:shadow-none ${isOpen ? 'visible translate-x-0' : 'invisible -translate-x-full'}`}
      >
        <div className="flex items-center justify-between px-2">
          <Brand />
          <button data-nav-close type="button" onClick={() => setIsOpen(false)} aria-label="Close navigation" className="nav-icon-button grid h-10 w-10 place-items-center rounded-lg border border-transparent lg:hidden">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5"><path strokeLinecap="round" d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div className="nav-kicker mt-10 px-2 text-[9px] font-bold uppercase tracking-[0.18em]">Workspace</div>
        <div className="mt-2 space-y-1">
          {links.map((link) => {
            const isActive = pathname === link.href || (link.href === '/dashboard' && pathname.startsWith('/dashboard/'));
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                aria-current={isActive ? 'page' : undefined}
                className={`nav-link group relative flex min-h-[54px] items-center gap-3 rounded-xl border px-3 py-2.5 transition ${isActive ? 'nav-link--active' : ''}`}
              >
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="nav-link-icon h-5 w-5 shrink-0">{link.icon}</svg>
                <span className="min-w-0">
                  <span className="block truncate text-[13px] font-semibold leading-4">{link.label}</span>
                  <span className="nav-link-description mt-0.5 block truncate text-[10px] leading-3">{link.description}</span>
                </span>
              </Link>
            );
          })}
        </div>

        <div className="mt-auto flex justify-end px-2">
          <button
            type="button"
            onClick={() => applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light')}
            aria-label="Toggle colour theme"
            title="Toggle colour theme"
            className="theme-toggle grid h-10 w-10 place-items-center rounded-full border transition"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="theme-icon theme-icon--moon h-[18px] w-[18px]"><path strokeLinecap="round" strokeLinejoin="round" d="M20 15.2A8.3 8.3 0 0 1 8.8 4a8.3 8.3 0 1 0 11.2 11.2Z"/></svg>
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="theme-icon theme-icon--sun h-[18px] w-[18px]"><circle cx="12" cy="12" r="3.5"/><path strokeLinecap="round" d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4"/></svg>
          </button>
        </div>
      </nav>

      {isOpen && <button type="button" aria-label="Close navigation overlay" onClick={() => setIsOpen(false)} className="fixed inset-0 z-40 bg-[#09050d]/75 backdrop-blur-[3px] lg:hidden" />}
    </>
  );
}
