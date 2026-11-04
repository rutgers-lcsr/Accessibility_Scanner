// theme.ts
import { type ThemeConfig } from 'antd';

export const rutgersTheme: ThemeConfig = {
    token: {
        // Core brand colors
        colorPrimary: '#cc0033',

        colorInfo: '#007fac',
        colorSuccess: '#00626d',
        colorWarning: '#ebb600',
        colorError: '#8e0d18',

        // Base colors
        colorTextBase: '#000000',
        colorBgBase: '#f2f2f2',

        // Greys
        colorText: '#222222',
        colorTextSecondary: '#666666',
        colorBorder: '#d8d8d8',
        colorBorderSecondary: '#efefef',
        colorBgContainer: '#ffffff',

        // Type: Geist is loaded by the root layout (next/font) and exposed as CSS variables.
        fontFamily:
            "var(--font-geist-sans), -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        fontFamilyCode:
            'var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',

        // Other accents. Hover and active go darker, not lighter, so a hovered link keeps
        // its contrast (the lighter blues were about 2:1 on white).
        colorLink: '#007fac',
        colorLinkHover: '#005f80',
        colorLinkActive: '#004d68',

        // Control backgrounds
        controlItemBgActive: '#def0f9',
        controlItemBgHover: '#e3f3ef',
    },
    components: {
        Button: {
            colorPrimary: '#cc0033',
        },
        Card: {
            colorPrimary: '#cc0033',
        },
        Layout: {
            colorPrimary: '#cc0033',
            headerBg: '#ffffff',
            footerBg: '#ffffff',
            siderBg: '#222222',
        },
        // Navigation: the current page reads as scarlet on a scarlet tint, not scarlet on blue.
        Menu: {
            itemSelectedBg: '#fdecef',
            itemSelectedColor: '#b3002d',
            itemHoverBg: '#f3f3f3',
            itemActiveBg: '#fbdde4',
            groupTitleColor: '#666666',
        },
    },
};
