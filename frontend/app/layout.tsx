import type { Metadata, Viewport } from "next";
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
  description: "Коллективные подарки и вишлисты с реальным временем",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "WishShare"
  },
  formatDetection: {
    telephone: false
  }
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffb86b" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0b0f" }
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        {/* iOS PWA icons */}
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="apple-touch-icon" sizes="152x152" href="/icons/icon-152x152.png" />
        <link rel="apple-touch-icon" sizes="167x167" href="/icons/icon-167x167.png" />
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/icon-180x180.png" />
        
        {/* iOS PWA meta tags */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="WishShare" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="format-detection" content="telephone=no" />
        
        {/* Splash screens for iOS (iPhone) */}
        <link rel="apple-touch-startup-image" href="/splash/iphone.png" />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)" 
          href="/splash/iphone-x.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2)" 
          href="/splash/iphone-xr.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 3)" 
          href="/splash/iphone-xs-max.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3)" 
          href="/splash/iphone-12.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 428px) and (device-height: 926px) and (-webkit-device-pixel-ratio: 3)" 
          href="/splash/iphone-14-pro-max.png" 
        />
        
        {/* iPad splash screens */}
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2)" 
          href="/splash/ipad.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2)" 
          href="/splash/ipad-pro-11.png" 
        />
        <link 
          rel="apple-touch-startup-image" 
          media="screen and (device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2)" 
          href="/splash/ipad-pro-12.png" 
        />
      </head>
      <body className={`${bodyFont.variable} ${displayFont.variable} antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
