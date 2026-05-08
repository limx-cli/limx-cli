import React from 'react';
import {FormattedMessage, injectIntl, intlShape, defineMessages} from 'react-intl';
import {connect} from 'react-redux';
import classNames from 'classnames';
import PropTypes from 'prop-types';
import bindAll from 'lodash.bindall';
import styles from './loader.css';
import {getIsLoadingWithId} from '../../reducers/project-state';
import topBlock from './top-block.svg';
import middleBlock from './middle-block.svg';
import bottomBlock from './bottom-block.svg';

const mainMessages = {
    'gui.loader.headline': (
        <FormattedMessage
            defaultMessage="Loading Project"
            description="Main loading message"
            id="gui.loader.headline"
        />
    ),
    'gui.loader.creating': (
        <FormattedMessage
            defaultMessage="Creating Project"
            description="Main creating message"
            id="gui.loader.creating"
        />
    ),
    'gui.loader.robotConnection': (
        <FormattedMessage
            defaultMessage="Please connect the robot"
            description="Main message shown when robot connection appears unavailable during project creation"
            id="gui.loader.robotConnection"
        />
    )
};

const messages = defineMessages({
    projectData: {
        defaultMessage: 'Loading project …',
        description: 'Appears when loading project data, but not assets yet',
        id: 'tw.loader.projectData'
    },
    downloadingAssets: {
        defaultMessage: 'Downloading assets ({complete}/{total}) …',
        description: 'Appears when loading project assets from a project on a remote website',
        id: 'tw.loader.downloadingAssets'
    },
    loadingAssets: {
        defaultMessage: 'Loading assets ({complete}/{total}) …',
        description: 'Appears when loading project assets from a project file on the user\'s computer',
        id: 'tw.loader.loadingAssets'
    }
});

const ROBOT_CONNECTION_HINT_DELAY_MS = 8000;

// Because progress events are fired so often during the very performance-critical loading
// process and React updates are very slow, we bypass React for updating the progress bar.

