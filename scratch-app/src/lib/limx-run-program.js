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

const runCurrentProgram = vm => {
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

    vm.stopAll();
    vm.start();

    const target = vm.runtime.getEditingTarget ? vm.runtime.getEditingTarget() : vm.editingTarget;
    vm.runtime.toggleScript(blockId, {
        target,
        stackClick: true
    });
    return true;
};

export {
    mainProgramBlock,
    runCurrentProgram,
    topLevelProgramBlocks
};
