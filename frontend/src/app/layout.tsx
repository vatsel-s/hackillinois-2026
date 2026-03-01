import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "Kalshi News Dashboard",
  description: "News-driven prediction market dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans min-h-screen flex flex-col bg-[hsl(220,18%,8%)]">
        <Providers>
          <Nav />
          <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
