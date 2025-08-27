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

        // Other accents
        colorLink: '#007fac',
        colorLinkHover: '#7dbfd6',
        colorLinkActive: '#92d6e3',

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
            footerBg: '#f2f2f2',
            siderBg: '#222222',
        },
    },
};
