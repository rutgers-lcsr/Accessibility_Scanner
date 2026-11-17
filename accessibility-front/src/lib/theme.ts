// theme.ts
import { type ThemeConfig } from 'antd';

export const rutgersTheme: ThemeConfig = {
    token: {
        // Core brand colors
        colorPrimary: '#cc0033',

        colorInfo: '#007fac',
        colorSuccess: '#00626d',
        // antd derives the success alert's fill from colorSuccess, which for this dark teal
        // comes out a muddy grey; use a light tint of the same teal instead.
        colorSuccessBg: '#e8f5f2',
        colorSuccessBorder: '#a7d5cc',
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
        // antd's default placeholder grey is 1.8:1 on white.
        colorTextPlaceholder: '#707070',
        // Captions such as Statistic titles; antd's default #8c8c8c is 3.4:1 on white.
        colorTextDescription: '#595959',

        // Type: Geist is loaded by the root layout (next/font) and exposed as CSS variables.
        fontFamily:
            "var(--font-geist-sans), -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        fontFamilyCode:
            'var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',

        // Other accents. Hover and active go darker, not lighter, so a hovered link keeps
        // its contrast (the lighter blues were about 2:1 on white). #007fac itself is only
        // 4.3:1 on the gray panels and 3.6:1 on an info alert, so links use a darker step.
        colorLink: '#006a8f',
        colorLinkHover: '#005f80',
        colorLinkActive: '#004d68',

        // Control backgrounds
        controlItemBgActive: '#def0f9',
        controlItemBgHover: '#e3f3ef',
    },
    components: {
        // Tag text is shade 7 of each preset palette, which fails 4.5:1 on its own tint for
        // these colours (green 3.4:1, orange 3.3:1, gold 2.8:1); use the next darker shade.
        Tag: {
            volcano7: '#ad2102',
            orange7: '#ad4e00',
            gold7: '#874d00',
            yellow7: '#876800',
            lime7: '#3f6600',
            green7: '#237804',
            cyan7: '#006d75',
        },
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
