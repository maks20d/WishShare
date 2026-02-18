import type { Metadata } from "next";
import "./globals.css";
import { ReactNode } from "react";
import { AppProviders } from "./providers";
import { Golos_Text, Unbounded } from "next/font/google";

const bodyFont = Golos_Text({
  subsets: ["latin", "cyrillic"],
  variable: "--font-body"
});

const displayFont = Unbounded({
  subsets: ["latin", "cyrillic"],
  variable: "--font-display"
});

export const metadata: Metadata = {
  title: "WishShare – социальный вишлист",
  description: "Коллективные подарки и вишлисты с реальным временем"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={`${bodyFont.variable} ${displayFont.variable} antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
