import {hex2hsv, hsv2hex} from '../../tw-color-utils';

const blockColors = {
    motion: {
        primary: '#0C2C47',
        secondary: '#143A5A',
        tertiary: '#1FB8FF',
        quaternary: '#57E7FF'
    },
    looks: {
        primary: '#1D1A4C',
        secondary: '#29246A',
        tertiary: '#8B7CFF',
        quaternary: '#B7AEFF'
    },
    sounds: {
        primary: '#291329',
        secondary: '#4C4C4C',
        tertiary: '#CF63CF',
        quaternary: '#CF63CF'
    },
    control: {
        primary: '#3B2608',
        secondary: '#5A390C',
        tertiary: '#FFB84D',
        quaternary: '#FFD27A'
    },
    event: {
        primary: '#332600',
        secondary: '#4C4C4C',
        tertiary: '#FFBF00',
        quaternary: '#FFBF00'
    },
    sensing: {
        primary: '#0C3038',
        secondary: '#124654',
        tertiary: '#57E7FF',
        quaternary: '#9AF4FF'
    },
    pen: {
        primary: '#06352B',
        secondary: '#0A5141',
        tertiary: '#4EECC6',
        quaternary: '#8AF5DE'
    },
    operators: {
        primary: '#112611',
        secondary: '#4C4C4C',
        tertiary: '#59C059',
        quaternary: '#59C059'
    },
    data: {
        primary: '#3B1F13',
        secondary: '#5A2E1D',
        tertiary: '#FF8F6A',
        quaternary: '#FFB299'
    },
    data_lists: {
        primary: '#331405',
        secondary: '#4C4C4C',
        tertiary: '#FF661A',
        quaternary: '#FF661A'
    },
    more: {
        primary: '#331419',
        secondary: '#4C4C4C',
        tertiary: '#FF6680',
        quaternary: '#FF6680'
    },
    addons: {
        primary: '#0b3331',
        secondary: '#4C4C4C',
        tertiary: '#34e4d0',
        quaternary: '#34e4d0'
    },
    text: 'rgba(235, 250, 255, .86)',
    textFieldText: '#E5E5E5',
    textField: '#102D4A',
    menuHover: 'rgba(87, 231, 255, 0.24)'
};

const extensions = {};

const customExtensionColors = {
    primary: primary => {
        const hsv = hex2hsv(primary);
        hsv[2] = Math.max(hsv[2] - 70, 20);
        return hsv2hex(hsv);
    },
    secondary: () => '#143A5A',
    tertiary: primary => primary,
    quaternary: primary => primary,
    categoryIconBackground: primary => customExtensionColors.primary(primary),
    categoryIconBorder: primary => customExtensionColors.tertiary(primary)
};

export {
    blockColors,
    extensions,
    customExtensionColors
};
