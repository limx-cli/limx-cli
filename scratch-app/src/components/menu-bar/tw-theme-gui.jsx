import PropTypes from 'prop-types';
import React from 'react';
import {FormattedMessage} from 'react-intl';
import {connect} from 'react-redux';

import {MenuItem} from '../menu/menu.jsx';
import {BLOCKS_DARK, BLOCKS_THREE, GUI_DARK, GUI_LIGHT, Theme} from '../../lib/themes/index.js';
import {closeSettingsMenu} from '../../reducers/menus.js';
import {setTheme} from '../../reducers/theme.js';
import {persistTheme} from '../../lib/themes/themePersistance.js';
import lightModeIcon from './tw-sun.svg';
import darkModeIcon from './tw-moon.svg';
import styles from './settings-menu.css';

const GuiThemeMenu = ({
    onChangeTheme,
    theme
}) => (
    <MenuItem>
        <div
            className={styles.option}
            // eslint-disable-next-line react/jsx-no-bind
            onClick={() => {
                const nextGui = theme.gui === GUI_DARK ? GUI_LIGHT : GUI_DARK;
                const nextBlocks = nextGui === GUI_DARK ? BLOCKS_DARK : BLOCKS_THREE;
                onChangeTheme(theme.set('gui', nextGui).set('blocks', nextBlocks));
            }}
        >
            <span className={styles.submenuLabel}>
                {theme.gui === GUI_DARK ? (
                    <FormattedMessage
                        defaultMessage="Light Mode"
                        description="Menu item to change color scheme to light (it is currently dark)"
                        id="tw.darkMode"
                    />
                ) : (
                    <FormattedMessage
                        defaultMessage="Dark Mode"
                        description="Menu item to change color scheme to dark (it is currently light)"
                        id="tw.lightMode"
                    />
                )}
            </span>
        </div>
    </MenuItem>
);

GuiThemeMenu.propTypes = {
    onChangeTheme: PropTypes.func,
    theme: PropTypes.instanceOf(Theme)
};

const mapStateToProps = state => ({
    theme: state.scratchGui.theme.theme
});

const mapDispatchToProps = dispatch => ({
    onChangeTheme: theme => {
        dispatch(setTheme(theme));
        dispatch(closeSettingsMenu());
        persistTheme(theme);
    }
});

export default connect(
    mapStateToProps,
    mapDispatchToProps
)(GuiThemeMenu);
