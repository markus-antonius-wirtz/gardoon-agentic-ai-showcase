import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Gardoon Ltd. | Enterprise Multi-Agent AI & Hybrid Vector Lab',
  description:
    'Live stateful LangGraph Multi-Agent & Qdrant Hybrid RAG reference architecture engineered by Gardoon Ltd. — Production Case Study: TradingTackle.ai.',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
  },
  openGraph: {
    title: 'Gardoon Ltd. | Enterprise Multi-Agent AI Systems Showcase',
    description:
      'Glass-box LangGraph orchestration, parallel Qdrant Dense+BM25 RRF vector search, four-eyes self-correction, and stateful Human-in-the-Loop governance.',
    url: 'https://agents.gardoon.ltd',
    siteName: 'Gardoon Ltd.',
    type: 'website',
  },
};

export const viewport: Viewport = {
  themeColor: '#060913',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased selection:bg-brand-500/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
