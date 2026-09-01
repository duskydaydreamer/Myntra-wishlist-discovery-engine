import type { Metadata } from "next";
import "./globals.css";
import Nav from "../components/nav";

export const metadata: Metadata = {
  title: "Myntra Wishlist Discovery Pulse",
  description: "Evidence-backed insights into wishlist behavior and purchase barriers.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "try{const t=localStorage.getItem('discovery-pulse-theme');document.documentElement.dataset.theme=t==='light'?'light':'dark'}catch{}" }} />
      </head>
      <body>
        <Nav />
        <main id="main-content" className="min-h-screen min-w-0 lg:pl-[240px]">
          {children}
        </main>
      </body>
    </html>
  );
}
