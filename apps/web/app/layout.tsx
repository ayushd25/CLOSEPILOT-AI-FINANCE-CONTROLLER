import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { GlobalErrorProvider } from "@/components/global-error-provider";
import AssistantWidget from "@/components/assistant/assistant-widget";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ClosePilot - Autonomous Finance Controller",
  description: "Models investigate. Rules authorize. Evidence proves.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-background text-foreground min-h-screen`}>
        <GlobalErrorProvider>{children}</GlobalErrorProvider>
        <AssistantWidget />
      </body>
    </html>
  );
}
