import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MediCard | Clinical coordination",
  description: "Secure clinical coordination and clinician-reviewed workflow routing."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
