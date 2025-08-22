import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ConfigProvider, Layout } from "antd";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import TabNav from "../components/TabNav";
import { UserProvider } from "../providers/User";
import { rutgersTheme } from "@/lib/theme";
import { Content, Footer, Header } from "antd/es/layout/layout";
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
        className={`${geistSans.variable} ${geistMono.variable}`}
      >
        <AntdRegistry>
          <Layout hasSider>
            <ConfigProvider theme={rutgersTheme}>
              <UserProvider>
                <TabNav />
                <Layout>
                  {children}

                </Layout>
              </UserProvider>
            </ConfigProvider>
          </Layout>

        </AntdRegistry>
      </body>
    </html>
  );
}
