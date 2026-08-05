(() => {
    const install = () => {
        const world = document.getElementById('smartWorld') || document.getElementById('world');
        if (!world || world.dataset.performanceAssist === '1') return;
        world.dataset.performanceAssist = '1';
        const tuneImages = (root) => {
            root.querySelectorAll?.('.image-node img, .image-node video').forEach(media => {
                if (media.closest('#previewStage, #imageEditModal')) return;
                if (media.tagName === 'IMG') {
                    if (!media.hasAttribute('loading')) media.loading = 'lazy';
                    if (!media.hasAttribute('decoding')) media.decoding = 'async';
                } else if (!media.hasAttribute('preload')) {
                    media.preload = 'metadata';
                }
            });
        };
        tuneImages(world);
        const observer = new MutationObserver(records => {
            for (const record of records) {
                record.addedNodes.forEach(node => {
                    if (node.nodeType === 1) tuneImages(node);
                });
            }
        });
        observer.observe(world, {childList:true, subtree:true});
        window.addEventListener('beforeunload', () => observer.disconnect(), {once:true});
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
    else install();
})();
