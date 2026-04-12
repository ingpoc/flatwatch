import type { Metadata } from "next";
import { Geist, Geist_Mono, Sacramento, Inter } from "next/font/google";
import "./globals.css";
import { SkipLink } from "@/components/a11y";
import { AuthProvider } from "@/lib/auth";
import { WalletProvider } from "@/lib/wallet";
import { cn } from "@/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sacramento = Sacramento({
  variable: "--font-sacramento",
  subsets: ["latin"],
  weight: ["400"],
});

export const metadata: Metadata = {
  title: "FlatWatch - Society Transparency System",
  description: "Financial transparency for housing societies",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("font-sans", inter.variable)}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${sacramento.variable} antialiased`}
      >
        <WalletProvider>
          <AuthProvider>
            <SkipLink />
            <main id="main-content">
              {children}
            </main>
          </AuthProvider>
        </WalletProvider>
      </body>
    </html>
  );
}
