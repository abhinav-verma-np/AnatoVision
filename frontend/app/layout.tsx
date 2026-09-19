import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AnatoVision — Learn Anatomy Through Medical Imaging",
  description:
    "A free, open educational platform for exploring human anatomy through X-ray, CT, MRI, Ultrasound, and other imaging modalities. No login required.",
  metadataBase: new URL("https://anatovision.dpdns.org"),
  icons: {
    icon: "https://img.abhinavverma.com.np/anstovision-logo.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0d12",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
