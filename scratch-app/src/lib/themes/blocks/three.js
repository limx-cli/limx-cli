const blockColors = {
    motion: {
        primary: '#1FB8FF',
        secondary: '#1398D9',
        tertiary: '#0B6EA8',
        quaternary: '#0B6EA8'
    },
    looks: {
        primary: '#8B7CFF',
        secondary: '#6E61D9',
        tertiary: '#5148A8',
        quaternary: '#5148A8'
    },
    sounds: {
        primary: '#CF63CF',
        secondary: '#C94FC9',
        tertiary: '#BD42BD',
        quaternary: '#BD42BD'
    },
    control: {
        primary: '#FFB84D',
        secondary: '#E69A21',
        tertiary: '#B87515',
        quaternary: '#B87515'
    },
    event: {
        primary: '#FFBF00',
        secondary: '#E6AC00',
        tertiary: '#CC9900',
        quaternary: '#CC9900'
    },
    sensing: {
        primary: '#57E7FF',
        secondary: '#28BBD6',
        tertiary: '#1590A8',
        quaternary: '#1590A8'
    },
    pen: {
        primary: '#4EECC6',
        secondary: '#25C7A0',
        tertiary: '#12997A',
        quaternary: '#12997A'
    },
    operators: {
        primary: '#59C059',
        secondary: '#46B946',
        tertiary: '#389438',
        quaternary: '#389438'
    },
    data: {
        primary: '#FF8F6A',
        secondary: '#E66F49',
        tertiary: '#B94D2F',
        quaternary: '#B94D2F'
    },
    // This is not a new category, but rather for differentiation
    // between lists and scalar variables.
    data_lists: {
        primary: '#FF661A',
        secondary: '#FF5500',
        tertiary: '#E64D00',
        quaternary: '#E64D00'
    },
    more: {
        primary: '#FF6680',
        secondary: '#FF4D6A',
        tertiary: '#FF3355',
        quaternary: '#FF3355'
    },
    addons: {
        primary: '#29beb8',
        secondary: '#3aa8a4',
        tertiary: '#3aa8a4',
        quaternary: '#3aa8a4'
    },
    text: '#FFFFFF',
    workspace: '#F5F9FC',
    toolboxHover: '#17C7FF',
    toolboxSelected: '#E7F6FF',
    toolboxText: '#16324A',
    toolbox: '#FFFFFF',
    blackText: '#575E75',
    flyout: '#F5F9FC',
    scrollbar: '#57E7FF',
    scrollbarHover: '#17C7FF',
    textField: '#FFFFFF',
    textFieldText: '#575E75',
    insertionMarker: '#000000',
    insertionMarkerOpacity: 0.2,
    dragShadowOpacity: 0.6,
    stackGlow: '#FFF200',
    stackGlowSize: 4,
    stackGlowOpacity: 1,
    replacementGlow: '#FFFFFF',
    replacementGlowSize: 2,
    replacementGlowOpacity: 1,
    colourPickerStroke: '#FFFFFF',
    // CSS colours: support RGBA
    fieldShadow: 'rgba(255, 255, 255, 0.3)',
    dropDownShadow: 'rgba(0, 0, 0, .3)',
    numPadBackground: '#547AB2',
    numPadBorder: '#435F91',
    numPadActiveBackground: '#435F91',
    numPadText: 'white', // Do not use hex here, it cannot be inlined with data-uri SVG
    valueReportBackground: '#FFFFFF',
    valueReportBorder: '#AAAAAA',
    valueReportForeground: '#000000',
    menuHover: 'rgba(0, 0, 0, 0.2)',
    contextMenuBackground: '#ffffff',
    contextMenuBorder: '#cccccc',
    contextMenuForeground: '#000000',
    contextMenuActiveBackground: '#d6e9f8',
    contextMenuDisabledForeground: '#cccccc',
    flyoutLabelColor: '#575E75',
    checkboxInactiveBackground: '#ffffff',
    checkboxInactiveBorder: '#c8c8c8',
    checkboxActiveBackground: '#4C97FF',
    checkboxActiveBorder: '#3373CC',
    checkboxCheck: '#ffffff',
    buttonBorder: '#c6c6c6',
    buttonActiveBackground: '#ffffff',
    buttonForeground: '#575E75',
    zoomIconFilter: 'none',
    gridColor: '#dddddd'
};

const extensions = {};

export {
    blockColors,
    extensions
};
