import bindAll from 'lodash.bindall';
import PropTypes from 'prop-types';
import React from 'react';
import VM from 'scratch-vm';
import {connect} from 'react-redux';

import ControlsComponent from '../components/controls/controls.jsx';
import {runCurrentProgram} from '../lib/limx-run-program';

let lastRobotStopAt = 0;

const requestRobotStop = () => {
    const now = Date.now();
    if (now - lastRobotStopAt < 300) {
        return;
    }
    lastRobotStopAt = now;
    const url = `/project/stop-now?t=${now}`;
    try {
        const img = new Image();
        img.src = url;
    } catch (e) {
        // Keep the POST fallback below.
    }
    fetch('/project/stop', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}',
        keepalive: true
    }).catch(() => {
        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon('/project/stop', new Blob(['{}'], {type: 'application/json'}));
            }
        } catch (e) {
            // Ignore stop fallback failures; VM stop still runs locally.
        }
    });
};

class Controls extends React.Component {
    constructor (props) {
        super(props);
        bindAll(this, [
            'handleGreenFlagClick',
            'handleStopAllClick'
        ]);
    }
    handleGreenFlagClick (e) {
        e.preventDefault();
        e.stopPropagation();
        // tw: implement alt+click and right click to toggle FPS
        if (e.shiftKey || e.altKey || e.type === 'contextmenu') {
            if (e.shiftKey) {
                this.props.vm.setTurboMode(!this.props.turbo);
            }
            if (e.altKey || e.type === 'contextmenu') {
                if (this.props.framerate === 30) {
                    this.props.vm.setFramerate(60);
                } else {
                    this.props.vm.setFramerate(30);
                }
            }
        } else {
            runCurrentProgram(this.props.vm);
        }
    }
    handleStopAllClick (e) {
        e.preventDefault();
        requestRobotStop();
        this.props.vm.stopAll();
    }
    render () {
        const {
            vm, // eslint-disable-line no-unused-vars
            isStarted, // eslint-disable-line no-unused-vars
            projectRunning,
            turbo,
            ...props
        } = this.props;
        return (
            <ControlsComponent
                {...props}
                active={projectRunning && isStarted}
                turbo={turbo}
                onGreenFlagClick={this.handleGreenFlagClick}
                onStopAllClick={this.handleStopAllClick}
            />
        );
    }
}

Controls.propTypes = {
    isStarted: PropTypes.bool.isRequired,
    projectRunning: PropTypes.bool.isRequired,
    turbo: PropTypes.bool.isRequired,
    framerate: PropTypes.number.isRequired,
    interpolation: PropTypes.bool.isRequired,
    isSmall: PropTypes.bool,
    vm: PropTypes.instanceOf(VM)
};

const mapStateToProps = state => ({
    isStarted: state.scratchGui.vmStatus.started,
    projectRunning: state.scratchGui.vmStatus.running,
    framerate: state.scratchGui.tw.framerate,
    interpolation: state.scratchGui.tw.interpolation,
    turbo: state.scratchGui.vmStatus.turbo
});
// no-op function to prevent dispatch prop being passed to component
const mapDispatchToProps = () => ({});

export default connect(mapStateToProps, mapDispatchToProps)(Controls);
