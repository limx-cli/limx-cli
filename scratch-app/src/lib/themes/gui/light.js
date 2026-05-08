const guiColors = {
    'color-scheme': 'light',

    'ui-primary': '#F5F7FB',
    'ui-secondary': '#EEF3F9',
    'ui-tertiary': '#DDE5F0',

    'ui-modal-overlay': 'rgba(15, 23, 42, 0.24)',
    'ui-modal-background': '#FFFFFF',
    'ui-modal-foreground': '#0F172A',
    'ui-modal-header-background': '#FF6600',
    'ui-modal-header-foreground': 'hsla(0, 100%, 100%, 1)', /* #FFFFFF */

    'ui-white': 'hsla(0, 100%, 100%, 1)', /* #FFFFFF */
    'ui-white-dim': 'hsla(0, 100%, 100%, 0.75)', /* 25% transparent version of ui-white */
    'ui-white-transparent': 'hsla(0, 100%, 100%, 0.25)', /* 25% transparent version of ui-white */
    'ui-transparent': 'hsla(0, 100%, 100%, 0)', /* 25% transparent version of ui-white */

    'ui-black-transparent': 'hsla(0, 0%, 0%, 0.15)', /* 15% transparent version of black */

    'text-primary': '#0F172A',
    'text-primary-transparent': 'rgba(15, 23, 42, 0.75)',

    'motion-primary': '#FF6600',
    'motion-primary-transparent': '#FF6600e6',
    'motion-tertiary': '#CC5200',

    'looks-secondary': '#FF6600',
    'looks-transparent': '#FF660059',
    'looks-light-transparent': '#FF660026',
    'looks-secondary-dark': '#CC5200',

    'red-primary': 'hsla(20, 100%, 55%, 1)', /* #FF661A */
    'red-tertiary': 'hsla(20, 100%, 45%, 1)', /* #E64D00 */

    'sound-primary': 'hsla(300, 53%, 60%, 1)', /* #CF63CF */
    'sound-tertiary': 'hsla(300, 48%, 50%, 1)', /* #BD42BD */

    'control-primary': 'hsla(38, 100%, 55%, 1)', /* #FFAB19 */

    'data-primary': 'hsla(30, 100%, 55%, 1)', /* #FF8C1A */

    'pen-primary': 'hsla(163, 85%, 40%, 1)', /* #0FBD8C */
    'pen-transparent': 'hsla(163, 85%, 40%, 0.25)', /* #0FBD8C */
    'pen-tertiary': 'hsla(163, 86%, 30%, 1)', /* #0B8E69 */

    'error-primary': 'hsla(30, 100%, 55%, 1)', /* #FF8C1A */
    'error-light': 'hsla(30, 100%, 70%, 1)', /* #FFB366 */
    'error-transparent': 'hsla(30, 100%, 55%, 0.25)', /* #FF8C1A */

    'extensions-primary': '#FF6600',
    'extensions-tertiary': '#CC5200',
    'extensions-transparent': '#FF660059',
    'extensions-light': '#FFE0CC',

    'drop-highlight': '#FF8800',

    'menu-bar-background': '#FFFFFF',
    'menu-bar-background-image': 'linear-gradient(135deg, #FFFFFF 0%, #F8FBFF 58%, #FFEBDD 100%)',
    'menu-bar-foreground': '#ffffff',

    'assets-background': '#ffffff',

    'input-background': '#ffffff',

    'popover-background': '#ffffff',

    'shadow': 'hsla(0, 0%, 0%, 0.15)',

    'badge-background': '#FFF0E5',
    'badge-border': '#FFD0AD',

    'fullscreen-background': '#F5F7FB',
    'fullscreen-accent': '#FF6600',

    'page-background': '#EEF3F9',
    'page-foreground': '#0F172A',

    'project-title-inactive': 'var(--ui-white-transparent)',
    'project-title-hover': '#ffffff7f',

    'link-color': '#CC5200',

    'limx-app-background': 'radial-gradient(900px 520px at 0% 0%, rgba(191, 219, 254, 0.7), transparent 50%), radial-gradient(900px 520px at 100% 0%, rgba(254, 215, 170, 0.4), transparent 52%), #EEF3F9',
    'limx-card-background': 'rgba(255, 255, 255, 0.92)',
    'limx-card-border': 'rgba(148, 163, 184, 0.22)',
    'limx-card-shadow': '0 18px 42px rgba(148, 163, 184, 0.16)',
    'limx-grid-line': 'rgba(15, 23, 42, 0.045)',
    'limx-menu-background': 'linear-gradient(135deg, #FFFFFF 0%, #F8FBFF 58%, #FFEBDD 100%)',
    'limx-menu-border': 'rgba(148, 163, 184, 0.22)',
    'limx-brand-primary': '#FF6600',
    'limx-brand-secondary': '#FF8800',

    'filter-icon-black': 'none',
    'filter-icon-gray': 'grayscale(100%)',
    'filter-icon-white': 'none',

    'paint-ui-pane-border': 'var(--ui-black-transparent)',
    'paint-text-primary': 'var(--text-primary)',
    'paint-form-border': 'var(--ui-black-transparent)',
    'paint-looks-secondary': 'var(--looks-secondary)',
    'paint-looks-transparent': 'var(--looks-transparent)',
    'paint-input-background': 'var(--input-background)',
    'paint-popover-background': 'var(--popover-background)',
    'paint-filter-icon-gray': 'none'
};

const blockColors = {
    workspace: '#F5F7FB',
    toolboxSelected: '#FFFFFF',
    toolboxText: '#0F172A',
    toolbox: '#EEF3F9',
    flyout: '#FFFFFF',
    scrollbar: '#FF8800',
    valueReportBackground: '#FFFFFF',
    valueReportBorder: '#FFD0AD',
    valueReportForeground: '#0F172A',
    contextMenuBackground: '#FFFFFF',
    contextMenuBorder: 'rgba(148, 163, 184, 0.22)',
    contextMenuForeground: '#0F172A',
    contextMenuActiveBackground: '#FFF0E5',
    contextMenuDisabledForeground: 'rgba(15, 23, 42, 0.3)',
    flyoutLabelColor: 'rgba(15, 23, 42, 0.56)',
    checkboxActiveBackground: '#FF6600',
    checkboxActiveBorder: '#CC5200',
    gridColor: 'rgba(15, 23, 42, 0.06)'
};

export {
    guiColors,
    blockColors
};
