import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Signal Clone - Secure Real-Time Messaging',
  description: 'Real-time messaging application powered by FastAPI and Next.js',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
