import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "화가 에이전트 — local image-gen",
  description: "Korean NL → local AI image generation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
