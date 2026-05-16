import limxConfirm from './limx-confirm';

const isRunnableTopBlock = block => (
    block &&
    block.topLevel &&
    !block.parent &&
    !block.shadow &&
    block.opcode !== 'procedures_definition'
);

const MAIN_PROGRAM_RUN_INTERVAL_MS = 800;
let lastMainProgramRunAt = 0;

const blockPosition = block => ({
    x: Number.isFinite(block.x) ? block.x : 0,
    y: Number.isFinite(block.y) ? block.y : 0
});

const confirmRunProgram = () => {
    return limxConfirm('确定要运行当前程序吗？');
};

const stopDanceAndActionModes = () => {
    if (typeof fetch !== 'function') {
        return Promise.resolve();
    }
    return fetch('/project/stop-modes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}',
        keepalive: true
    }).catch(() => {
        // Running from a standalone Scratch dev server has no bridge endpoint.
    });
};

const installRunGuards = vm => {
    const runtime = vm && vm.runtime;
    if (!runtime || runtime.__limxStackClickRunGuarded || typeof runtime.toggleScript !== 'function') {
        return;
    }

    const toggleScript = runtime.toggleScript.bind(runtime);
    runtime.toggleScript = (...args) => {
        const options = args[1];
        if (options && options.stackClick) {
            if (window.__limxAllowNextSourceStackClickRun) {
                window.__limxAllowNextSourceStackClickRun = false;
                return toggleScript(...args);
            }
            if (!runtime.__limxAllowStackClickRun) {
                const now = Date.now();
                if (now < (runtime.__limxFlyoutStackClickGroupUntil || 0)) {
                    if (now - (runtime.__limxFlyoutStackClickConfirmAt || 0) > 500) {
                        runtime.__limxFlyoutStackClickConfirmAt = now;
                        limxConfirm('确定要运行当前程序吗？').then(confirmed => {
                            if (confirmed) {
                                window.__limxSkipNextBootstrapStackClickConfirm = true;
                                toggleScript(...args);
                            }
                        });
                    }
                    return;
                }
                return;
            }
            runtime.__limxAllowStackClickRun = false;
        }
        return toggleScript(...args);
    };
    runtime.__limxStackClickRunGuarded = true;
};

const allowNextStackClickRun = vm => {
    installRunGuards(vm);
    if (vm && vm.runtime) {
        vm.runtime.__limxAllowStackClickRun = true;
    }
};

const topLevelProgramBlocks = vm => {
    const runtime = vm && vm.runtime;
    if (!runtime) return [];

    const target = runtime.getEditingTarget ? runtime.getEditingTarget() : vm.editingTarget;
    if (!target || !target.blocks || !target.blocks._blocks) return [];

    return Object.entries(target.blocks._blocks)
        .filter(([, block]) => isRunnableTopBlock(block))
        .map(([id, block]) => ({id, ...blockPosition(block)}))
        .sort((a, b) => (a.y - b.y) || (a.x - b.x));
};

const mainProgramBlock = vm => {
    const blockIds = topLevelProgramBlocks(vm);
    return blockIds.length > 0 ? blockIds[0].id : null;
};

const runCurrentProgram = async vm => {
    installRunGuards(vm);

    const now = Date.now();
    if (now - lastMainProgramRunAt < MAIN_PROGRAM_RUN_INTERVAL_MS) {
        return false;
    }
    lastMainProgramRunAt = now;

    const blockId = mainProgramBlock(vm);
    if (!blockId) {
        // eslint-disable-next-line no-alert
        alert('No program blocks to run. Please drag blocks into the programming workspace first.');
        return false;
    }

    if (!await confirmRunProgram()) {
        return false;
    }

    await stopDanceAndActionModes();

    vm.stopAll();
    vm.start();

    const target = vm.runtime.getEditingTarget ? vm.runtime.getEditingTarget() : vm.editingTarget;
    allowNextStackClickRun(vm);
    vm.runtime.toggleScript(blockId, {
        target,
        stackClick: true
    });
    return true;
};

export {
    allowNextStackClickRun,
    installRunGuards,
    mainProgramBlock,
    runCurrentProgram,
    stopDanceAndActionModes,
    topLevelProgramBlocks
};