class LoaderComponent extends React.Component {
    constructor (props) {
        super(props);
        bindAll(this, [
            'handleAssetProgress',
            'handleProjectLoaded',
            'barInnerRef',
            'messageRef'
        ]);
        this.barInnerEl = null;
        this.messageEl = null;
        this.ignoreProgress = false;
        this.latestAssetFinished = 0;
        this.latestAssetTotal = 0;
        this.robotConnectionHintShown = false;
        this.robotConnectionHintTimer = null;
        this.state = {
            showRobotConnectionHint: false
        };
    }
    componentDidMount () {
        this.handleAssetProgress(
            this.props.vm.runtime.finishedAssetRequests,
            this.props.vm.runtime.totalAssetRequests
        );
        this.props.vm.on('ASSET_PROGRESS', this.handleAssetProgress);
        this.props.vm.runtime.on('PROJECT_LOADED', this.handleProjectLoaded);
        this.scheduleRobotConnectionHint();
    }
    componentDidUpdate (prevProps) {
        if (prevProps.messageId !== this.props.messageId) {
            this.scheduleRobotConnectionHint();
        }
    }
    componentWillUnmount () {
        this.props.vm.off('ASSET_PROGRESS', this.handleAssetProgress);
        this.props.vm.runtime.off('PROJECT_LOADED', this.handleProjectLoaded);
        this.clearRobotConnectionHint();
    }
    clearRobotConnectionHint () {
        if (this.robotConnectionHintTimer) {
            clearTimeout(this.robotConnectionHintTimer);
            this.robotConnectionHintTimer = null;
        }
    }
    scheduleRobotConnectionHint () {
        this.clearRobotConnectionHint();
        if (this.props.messageId !== 'gui.loader.creating') {
            return;
        }
        this.robotConnectionHintTimer = setTimeout(() => {
            if (this.latestAssetTotal > 0 && this.latestAssetFinished < this.latestAssetTotal) {
                this.scheduleRobotConnectionHint();
                return;
            }
            this.robotConnectionHintShown = true;
            this.setState({
                showRobotConnectionHint: true
            });
            if (this.barInnerEl) {
                this.barInnerEl.style.width = '100%';
            }
        }, ROBOT_CONNECTION_HINT_DELAY_MS);
    }
    handleAssetProgress (finished, total) {
        this.latestAssetFinished = finished;
        this.latestAssetTotal = total;
        if (this.ignoreProgress || this.robotConnectionHintShown || !this.barInnerEl || !this.messageEl) {
            return;
        }

        if (total === 0) {
            // Started loading a new project.
            this.barInnerEl.style.width = '0';
            this.messageEl.textContent = this.props.intl.formatMessage(messages.projectData);
        } else {
            this.barInnerEl.style.width = `${finished / total * 100}%`;
            const message = this.props.isRemote ? messages.downloadingAssets : messages.loadingAssets;
            this.messageEl.textContent = this.props.intl.formatMessage(message, {
                complete: finished,
                total
            });
        }
    }
    handleProjectLoaded () {
        if (this.ignoreProgress || !this.barInnerEl || !this.messageEl) {
            return;
        }

        this.ignoreProgress = true;
        this.props.vm.runtime.resetProgress();
        this.clearRobotConnectionHint();
    }
    barInnerRef (barInner) {
        this.barInnerEl = barInner;
    }
    messageRef (message) {
        this.messageEl = message;
    }
    render () {
        const titleMessageId = this.state.showRobotConnectionHint ?
            'gui.loader.robotConnection' :
            this.props.messageId;
        return (
            <div
                className={classNames(styles.background, {
                    [styles.fullscreen]: this.props.isFullScreen
                })}
            >
                <div className={styles.container}>
                    <div className={styles.blockAnimation}>
                        <img
                            className={styles.topBlock}
                            src={topBlock}
                            draggable={false}
                        />
                        <img
                            className={styles.middleBlock}
                            src={middleBlock}
                            draggable={false}
                        />
                        <img
                            className={styles.bottomBlock}
                            src={bottomBlock}
                            draggable={false}
                        />
                    </div>

                    <div className={styles.title}>
                        {mainMessages[titleMessageId]}
                    </div>

                    <div
                        className={classNames(styles.message, {
                            [styles.hintMessage]: this.state.showRobotConnectionHint
                        })}
                        ref={this.messageRef}
                    >
                        {this.state.showRobotConnectionHint ? (
                            <FormattedMessage
                                defaultMessage="Robot connection was not detected. Please make sure the robot is powered on, connected to the network, then refresh the page and try again."
                                id="tw.loader.robotConnectionHint"
                            />
                        ) : null}
                    </div>

                    <div className={styles.barOuter}>
                        <div
                            className={styles.barInner}
                            ref={this.barInnerRef}
                        />
                    </div>
                </div>
            </div>
        );
    }
}

LoaderComponent.propTypes = {
    intl: intlShape,
    isFullScreen: PropTypes.bool,
    isRemote: PropTypes.bool,
    messageId: PropTypes.string,
    vm: PropTypes.shape({
        on: PropTypes.func,
        off: PropTypes.func,
        runtime: PropTypes.shape({
            totalAssetRequests: PropTypes.number,
            finishedAssetRequests: PropTypes.number,
            resetProgress: PropTypes.func,
            on: PropTypes.func,
            off: PropTypes.func
        })
    })
};
LoaderComponent.defaultProps = {
    isFullScreen: false,
    messageId: 'gui.loader.headline'
};

const mapStateToProps = state => ({
    isRemote: getIsLoadingWithId(state.scratchGui.projectState.loadingState),
    vm: state.scratchGui.vm
});

const mapDispatchToProps = () => ({});

export default connect(
    mapStateToProps,
    mapDispatchToProps
)(injectIntl(LoaderComponent));
