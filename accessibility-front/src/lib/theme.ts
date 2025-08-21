// theme.ts
import type { ThemeConfig } from "antd";

export const rutgersTheme: ThemeConfig = {
    token: {
        // Core brand colors
        colorPrimary: "#cc0033",
        colorInfo: "#007fac",
        colorSuccess: "#00626d",
        colorWarning: "#ebb600",
        colorError: "#8e0d18",

        // Base colors
        colorTextBase: "#000000",
        colorBgBase: "#f2f2f2",

        // Greys
        colorText: "#222222",
        colorTextSecondary: "#666666",
        colorBorder: "#d8d8d8",
        colorBorderSecondary: "#efefef",

        // Other accents
        colorLink: "#007fac",
        colorLinkHover: "#7dbfd6",
        colorLinkActive: "#92d6e3",

        // Control backgrounds
        controlItemBgActive: "#def0f9",
        controlItemBgHover: "#e3f3ef",
    },

    components: {
        Button: {
            borderRadius: 8,
            controlHeight: 40,
            fontWeight: 600,
        },
        Card: {
            borderRadiusLG: 12,
            boxShadow: "0 4px 10px rgba(0,0,0,0.1), 0 2px 6px rgba(0,0,0,0.06)",
        },
        Layout: {
            headerBg: "#000000",
            footerBg: "#f2f2f2",
            siderBg: "#222222",
        },
    },
};
