import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "SplitSmart — Good plans. Great company.",
  description: "Your group, on the same page. An interactive Toronto outing demo with thoughtful plans and effortless expense splitting.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
