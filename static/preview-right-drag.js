(() => {
    const install = () => {
        const stage = document.getElementById('previewStage');
        if (!stage || stage.dataset.altDragInstalled === '1') return;
        stage.dataset.altDragInstalled = '1';
        stage.style.userSelect = 'none';
        stage.style.webkitUserSelect = 'none';
        stage.style.webkitUserDrag = 'none';
        stage.style.touchAction = 'none';

        let altDown = false;
        const updateAlt = event => {
            if (window.imageEditMode !== 'preview' || !window.imageEditModal?.classList?.contains('open')) return;
            if (event.key === 'Alt' || event.code === 'AltLeft' || event.code === 'AltRight') {
                altDown = event.type === 'keydown';
            }
        };

        window.addEventListener('keydown', updateAlt, true);
        window.addEventListener('keyup', updateAlt, true);
        window.addEventListener('blur', () => { altDown = false; }, true);

        const startDrag = event => {
            if (window.imageEditMode !== 'preview' || event.button !== 0) return;
            if (!altDown) return;
            if (event.target.closest('.preview-tools-overlay, .preview-download-overlay, .preview-compare-handle')) return;
            if (event.target.closest('video')) return;
            if (window.previewCompareDrag || window.imageEditPanDrag || window.cropDrag) return;

            const panoramaState = window.panoramaState;
            const previewPan = window.previewPan;
            if (!previewPan) return;

            event.preventDefault();
            event.stopPropagation();
            if (event.stopImmediatePropagation) event.stopImmediatePropagation();

            if (panoramaState && panoramaState.enabled) {
                panoramaState.drag = {
                    clientX: event.clientX,
                    clientY: event.clientY,
                    yaw: panoramaState.yaw,
                    pitch: panoramaState.pitch,
                };
                stage.classList.add('panning');
                return;
            }

            window.previewPanDrag = {
                clientX: event.clientX,
                clientY: event.clientY,
                startX: previewPan.x,
                startY: previewPan.y,
            };
        };

        stage.addEventListener('pointerdown', startDrag, true);
        stage.addEventListener('mousedown', startDrag, true);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', install, { once: true });
    } else {
        install();
    }
})();
