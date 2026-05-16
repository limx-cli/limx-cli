const ensureConfirmStyles = () => {
    if (document.getElementById('limx-confirm-css')) return;
    const style = document.createElement('style');
    style.id = 'limx-confirm-css';
    style.textContent = `
.limx-confirm-overlay {
    position: fixed;
    inset: 0;
    z-index: 100000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--ui-modal-overlay, rgba(15, 23, 42, 0.36));
}
.limx-confirm-dialog {
    width: min(360px, calc(100vw - 40px));
    overflow: hidden;
    border: 1px solid var(--ui-black-transparent, rgba(0, 0, 0, 0.12));
    border-radius: 16px;
    background: var(--ui-modal-background, #fff);
    color: var(--ui-modal-foreground, #0f172a);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
    font-family: inherit;
}
.limx-confirm-title {
    padding: 14px 18px;
    background: var(--ui-modal-header-background, #ff6600);
    color: var(--ui-modal-header-foreground, #fff);
    font-weight: 700;
}
.limx-confirm-message {
    padding: 20px 18px;
    font-size: 15px;
    line-height: 1.5;
}
.limx-confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 0 18px 16px;
}
.limx-confirm-actions button {
    min-width: 76px;
    border: 1px solid var(--ui-black-transparent, rgba(0, 0, 0, 0.16));
    border-radius: 8px;
    padding: 8px 14px;
    cursor: pointer;
    font: inherit;
}
.limx-confirm-cancel {
    background: var(--ui-white, #fff);
    color: var(--ui-modal-foreground, #0f172a);
}
.limx-confirm-ok {
    border-color: transparent;
    background: var(--motion-primary, #4c97ff);
    color: #fff;
}
`;
    document.head.appendChild(style);
};

const limxConfirm = message => new Promise(resolve => {
    ensureConfirmStyles();

    const overlay = document.createElement('div');
    overlay.className = 'limx-confirm-overlay';
    overlay.innerHTML = `
<div class="limx-confirm-dialog" role="dialog" aria-modal="true">
    <div class="limx-confirm-title">确认操作</div>
    <div class="limx-confirm-message"></div>
    <div class="limx-confirm-actions">
        <button type="button" class="limx-confirm-cancel">取消</button>
        <button type="button" class="limx-confirm-ok">确定</button>
    </div>
</div>`;
    overlay.querySelector('.limx-confirm-message').textContent = message;

    const close = result => {
        overlay.remove();
        resolve(result);
    };
    overlay.querySelector('.limx-confirm-cancel').addEventListener('click', () => close(false));
    overlay.querySelector('.limx-confirm-ok').addEventListener('click', () => close(true));
    overlay.addEventListener('click', e => {
        if (e.target === overlay) close(false);
    });
    overlay.addEventListener('keydown', e => {
        if (e.key === 'Escape') close(false);
    });

    document.body.appendChild(overlay);
    overlay.querySelector('.limx-confirm-ok').focus();
});

export default limxConfirm;
