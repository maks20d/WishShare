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
  applicationName: "WishShare",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
      { url: "/icons/icon-167x167.png", sizes: "167x167", type: "image/png" },
      { url: "/icons/icon-152x152.png", sizes: "152x152", type: "image/png" },
    ],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "WishShare"
  },
  formatDetection: {
    telephone: false
  },
  other: {
    "mobile-web-app-capable": "yes",
    "msapplication-TileColor": "#0f172a",
  }
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#10b981" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" }
  ],
  width: "device-width",
  initialScale: 1,
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

        {/* Dev safety: remove stale service workers/caches before Turbopack chunks load */}
        {process.env.NODE_ENV === "development" ? (
          <script
            dangerouslySetInnerHTML={{
              __html: `
                (function () {
                  try {
                    if (location.hostname !== "localhost") return;
                    if (!("serviceWorker" in navigator)) return;
                    navigator.serviceWorker.getRegistrations().then(function (regs) {
                      return Promise.all(regs.map(function (r) { return r.unregister(); }));
                    }).finally(function () {
                      if (!("caches" in window)) return;
                      caches.keys().then(function (keys) {
                        return Promise.all(keys.map(function (k) { return caches.delete(k); }));
                      });
                    });
                  } catch (e) {}
                })();
              `,
            }}
          />
        ) : null}
        
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
