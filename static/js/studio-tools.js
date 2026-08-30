(function(){
    'use strict';
    if(!/(?:canvas|smart-canvas)\.html$/i.test(location.pathname)) return;

    const state = {open:false, data:null, timer:0};
    const $ = selector => document.querySelector(selector);
    const tools = () => window.StudioCanvasTools || {};
    const canvasId = () => String(tools().getCanvasId?.() || new URLSearchParams(location.search).get('id') || '');
    const safe = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const stamp = value => {
        const raw = Number(value || 0);
        if(!raw) return '--';
        return new Intl.DateTimeFormat('zh-CN', {month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'}).format(raw < 100000000000 ? raw * 1000 : raw);
    };
    function snapshotReasonLabel(reason){
        const value = String(reason || '').trim();
        const labels = {
            'manual':'手动创建的恢复点',
            'restore-before':'恢复前自动备份',
            'repair-before':'修复前自动备份',
            '删除节点':'删除节点前自动备份',
            '导入工作流':'导入工作流前自动备份'
        };
        return labels[value] || value || '恢复点';
    }
    async function api(url, options={}){
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if(!response.ok) throw new Error(data.detail?.message || data.detail || data.message || '操作失败');
        return data;
    }
    function notify(message){
        if(typeof window.toast === 'function') window.toast(message);
        else window.alert(message);
    }

    function mount(){
        if($('#studioTools')) return;
        const root = document.createElement('section');
        root.id = 'studioTools';
        root.className = 'studio-tools';
        root.dataset.tab = 'tasks';
        root.innerHTML = '<button id="studioToolsToggle" class="studio-tools-toggle" type="button" aria-expanded="false"><span class="studio-tools-mark">◇</span><span>创作任务</span><span id="studioToolsCount" class="studio-tools-count">0</span></button>'
            + '<div id="studioToolsPanel" class="studio-tools-panel" aria-hidden="true"><header class="studio-tools-head"><div><b>创作任务中心</b><small>队列、恢复与画布检查</small></div><button id="studioToolsClose" type="button" aria-label="关闭">×</button></header>'
            + '<nav class="studio-tools-tabs"><button data-studio-tab="tasks" class="active" type="button">任务</button><button data-studio-tab="safety" type="button">恢复与检查</button><button data-studio-tab="settings" type="button">生成设置</button></nav><div id="studioToolsContent" class="studio-tools-content"></div></div>';
        document.body.appendChild(root);
        $('#studioToolsToggle').addEventListener('click', () => setOpen(!state.open));
        $('#studioToolsClose').addEventListener('click', () => setOpen(false));
        root.querySelectorAll('[data-studio-tab]').forEach(button => button.addEventListener('click', () => {
            root.dataset.tab = button.dataset.studioTab;
            root.querySelectorAll('[data-studio-tab]').forEach(item => item.classList.toggle('active', item === button));
            render();
        }));
    }
    function setOpen(open){
        state.open = Boolean(open);
        const root = $('#studioTools');
        if(!root) return;
        root.classList.toggle('open', state.open);
        $('#studioToolsToggle').setAttribute('aria-expanded', String(state.open));
        $('#studioToolsPanel').setAttribute('aria-hidden', String(!state.open));
        if(state.open) refresh();
    }
    function taskRow(task){
        const status = String(task.status || 'queued');
        const names = {queued:'排队中', running:'生成中', succeeded:'已完成', failed:'失败', cancelled:'已取消'};
        const action = status === 'queued' ? '<button data-task-action="cancel" data-task-id="' + safe(task.id) + '" type="button">取消</button>' : status === 'failed' ? '<button data-task-action="retry" data-task-id="' + safe(task.id) + '" type="button">重试</button>' : '';
        return '<article class="studio-task-row status-' + safe(status) + '"><div class="studio-task-main"><div><strong>' + safe(task.label || task.model || '生成任务') + '</strong><span>' + safe(task.provider_id || '本地任务') + ' · ' + stamp(task.updated_at || task.created_at) + '</span></div><em>' + (names[status] || safe(status)) + '</em></div>'
            + (task.prompt ? '<p class="studio-task-prompt">' + safe(task.prompt) + '</p>' : '')
            + (task.error ? '<p class="studio-task-error">' + safe(task.error) + '</p>' : '')
            + '<footer><span>' + (task.canvas_id ? '画布 ' + safe(String(task.canvas_id).slice(-6)) : '未归属画布') + '</span>' + (task.upstream_task_id ? '<span>上游 ' + safe(task.upstream_task_id) + '</span>' : '') + action + '</footer></article>';
    }
    function renderTasks(content){
        const data = state.data || {tasks:[], settings:{}};
        const rows = data.tasks || [];
        const active = rows.filter(task => ['queued','running'].includes(task.status)).length;
        content.innerHTML = '<div class="studio-task-summary"><span><b>' + active + '</b> 进行中</span><span><b>' + rows.filter(task => task.status === 'failed').length + '</b> 需要处理</span><span><b>' + (data.active || 0) + '/' + (data.settings?.max_concurrent || 2) + '</b> 并发</span></div><div class="studio-task-list">'
            + (rows.length ? rows.slice(0, 50).map(taskRow).join('') : '<div class="studio-empty">还没有任务。开始生成后，进度、失败原因和重试都会显示在这里。</div>') + '</div>';
        content.querySelectorAll('[data-task-action]').forEach(button => button.addEventListener('click', async () => {
            button.disabled = true;
            try { await api('/api/task-center/' + encodeURIComponent(button.dataset.taskId) + '/' + button.dataset.taskAction, {method:'POST'}); await refresh(); }
            catch(error) { notify(error.message); button.disabled = false; }
        }));
    }
    async function renderSafety(content){
        const id = canvasId();
        if(!id){ content.innerHTML = '<div class="studio-empty">请先打开一个画布。</div>'; return; }
        content.innerHTML = '<div class="studio-empty">正在检查画布...</div>';
        try {
            const pair = await Promise.all([api('/api/canvases/' + encodeURIComponent(id) + '/integrity'), api('/api/canvases/' + encodeURIComponent(id) + '/snapshots')]);
            const report = pair[0].report || {}, snapshots = pair[1].snapshots || [];
            const bad = report.broken_connections || report.invalid_nodes?.length || report.invalid_viewport;
            content.innerHTML = '<section class="studio-safety-card"><div class="studio-safety-title"><div><b>' + safe(report.summary || '画布检查') + '</b><small>' + (report.node_count || 0) + ' 个节点 · ' + (report.connection_count || 0) + ' 条连接</small></div><i class="' + (bad ? 'warn' : 'ok') + '"></i></div><p>断开连接：' + (report.broken_connections || 0) + '；异常节点：' + (report.invalid_nodes?.length || 0) + '；视口：' + (report.invalid_viewport ? '需要修复' : '正常') + '。</p><div class="studio-safety-actions"><button data-safety="snapshot" type="button">创建恢复点</button><button data-safety="fit" type="button">全部节点可见</button><button data-safety="arrange" type="button">整理选中节点</button><button data-safety="repair" class="danger" type="button">检查并修复</button></div></section><section class="studio-snapshot-list"><h4>恢复点</h4>'
                + (snapshots.length ? snapshots.map(item => '<div class="studio-snapshot"><span><b>' + safe(snapshotReasonLabel(item.reason)) + '</b><small>' + stamp(item.created_at) + '</small></span><button data-snapshot-id="' + safe(item.id) + '" type="button">恢复</button></div>').join('') : '<div class="studio-empty">还没有恢复点。删除节点、导入工作流前会自动新增。</div>') + '</section>';
            bindSafety(content);
        } catch(error) { content.innerHTML = '<div class="studio-empty">检查失败：' + safe(error.message) + '</div>'; }
    }
    function bindSafety(content){
        content.querySelectorAll('[data-safety]').forEach(button => button.addEventListener('click', async () => {
            const id = canvasId();
            try {
                if(button.dataset.safety === 'fit'){ tools().fitAll?.(); notify('已将全部节点调整到可视范围'); return; }
                if(button.dataset.safety === 'arrange'){ tools().arrange?.(); notify('已整理选中节点'); return; }
                if(button.dataset.safety === 'snapshot') { await window.StudioCanvasSnapshot('手动创建'); notify('恢复点已创建'); }
                if(button.dataset.safety === 'repair') {
                    if(!window.confirm('将只修复异常坐标、视口和断开的连线。不会删除节点、图片、日志或 API 配置。是否继续？')) return;
                    await api('/api/canvases/' + encodeURIComponent(id) + '/repair', {method:'POST'});
                    await tools().reload?.(); tools().fitAll?.(); notify('画布结构已修复，并已创建修复前恢复点');
                }
                render();
            } catch(error) { notify(error.message); }
        }));
        content.querySelectorAll('[data-snapshot-id]').forEach(button => button.addEventListener('click', async () => {
            if(!window.confirm('将恢复该恢复点的节点、连线、视口和画布设置。图片、日志与 API 配置不会被覆盖。是否继续？')) return;
            try { await api('/api/canvases/' + encodeURIComponent(canvasId()) + '/snapshots/' + encodeURIComponent(button.dataset.snapshotId) + '/restore', {method:'POST'}); await tools().reload?.(); notify('恢复完成'); render(); }
            catch(error) { notify(error.message); }
        }));
    }
    function renderSettings(content){
        const s = state.data?.settings || {max_concurrent:2,max_batch_size:20,retry_limit:1,daily_cost_alert:0};
        content.innerHTML = '<form class="studio-settings-form"><label>最大同时生成数量<input name="max_concurrent" type="number" min="1" max="8" value="' + Number(s.max_concurrent || 2) + '"></label><label>单次任务最大数量<input name="max_batch_size" type="number" min="1" max="100" value="' + Number(s.max_batch_size || 20) + '"></label><label>失败后允许手动重试次数<input name="retry_limit" type="number" min="0" max="3" value="' + Number(s.retry_limit || 1) + '"></label><label>每日费用提醒额度（元，0 为关闭）<input name="daily_cost_alert" type="number" min="0" step="0.01" value="' + Number(s.daily_cost_alert || 0) + '"></label><p>超过并发上限的新任务会自动排队，避免多图生成拖慢电脑。</p><button type="submit">保存生成设置</button></form>';
        content.querySelector('form').addEventListener('submit', async event => {
            event.preventDefault();
            try { await api('/api/task-center/settings', {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(event.currentTarget).entries()))}); notify('生成设置已保存'); await refresh(); }
            catch(error) { notify(error.message); }
        });
    }
    function render(){
        const root = $('#studioTools'), content = $('#studioToolsContent');
        if(!root || !content) return;
        if(root.dataset.tab === 'safety') void renderSafety(content);
        else if(root.dataset.tab === 'settings') renderSettings(content);
        else renderTasks(content);
    }
    async function refresh(){
        try {
            state.data = await api('/api/task-center');
            const count = (state.data.tasks || []).filter(task => ['queued','running'].includes(task.status)).length;
            if($('#studioToolsCount')) $('#studioToolsCount').textContent = String(count);
            if(state.open) render();
        } catch(error) {}
    }
    window.StudioCanvasTaskMeta = (payload, meta={}) => ({...(payload || {}), canvas_id:canvasId(), node_id:String(meta.nodeId || ''), task_label:String(meta.label || payload?.model || '画布生成')});
    window.StudioCanvasSnapshot = async reason => {
        const id = canvasId();
        return id ? api('/api/canvases/' + encodeURIComponent(id) + '/snapshots', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:reason || 'manual'})}) : null;
    };
    function initialize(){ mount(); refresh(); clearInterval(state.timer); state.timer = window.setInterval(refresh, 2400); }
    if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, {once:true}); else initialize();
})();
