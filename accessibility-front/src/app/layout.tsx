import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Avatar, ConfigProvider } from "antd";
import TabNav from "../components/TabNav";
import { UserProvider } from "../providers/User";
import { rutgersTheme } from "@/lib/theme";
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Access",
  description: "Accessibility Audit Tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased flex`}
      >
        <ConfigProvider theme={rutgersTheme}>
          <UserProvider>
            <div className="">
              <header className="w-lvw bg-white border-b border-gray-200 shadow-sm flex items-center px-6 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-xl font-semibold text-gray-800">Access</span>
                  <span className="text-sm text-gray-500">Accessibility Audit Tool</span>
                </div>

              </header>
              <div className="flex-1 antialiased flex relative">
                <TabNav />
                {children}
              </div>
            </div>


          </UserProvider>
        </ConfigProvider>
      </body>
    </html>
  );
}
