(function(){
    'use strict';
    var state={platforms:[],providers:[],brands:[],templates:[],detailPlan:null,history:[],run:null,action:'create',outputKind:'auto',quantityMode:'auto',customQuantity:'',parsedOutput:null,timer:0,parseTimer:0,analysis:null,viewerIndex:0,viewerSources:[],viewerSourceIndex:0,viewerLoadToken:0,viewerTimer:0,initTimer:0,initAttempts:0,initialized:false};
    function one(q,r){return (r||document).querySelector(q)}
    function all(q,r){return Array.prototype.slice.call((r||document).querySelectorAll(q))}
    function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
    function bridge(){return window.StudioEcommerceBridge}
    async function api(url,options){
        options=options||{};
        var response;
        try{response=await fetch(url,Object.assign({headers:{'Content-Type':'application/json'},cache:'no-store'},options))}
        catch(error){throw new Error('无法连接本地服务，请确认启动窗口仍在运行。')}
        var data=await response.json().catch(function(){return {}});
        if(!response.ok)throw new Error(data.detail||data.error||('请求失败 ('+response.status+')'));
        return data;
    }
    function statusLabel(s){return ({queued:'排队中',waiting:'等待',planned:'已生成方案',analyzing:'分析素材',planning:'规划创作',generating:'生成图片',quality_check:'检查结果',layout:'整理结果',adapting:'适配画布',exporting:'导出创作包',paused:'已暂停',interrupted:'重启后待确认',succeeded:'已完成',partial:'部分完成',failed:'失败',cancelled:'已取消'})[s]||s||'尚未开始'}
    function money(v){return v==null?'上游未提供':('¥'+Number(v||0).toFixed(4))}
    function dateText(v){if(!v)return '时间未知';var d=new Date(Number(v)*1000);return isNaN(d.getTime())?'时间未知':d.toLocaleString('zh-CN',{hour12:false})}
    function canvasId(){return bridge()&&bridge().getCanvasId?bridge().getCanvasId():''}
    function selected(){return (bridge()&&bridge().getSelectedNodes?bridge().getSelectedNodes():[]).filter(function(n){return n.type!=='ecommerce-agent'&&n.type!=='smart-ecommerce-agent'})}
    function html(){
        return [
        '<div id="ecAgentBackdrop" class="ec-agent-backdrop"></div>',
        '<aside id="ecAgentPanel" class="ec-agent-panel" aria-label="画布创作 Agent 中心">',
        '<header class="ec-agent-head"><div class="ec-agent-mark"><i data-lucide="bot"></i></div><div><h2>画布创作 Agent</h2><p>选中素材，用一句话继续创作，结果直接回到画布</p></div><button class="ec-agent-close" id="ecClose" title="关闭"><i data-lucide="x"></i></button></header>',
        '<div class="ec-agent-scroll">',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="scan-search"></i><strong>选中素材</strong><span id="ecSelectedCount">0 个节点</span></div><div id="ecHealth" class="ec-health" role="status">正在检查 Agent 服务...</div><div id="ecSelected" class="ec-selected"></div><div class="ec-actions"><button class="ec-btn" id="ecRefreshSelection">刷新选中内容</button><button class="ec-btn" id="ecCreateNode">放入 Agent 节点</button><button class="ec-btn primary" id="ecAnalyze">分析并规划</button></div><p class="ec-hint">Agent 只读取当前选中的图片、文字和参考素材，不会混入画布里的其他内容。</p><div id="ecAnalysis" class="ec-analysis"><div class="ec-empty">点击“分析并规划”，先查看 Agent 准备怎么做。</div></div></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="wand-sparkles"></i><strong>创作指令</strong><span>只读取当前选中内容</span></div><div id="ecOutputChips" class="ec-output-chips"><button type="button" class="ec-output-chip active" data-ec-output="auto">自动判断</button><button type="button" class="ec-output-chip" data-ec-output="detail">一套详情页</button><button type="button" class="ec-output-chip" data-ec-output="main">一套商品主图</button><button type="button" class="ec-output-chip" data-ec-output="video">一条商品视频</button></div><div id="ecActionChips" class="ec-action-chips"><button type="button" class="ec-action-chip active" data-ec-action="create">开始创作</button><button type="button" class="ec-action-chip" data-ec-action="variation">生成变体</button><button type="button" class="ec-action-chip" data-ec-action="background">换背景</button><button type="button" class="ec-action-chip" data-ec-action="expand">扩展画面</button><button type="button" class="ec-action-chip" data-ec-action="refine">局部优化</button><button type="button" class="ec-action-chip" data-ec-action="continue">继续创作</button></div><label class="ec-field"><span>用大白话告诉 Agent 想做什么</span><textarea id="ecRequest" placeholder="例如：帮我把这个商品做成一套详情页，突出材质和使用场景">帮我做一套风格统一的商品主图，保持商品外观不变</textarea></label><div class="ec-quantity"><div class="ec-quantity-head"><strong>生成数量</strong><span>可选或自定义，最多 200 张</span></div><div id="ecQuantityChips" class="ec-quantity-chips"><button type="button" class="ec-quantity-chip active" data-ec-quantity="auto">自动规划</button><button type="button" class="ec-quantity-chip" data-ec-quantity="4">4 张</button><button type="button" class="ec-quantity-chip" data-ec-quantity="6">6 张</button><button type="button" class="ec-quantity-chip" data-ec-quantity="9">9 张</button><button type="button" class="ec-quantity-chip" data-ec-quantity="12">12 张</button><button type="button" class="ec-quantity-chip" data-ec-quantity="custom">自定义</button></div><label id="ecCustomQuantityWrap" class="ec-custom-quantity" hidden><span>输入数量</span><input id="ecCustomQuantity" type="number" min="1" max="200" step="1" placeholder="例如 15"><em>手动数量会覆盖提示词里的数量，点“自动规划”恢复自动识别。</em></label></div><div id="ecParseSummary" class="ec-parse-summary"></div><div id="ecWarnings"></div>',
        '<section class="ec-section ec-template-section"><div class="ec-section-head"><i data-lucide="layout-template"></i><strong>详情页模板</strong><span>先预览结构，不会扣费</span></div><div id="ecTemplates" class="ec-templates"><div class="ec-empty">正在读取模板...</div></div><div id="ecTemplatePlan" class="ec-template-plan"><div class="ec-empty">选择一个模板后，会显示详情页模块顺序。</div></div></section>',
        '<div class="ec-row"><label class="ec-field"><span id="ecProviderLabel">图片 API</span><select id="ecProvider"></select></label><label class="ec-field"><span id="ecModelLabel">图片模型</span><select id="ecModel"></select></label></div><div id="ecVideoOptions" class="ec-video-options" hidden><label class="ec-field"><span>视频时长（秒）</span><input id="ecVideoDuration" type="number" min="1" max="60" value="5"></label><label class="ec-field"><span>画面比例</span><select id="ecAspectRatio"><option>16:9</option><option>9:16</option><option>1:1</option><option>4:3</option><option>3:4</option></select></label></div><label class="ec-check" style="margin-top:8px"><input id="ecAddText" type="checkbox" checked>保留可编辑文字层</label><label class="ec-check"><input id="ecStrictFidelity" type="checkbox" checked>严格保留主体、Logo 和原有文字</label></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="workflow"></i><strong>执行</strong><span>结果自动放回画布</span></div><div class="ec-actions"><button class="ec-btn" id="ecDryRun">预演方案（不扣费）</button><button class="ec-btn primary" id="ecStart">开始生成</button><button class="ec-btn" id="ecPause" disabled>暂停</button><button class="ec-btn" id="ecResume" disabled>继续</button><button class="ec-btn danger" id="ecCancel" disabled>取消</button></div></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="history"></i><strong>最近运行</strong><span>重新打开仍可查看</span></div><div id="ecHistory" class="ec-history"><div class="ec-empty">正在读取运行记录...</div></div></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="activity"></i><strong>运行进度</strong><span id="ecRunId">未运行</span></div><div id="ecRunStatus" class="ec-empty">运行后会显示每一步、成功数、失败原因和上游任务编号</div></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="images"></i><strong>创作结果</strong><span id="ecResultCount">0 张</span></div><div id="ecResults" class="ec-results"><div class="ec-empty" style="grid-column:1/-1">尚无结果</div></div><div class="ec-actions"><button class="ec-btn" id="ecFactOnly" disabled>仅保留原始文字</button><button class="ec-btn" id="ecViewDetail" disabled>查看详情页</button><button class="ec-btn primary" id="ecExport" disabled>导出创作包</button></div></section>',
        '<section class="ec-section"><div class="ec-section-head"><i data-lucide="circle-dollar-sign"></i><strong>费用统计</strong><span>以实际返回为准</span></div><div class="ec-cost"><div><span>预计费用</span><strong id="ecEstimated">上游未提供</strong></div><div><span>实际扣费</span><strong id="ecActual">上游未提供</strong></div></div><p class="ec-hint">接口未提供费用时显示“上游未提供”，不会猜测或套用本机其他接口的价格。</p></section>',
        '</div></aside>'
        ].join('');
    }
    function selectedPreview(){
        var rows=selected();
        one('#ecSelectedCount').textContent=rows.length+' 个节点';
        one('#ecSelected').innerHTML=rows.length?rows.slice(0,8).map(function(node){
            var url=node.url||(node.images&&node.images[0]&&node.images[0].url)||'';
            return '<div class="ec-selected-item">'+(url?'<img src="'+esc(url)+'" loading="lazy">':'<span>'+esc(node.text||node.title||node.name||node.type||'文字节点')+'</span>')+'</div>';
        }).join(''):'<div class="ec-empty" style="grid-column:1/-1">先在画布中选中图片、文字或参考素材</div>';
    }
    function platformIds(){return ['canvas']}
    function activeOutputKind(){return state.outputKind!=='auto'?state.outputKind:((state.parsedOutput&&state.parsedOutput.kind)||'main')}
    function explicitOutputKind(text){
        text=String(text||'').trim();
        if(/视频|短视频|宣传片|广告片|商品片/i.test(text))return 'video';
        if(/详情页|详情图|详情页面|详情/i.test(text))return 'detail';
        if(/主图|白底图|商品图|产品图|电商图|套图/i.test(text))return 'main';
        return '';
    }
    function requestedOutputKind(){return explicitOutputKind(one('#ecRequest')&&one('#ecRequest').value)||activeOutputKind()}
    function quantityOverride(){
        if(state.quantityMode==='auto')return 0;
        var value=state.quantityMode==='custom'?Number(one('#ecCustomQuantity')&&one('#ecCustomQuantity').value):Number(state.quantityMode);
        if(!Number.isFinite(value)||value<1)return 0;
        return Math.max(1,Math.min(200,Math.round(value)));
    }
    function syncQuantityUi(){
        all('.ec-quantity-chip').forEach(function(item){item.classList.toggle('active',item.getAttribute('data-ec-quantity')===String(state.quantityMode))});
        var custom=state.quantityMode==='custom',wrap=one('#ecCustomQuantityWrap');
        if(wrap)wrap.hidden=!custom;
        if(custom&&one('#ecCustomQuantity')&&!one('#ecCustomQuantity').value)one('#ecCustomQuantity').value=state.customQuantity||'';
    }
    function outputLabel(){return (state.parsedOutput&&state.parsedOutput.label)||({detail:'详情页',main:'商品主图',video:'商品视频'})[activeOutputKind()]||'商品主图'}
    function syncOutputUi(){
        var kind=activeOutputKind(),video=kind==='video';
        one('#ecProviderLabel').textContent=video?'视频 API':'图片 API';
        one('#ecModelLabel').textContent=video?'视频模型':'图片模型';
        one('#ecVideoOptions').hidden=!video;
        one('#ecAddText').closest('.ec-check').style.display=video?'none':'';
        all('.ec-output-chip').forEach(function(item){item.classList.toggle('active',item.getAttribute('data-ec-output')===state.outputKind)});
    }
    function renderModels(){
        var kind=activeOutputKind(),key=kind==='video'?'video_models':'image_models';
        var candidates=state.providers.filter(function(item){return (item[key]||[]).length});
        var previous=one('#ecProvider').value;
        one('#ecProvider').innerHTML=candidates.map(function(p){return '<option value="'+esc(p.id)+'">'+esc(p.name||p.id)+(p.has_key?'':'（未配置 Key）')+'</option>'}).join('')||'<option value="">没有可用 API</option>';
        if(candidates.some(function(p){return p.id===previous}))one('#ecProvider').value=previous;
        var p=candidates.find(function(item){return item.id===one('#ecProvider').value})||candidates[0];
        one('#ecModel').innerHTML=((p&&p[key])||[]).map(function(model){return '<option value="'+esc(model)+'">'+esc(model)+'</option>'}).join('')||'<option value="">没有可用模型</option>';
        var note=one('#ecHealth');
        if(note&&candidates.length){
            var configured=candidates.filter(function(item){return item.has_key}).length;
            var label=kind==='video'?'视频':'图片';
            note.className='ec-health '+(configured?'ok':'warn');
            note.textContent=configured?'Agent 已就绪，可生成'+label+'。':'已找到'+label+' API，但还没有配置 API Key，请先到 API 设置填写。';
        }
        if(note&&!candidates.length){
            note.className='ec-health warn';
            note.textContent='当前没有可用的'+(kind==='video'?'视频':'图片')+' API 或模型，请先到 API 设置配置。';
        }
    }
    function renderTemplates(){
        var target=one('#ecTemplates');if(!target)return;
        target.innerHTML=state.templates.length?state.templates.map(function(t){
            var active=state.detailPlan&&state.detailPlan.template_id===t.id?' active':'';
            return '<button type="button" class="ec-template-card'+active+'" data-ec-template="'+esc(t.id)+'"><strong>'+esc(t.name)+'</strong><span>'+esc(t.description)+'</span><small>'+Number(t.modules.length)+' 个模块 · 建议 '+Number(t.recommended_count)+' 张</small></button>';
        }).join(''):'<div class="ec-empty">暂无详情页模板</div>';
    }
    function renderTemplatePlan(){
        var target=one('#ecTemplatePlan');if(!target)return;var p=state.detailPlan;
        if(!p){target.innerHTML='<div class="ec-empty">选择一个模板后，会显示详情页模块顺序。</div>';return}
        target.innerHTML='<div class="ec-template-plan-head"><strong>'+esc(p.template_name)+'</strong><span>'+Number(p.total_images)+' 张 · 不扣费预览</span></div><p class="ec-template-description">'+esc(p.template_description||'')+'</p><div class="ec-module-list">'+(p.modules||[]).map(function(m,i){return '<div class="ec-module-item ec-module-item-rich"><b>'+String(i+1).padStart(2,'0')+'</b><span><strong>'+esc(m.module_name)+'</strong><small>'+esc(m.kind)+' · '+esc(m.purpose)+'</small><em>'+esc(m.text_hint)+'</em><details><summary>查看自动提示词</summary><pre>'+esc(m.prompt||'正在生成提示词...')+'</pre><button type="button" class="ec-copy-prompt" data-ec-copy-prompt="'+esc(m.prompt||'')+'">复制提示词</button></details></span></div>'}).join('')+'</div><div class="ec-template-plan-actions"><button type="button" class="ec-btn primary" id="ecApplyTemplate">应用这个模板</button><span>应用后会按模块逐张生成，旧图片不会被覆盖。</span></div>';
    }
    function selectTemplate(id){
        var source=selected();if(!source.length){one('#ecTemplatePlan').innerHTML='<div class="ec-warning">请先在画布中选中商品图片，再选择详情页模板。</div>';return}
        state.outputKind='detail';syncOutputUi();renderModels();
        api('/api/ecommerce-agent/detail-plan',{method:'POST',body:JSON.stringify({input_snapshot:source,request_text:one('#ecRequest').value,template_id:id,quantity_override:quantityOverride()})}).then(function(data){state.detailPlan=data.plan||null;renderTemplates();renderTemplatePlan();parseRequest()}).catch(function(e){one('#ecTemplatePlan').innerHTML='<div class="ec-warning">模板预览失败：'+esc(e.message)+'</div>'});
    }
    function previewDefaultDetailTemplate(){
        if(activeOutputKind()!=='detail'||state.detailPlan)return;
        var source=selected();if(!source.length)return;
        api('/api/ecommerce-agent/detail-plan',{method:'POST',body:JSON.stringify({input_snapshot:source,request_text:one('#ecRequest').value,template_id:'basic-detail',quantity_override:quantityOverride()})}).then(function(data){
            state.detailPlan=data.plan||null;renderTemplates();renderTemplatePlan();
        }).catch(function(e){console.warn('基础详情页预览失败',e)});
    }
    function renderBase(){
        syncOutputUi();syncQuantityUi();renderModels();
    }
    async function loadBase(){
        var results=await Promise.all([api('/api/ecommerce-agent/platforms'),api('/api/ecommerce-agent/detail-templates')]);
        var data=results[0],templateData=results[1];
        state.platforms=data.platforms||[];
        state.providers=(data.providers||[]).filter(function(p){return p.enabled!==false&&((p.image_models||[]).length||(p.video_models||[]).length)});
        state.brands=[];
        state.templates=templateData.templates||[];
        renderBase();renderTemplates();await parseRequest();
    }
    async function checkHealth(){
        var note=one('#ecHealth');if(!note)return;
        try{
            var data=await api('/api/ecommerce-agent/health');
            if(data.ok){
                note.className='ec-health ok';
                note.textContent=(data.provider_count?'Agent 已就绪，已读取 '+data.provider_count+' 个 API 配置。':'Agent 已就绪，请先在 API 设置配置接口。');
            }else{
                note.className='ec-health warn';
                note.textContent=data.message||'Agent 服务未完全就绪，请重启本地服务后重试。';
            }
        }catch(error){
            note.className='ec-health warn';
            note.textContent=error.message||'Agent 服务检查失败';
        }
    }
    function renderHistory(){
        var target=one('#ecHistory');if(!target)return;
        target.innerHTML=state.history.length?state.history.slice(0,12).map(function(run){
            var selected=state.run&&state.run.id===run.id?' selected':'';
            var name=run.product_profile&&run.product_profile.name||'未命名创作';
            var historyUnit=run.output_kind==='video'?'条':'张';
            return '<button type="button" class="ec-history-item'+selected+'" data-ec-history-id="'+esc(run.id)+'"><span><strong>'+esc(name)+'</strong><small>'+esc(dateText(run.created_at))+'</small></span><span class="ec-history-meta"><b>'+esc(statusLabel(run.status))+'</b><small>'+Number(run.success_count||0)+' / '+Number(run.total_images||0)+' '+historyUnit+'</small></span></button>';
        }).join(''):'<div class="ec-empty">当前画布还没有运行记录</div>';
    }
    async function loadHistory(preferLatest){
        try{
            var data=await api('/api/ecommerce-agent/runs?canvas_id='+encodeURIComponent(canvasId())+'&limit=30');
            state.history=data.runs||[];renderHistory();
            if(preferLatest&&state.history.length&&!state.run){state.run=state.history[0];updateRun();}
        }catch(e){one('#ecHistory').innerHTML='<div class="ec-warning">运行记录读取失败：'+esc(e.message)+'</div>'}
    }
    function chooseHistory(id){
        var run=state.history.find(function(item){return item.id===id});if(!run)return;
        state.run=run;renderHistory();updateRun();
        if(['succeeded','partial','failed','cancelled'].indexOf(run.status)<0)poll();
    }
    async function parseRequest(){
        try{
            var data=await api('/api/ecommerce-agent/parse-request',{method:'POST',body:JSON.stringify({request_text:one('#ecRequest').value,platforms:platformIds(),output_kind:state.outputKind,quantity_override:quantityOverride()})});
            var q=data.quantity||{};
            state.parsedOutput=data.output||null;syncOutputUi();renderModels();
            if(q.output_kind!=='detail'&&state.outputKind==='auto')state.detailPlan=null;
            var unit=q.output_kind==='video'?'条':'张';
            if(state.outputKind==='auto'&&q.output_kind!==activeOutputKind()){state.detailPlan=null;syncOutputUi();renderTemplates();renderTemplatePlan()}
            one('#ecParseSummary').innerHTML='<span class="ec-chip">'+esc(outputLabel())+' <strong>'+Number(q.total_images||0)+' '+unit+'</strong></span><span class="ec-chip">任务批次 <strong>'+Number((q.batches||[]).length||1)+'</strong></span>'+(q.output_kind==='detail'&&!state.detailPlan?'<span class="ec-chip">将自动套用 <strong>基础详情页</strong></span>':'');
            one('#ecWarnings').innerHTML=(q.warnings||[]).map(function(w){return '<div class="ec-warning">'+esc(w)+'</div>'}).join('');
            if(q.output_kind==='detail'&&!state.detailPlan)previewDefaultDetailTemplate();
        }catch(e){one('#ecWarnings').innerHTML='<div class="ec-warning">'+esc(e.message)+'</div>'}
    }
    async function analyzeSelection(){
        var source=selected();
        if(!source.length){one('#ecAnalysis').innerHTML='<div class="ec-warning">请先在画布中选中图片、文字或参考素材。</div>';return false}
        try{
            var data=await api('/api/ecommerce-agent/analyze',{method:'POST',body:JSON.stringify({input_snapshot:source,request_text:one('#ecRequest').value,action:state.action})});
            state.analysis=data.analysis||{};
            var a=state.analysis;
            one('#ecAnalysis').innerHTML='<div class="ec-analysis-summary"><span class="ec-chip">素材 <strong>'+Number(a.source_count||0)+'</strong></span><span class="ec-chip">图片 <strong>'+Number(a.image_count||0)+'</strong></span><span class="ec-chip">文字 <strong>'+Number(a.text_count||0)+'</strong></span></div><strong class="ec-analysis-title">建议执行步骤</strong><ol>'+((a.steps||[]).map(function(step){return '<li>'+esc(step)+'</li>'}).join(''))+'</ol>'+((a.known_text||[]).length?'<div class="ec-analysis-known"><strong>已读到的文字</strong><p>'+a.known_text.map(esc).join('<br>')+'</p></div>':'')+((a.warnings||[]).map(function(w){return '<div class="ec-warning">'+esc(w)+'</div>'}).join(''));
            return Boolean(a.ready);
        }catch(e){one('#ecAnalysis').innerHTML='<div class="ec-warning">分析失败：'+esc(e.message)+'</div>';return false}
    }
    function ensureAgent(){if(!bridge())throw new Error('当前画布尚未准备好');return bridge().ensureAgentNode?bridge().ensureAgentNode():null}
    function makePayload(dry){
        var source=selected();if(!source.length)throw new Error('请先在画布里选中图片、文字或参考素材');
        var agent=ensureAgent();
        var outputKind=requestedOutputKind(),detail=outputKind==='detail'?state.detailPlan:null;
        return {canvas_id:bridge().getCanvasId?bridge().getCanvasId():'',node_id:agent&&agent.id||'',canvas_kind:bridge().kind||'classic',selected_node_ids:source.map(function(n){return n.id}),input_snapshot:source,brand_profile_id:'',platforms:['canvas'],provider_id:one('#ecProvider').value,model:one('#ecModel').value,request_text:one('#ecRequest').value,action:state.action,size:'',quality:'auto',fidelity:one('#ecStrictFidelity')&&one('#ecStrictFidelity').checked?'strict':'balanced',add_text:one('#ecAddText').checked,max_retries:2,dry_run:dry,template_id:detail&&detail.template_id||'',template_name:detail&&detail.template_name||'',detail_modules:detail&&detail.modules||[],template_version:'1',output_kind:outputKind,quantity_override:quantityOverride(),video_duration:Number(one('#ecVideoDuration').value||5),aspect_ratio:one('#ecAspectRatio').value||'16:9',resolution:''};
    }
    async function startRun(dry){
        try{
         if(state.quantityMode==='custom'&&!quantityOverride()){alert('请先输入自定义生成数量（1 到 200 张）。');return;}
         if(!await analyzeSelection())return;
         if(!dry&&!confirm('将按当前数量向选定 API 提交图片任务，可能产生费用。确认开始吗？'))return;
            var data=await api('/api/ecommerce-agent/runs',{method:'POST',body:JSON.stringify(makePayload(dry))});
            state.run=data.run;state.history=[state.run].concat(state.history.filter(function(item){return item.id!==state.run.id}));renderHistory();updateRun();poll();
        }catch(e){alert(e.message)}
    }
    async function action(name){
        if(!state.run)return;
        try{var data=await api('/api/ecommerce-agent/runs/'+encodeURIComponent(state.run.id)+'/'+name,{method:'POST',body:'{}'});state.run=data.run;updateRun();if(name==='resume')poll()}catch(e){alert(e.message)}
    }
    async function poll(){
        clearTimeout(state.timer);if(!state.run)return;
        try{var data=await api('/api/ecommerce-agent/runs/'+encodeURIComponent(state.run.id));state.run=data.run;updateRun()}catch(e){console.warn('画布 Agent 状态读取失败',e)}
        if(state.run&&['succeeded','partial','failed','cancelled'].indexOf(state.run.status)<0)state.timer=setTimeout(poll,900);
    }
    function updateRun(){
        var run=state.run;if(!run)return;
        var terminal=['succeeded','partial','failed','cancelled'].indexOf(run.status)>=0;
        one('#ecRunId').textContent=run.id.slice(-8);
        one('#ecRunStatus').className='ec-status-card';
        var runStatusLabel=run.status==='generating'&&run.output_kind==='video'?'生成视频':statusLabel(run.status);
        one('#ecRunStatus').innerHTML='<div class="ec-status-top"><strong>'+esc(runStatusLabel)+'</strong><span>'+esc(run.current_stage||'')+'</span></div><div class="ec-progress" style="--progress:'+Number(run.progress||0)+'%"><i></i></div><div class="ec-metrics"><div><b>'+Number(run.total_images||0)+'</b><span>'+((run.output_kind==='video')?'总条数':'总张数')+'</span></div><div><b>'+Number(run.success_count||0)+'</b><span>成功</span></div><div><b>'+Number(run.failed_count||0)+'</b><span>失败</span></div><div><b>'+Number(run.retry_count||0)+'</b><span>重做</span></div></div>'+(run.warnings||[]).map(function(w){return '<div class="ec-warning">'+esc(w)+'</div>'}).join('');
        var outputs=run.outputs||[];
        var outputUnit=run.output_kind==='video'?' 条':' 张';
        one('#ecResultCount').textContent=outputs.filter(function(o){return o.status==='succeeded'}).length+' / '+Number(run.total_images||0)+outputUnit;
        one('#ecResults').innerHTML=outputs.length?outputs.map(function(o){
            if(o.url){var isVideo=o.media_kind==='video'||/\.(mp4|webm|mov|m4v)(?:[?#]|$)/i.test(o.url);return '<div class="ec-result'+(isVideo?' is-video':'')+'" role="button" tabindex="0" data-ec-view-output="'+esc(o.id)+'">'+(isVideo?'<video src="'+esc(o.url)+'" muted preload="metadata" playsinline></video><i class="ec-video-badge">视频</i>':'<img src="'+esc(o.url)+'" loading="lazy" alt="生成结果">')+'<em>'+esc((o.plan&&((o.plan.module_name)||o.plan.purpose))||'创作结果')+'</em>'+(o.cost&&o.cost.amount!=null?'<small>¥'+Number(o.cost.amount).toFixed(4)+'</small>':'')+'</div>';}
            var label=({waiting:'等待',queued:'排队',running:'生成中',retrying:'重试中',interrupted:'重启后待确认',failed:'失败',cancelled:'已取消',planned:'已生成方案'})[o.status]||o.status;
            return '<div class="ec-result pending"><span>'+esc(o.plan&&o.plan.index||'')+' · '+esc(label)+'</span>'+(o.error?'<small title="'+esc(o.error)+'">'+esc(o.error)+'</small>':'')+(o.upstream_task_id?'<small>上游编号：'+esc(o.upstream_task_id)+'</small>':'')+((o.status==='failed'||o.status==='succeeded')?'<button type="button" class="ec-result-retry" data-ec-retry-output="'+esc(o.id)+'">重新生成</button>':'')+'</div>';
        }).join(''):'<div class="ec-empty" style="grid-column:1/-1">尚无结果</div>';
        one('#ecEstimated').textContent=money(run.estimated_cost);one('#ecActual').textContent=money(run.actual_cost);
        one('#ecPause').disabled=terminal||run.status==='paused';one('#ecResume').disabled=terminal||run.status!=='paused';one('#ecCancel').disabled=terminal;one('#ecFactOnly').disabled=run.output_kind==='video'||!(run.inferred_claims||[]).length;one('#ecExport').disabled=!terminal;one('#ecViewDetail').textContent=run.output_kind==='video'?'查看视频结果':'打开结果预览';one('#ecViewDetail').disabled=!outputs.some(function(o){return o.status==='succeeded'&&o.url});
        if(bridge().updateAgentNode)bridge().updateAgentNode(run);
        if(bridge().applyRunResults)bridge().applyRunResults(run);
        renderHistory();
    }
    async function retryOutput(id){
        if(!state.run)return;
        try{var data=await api('/api/ecommerce-agent/runs/'+encodeURIComponent(state.run.id)+'/retry-output/'+encodeURIComponent(id),{method:'POST',body:'{}'});state.run=data.run;updateRun();poll()}catch(e){alert(e.message)}
    }
    function editBrand(fresh){
        var brand=fresh?null:state.brands.find(function(b){return b.id===one('#ecBrand').value});if(fresh)one('#ecBrand').value='';
        one('#ecBrandName').value=brand&&brand.name||'';one('#ecBrandPrimary').value=brand&&brand.primary_color||'#13b8a6';one('#ecBrandSecondary').value=brand&&brand.secondary_color||'#69c7ff';one('#ecBrandAudience').value=brand&&brand.audience||'';one('#ecBrandForbidden').value=((brand&&brand.forbidden_words)||[]).join('，');one('#ecBrandEditor').classList.add('open');
    }
    async function saveBrand(){
        var id=one('#ecBrand').value;
        var body={name:one('#ecBrandName').value.trim(),primary_color:one('#ecBrandPrimary').value,secondary_color:one('#ecBrandSecondary').value,audience:one('#ecBrandAudience').value.trim(),forbidden_words:one('#ecBrandForbidden').value.split(/[,，]/).map(function(x){return x.trim()}).filter(Boolean),logo:'',font:'',title_style:'',background_style:'',forbidden_visuals:[],approved_references:[]};
        if(!body.name){alert('请填写品牌名称');return}
        try{var data=await api(id?'/api/ecommerce-agent/brands/'+encodeURIComponent(id):'/api/ecommerce-agent/brands',{method:id?'PUT':'POST',body:JSON.stringify(body)});if(id)state.brands=state.brands.map(function(x){return x.id===id?data.brand:x});else state.brands.unshift(data.brand);renderBrands();one('#ecBrand').value=data.brand.id;one('#ecBrandEditor').classList.remove('open')}catch(e){alert(e.message)}
    }
    async function exportRun(){
        if(!state.run)return;
         try{var response=await fetch('/api/ecommerce-agent/runs/'+encodeURIComponent(state.run.id)+'/export',{method:'POST'});if(!response.ok){var d=await response.json();throw new Error(d.detail||'导出失败')}var blob=await response.blob();var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=((state.run.product_profile&&state.run.product_profile.name)||'创作项目')+'-创作包.zip';a.click();setTimeout(function(){URL.revokeObjectURL(url)},2000)}catch(e){alert(e.message)}
    }
    function viewerSources(raw){
        var url=String(raw||'').trim();if(!url)return [];if(/^data:|^blob:/i.test(url))return [url];
        if(/\.(mp4|webm|mov|m4v)(?:[?#]|$)/i.test(url))return [url];
        var name='详情页预览.'+((url.match(/\.(png|jpe?g|webp)(?:[?#]|$)/i)||[])[1]||'png');
        var preview='/api/media-preview?w=2048&url='+encodeURIComponent(url);
        var proxy='/api/download-output?inline=1&url='+encodeURIComponent(url)+'&name='+encodeURIComponent(name);
        return [preview,proxy,url].filter(function(item,index,items){return item&&items.indexOf(item)===index});
    }
    function loadViewerImage(){
        var img=one('#ecViewerImage'),video=one('#ecViewerVideo'),stateEl=one('#ecViewerState');if(!img||!video||!stateEl)return;
        clearTimeout(state.viewerTimer);var token=++state.viewerLoadToken;var src=state.viewerSources[state.viewerSourceIndex];
        img.style.display='none';img.removeAttribute('src');video.style.display='none';video.pause();video.removeAttribute('src');stateEl.className='ec-viewer-state loading';stateEl.textContent=state.viewerSourceIndex?'正在切换备用预览...':(state.viewerIsVideo?'正在加载视频...':'正在加载图片...');
        if(state.viewerIsVideo){
            video.onloadeddata=function(){if(token!==state.viewerLoadToken)return;clearTimeout(state.viewerTimer);video.style.display='block';stateEl.className='ec-viewer-state success';stateEl.textContent='视频已加载';setTimeout(function(){if(token===state.viewerLoadToken)stateEl.textContent=''},500)};
            video.onerror=function(){if(token!==state.viewerLoadToken)return;clearTimeout(state.viewerTimer);video.style.display='none';stateEl.className='ec-viewer-state error';stateEl.innerHTML='视频暂时无法加载，请重新尝试<button type="button" class="ec-viewer-retry" id="ecViewerRetry">重新加载</button>';one('#ecViewerRetry').onclick=function(){state.viewerSourceIndex=0;loadViewerImage()}};
            state.viewerTimer=setTimeout(function(){if(token===state.viewerLoadToken)video.onerror()},30000);video.src=src;video.load();return;
        }
        img.onload=function(){if(token!==state.viewerLoadToken)return;clearTimeout(state.viewerTimer);img.style.display='block';stateEl.className='ec-viewer-state success';stateEl.textContent='图片已加载';setTimeout(function(){if(token===state.viewerLoadToken)stateEl.textContent=''},500)};
        img.onerror=function(){if(token!==state.viewerLoadToken)return;clearTimeout(state.viewerTimer);if(state.viewerSourceIndex<state.viewerSources.length-1){state.viewerSourceIndex+=1;loadViewerImage();return}img.style.display='none';stateEl.className='ec-viewer-state error';stateEl.innerHTML='图片暂时无法加载，请重新尝试<button type="button" class="ec-viewer-retry" id="ecViewerRetry">重新加载</button>';one('#ecViewerRetry').onclick=function(){state.viewerSourceIndex=0;loadViewerImage()}};
        state.viewerTimer=setTimeout(function(){if(token===state.viewerLoadToken)img.onerror()},18000);img.src=src;
    }
    function showViewer(index){
        if(!state.run)return;var list=(state.run.outputs||[]).filter(function(o){return o.status==='succeeded'&&o.url});if(!list.length)return;
        state.viewerIndex=(index+list.length)%list.length;var o=list[state.viewerIndex];
        var box=one('#ecDetailViewer');if(!box){document.body.insertAdjacentHTML('beforeend','<div id="ecDetailViewer" class="ec-detail-viewer" role="dialog" aria-modal="true"><div class="ec-viewer-panel"><button type="button" class="ec-viewer-close" id="ecViewerClose">×</button><div class="ec-viewer-kicker" id="ecViewerKicker">创作结果预览</div><h3 id="ecViewerTitle"></h3><div class="ec-viewer-image-wrap"><div id="ecViewerState" class="ec-viewer-state loading">正在加载图片...</div><img id="ecViewerImage" alt="创作结果"><video id="ecViewerVideo" controls playsinline preload="metadata" style="display:none"></video></div><div class="ec-viewer-meta" id="ecViewerMeta"></div><div class="ec-viewer-actions"><button type="button" class="ec-btn" id="ecViewerPrev">上一项</button><button type="button" class="ec-btn" id="ecViewerNext">下一项</button><a class="ec-btn primary" id="ecViewerDownload" download>下载结果</a></div></div></div>');box=one('#ecDetailViewer');one('#ecViewerClose').onclick=function(){clearTimeout(state.viewerTimer);one('#ecViewerVideo').pause();box.classList.remove('open')};one('#ecViewerPrev').onclick=function(){showViewer(state.viewerIndex-1)};one('#ecViewerNext').onclick=function(){showViewer(state.viewerIndex+1)};box.onclick=function(e){if(e.target===box){clearTimeout(state.viewerTimer);one('#ecViewerVideo').pause();box.classList.remove('open')}}}
        state.viewerIsVideo=o.media_kind==='video'||/\.(mp4|webm|mov|m4v)(?:[?#]|$)/i.test(o.url);one('#ecViewerKicker').textContent=state.viewerIsVideo?'商品视频预览':'详情页/主图预览';one('#ecViewerTitle').textContent=(o.plan&&((o.plan.module_name)||o.plan.purpose))||'创作结果';one('#ecViewerDownload').href=o.url;one('#ecViewerDownload').download=(state.viewerIsVideo?'商品视频-':'创作图片-')+String((o.plan&&o.plan.index)||state.viewerIndex+1).padStart(2,'0')+(state.viewerIsVideo?'.mp4':'.png');one('#ecViewerMeta').textContent='第 '+String((o.plan&&o.plan.index)||state.viewerIndex+1)+(state.viewerIsVideo?' 条':' 张')+' · '+((state.run.template_name)||state.run.output_label||'创作结果')+(o.cost&&o.cost.amount!=null?' · 费用 ¥'+Number(o.cost.amount).toFixed(4):'');state.viewerSources=viewerSources(o.url);state.viewerSourceIndex=0;box.classList.add('open');loadViewerImage();
    }
    function open(){one('#ecAgentBackdrop').classList.add('open');one('#ecAgentPanel').classList.add('open');selectedPreview();loadHistory(true)}
    function close(){one('#ecAgentBackdrop').classList.remove('open');one('#ecAgentPanel').classList.remove('open')}
    function bind(){
        document.addEventListener('click',function(e){if(e.target.closest('[data-ecommerce-agent-open]'))open()});
        one('#ecClose').onclick=close;one('#ecAgentBackdrop').onclick=close;one('#ecRefreshSelection').onclick=function(){selectedPreview();analyzeSelection()};one('#ecCreateNode').onclick=function(){ensureAgent();selectedPreview()};one('#ecAnalyze').onclick=analyzeSelection;
        one('#ecHistory').addEventListener('click',function(e){var item=e.target.closest('[data-ec-history-id]');if(item)chooseHistory(item.getAttribute('data-ec-history-id'))});
        one('#ecTemplates').addEventListener('click',function(e){var item=e.target.closest('[data-ec-template]');if(item)selectTemplate(item.getAttribute('data-ec-template'))});
        one('#ecTemplatePlan').addEventListener('click',function(e){var copy=e.target.closest('[data-ec-copy-prompt]');if(copy){var text=copy.getAttribute('data-ec-copy-prompt')||'';if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){copy.textContent='已复制'}).catch(function(){window.prompt('复制下面的提示词：',text)})}else{window.prompt('复制下面的提示词：',text)}return}if(e.target.closest('#ecApplyTemplate')){one('#ecRequest').value='按当前详情页模板生成每个模块，保持商品主体和原有文字不变';state.outputKind='detail';state.parsedOutput=null;syncOutputUi();var id=state.detailPlan&&state.detailPlan.template_id;if(id)selectTemplate(id);else parseRequest();}});
        one('#ecResults').addEventListener('click',function(e){var retry=e.target.closest('[data-ec-retry-output]');if(retry){e.preventDefault();retryOutput(retry.getAttribute('data-ec-retry-output'));return}var item=e.target.closest('[data-ec-view-output]');if(item)showViewer((state.run.outputs||[]).filter(function(o){return o.status==='succeeded'&&o.url}).findIndex(function(o){return o.id===item.getAttribute('data-ec-view-output')}))});
         one('#ecProvider').onchange=renderModels;one('#ecRequest').oninput=function(){
             var text=(one('#ecRequest').value||'').trim();
             var detected=text.match(/视频|短视频|宣传片|广告片|商品片/)?'video':(text.match(/详情页|详情图|详情页面|详情/)?'detail':(text.match(/主图|白底图|商品图|产品图|电商图|套图/)?'main':''));
             if(state.outputKind!=='auto'&&detected&&detected!==state.outputKind){state.outputKind='auto';state.detailPlan=null;syncOutputUi();renderModels();renderTemplates();renderTemplatePlan()}
             state.parsedOutput=null;clearTimeout(state.parseTimer);state.parseTimer=setTimeout(parseRequest,350)
         };
        one('#ecOutputChips').addEventListener('click',function(e){var chip=e.target.closest('[data-ec-output]');if(!chip)return;state.outputKind=chip.getAttribute('data-ec-output')||'auto';state.parsedOutput=null;if(state.outputKind!=='detail')state.detailPlan=null;syncOutputUi();renderModels();parseRequest();renderTemplates();renderTemplatePlan();if(state.outputKind==='detail')previewDefaultDetailTemplate();});
        one('#ecActionChips').addEventListener('click',function(e){var chip=e.target.closest('[data-ec-action]');if(!chip)return;state.action=chip.getAttribute('data-ec-action')||'create';all('.ec-action-chip').forEach(function(item){item.classList.toggle('active',item===chip)});analyzeSelection();});
        one('#ecQuantityChips').addEventListener('click',function(e){
            var chip=e.target.closest('[data-ec-quantity]');if(!chip)return;
            state.quantityMode=chip.getAttribute('data-ec-quantity')||'auto';
            if(state.quantityMode==='custom'&&one('#ecCustomQuantity'))one('#ecCustomQuantity').focus();
            syncQuantityUi();if(activeOutputKind()==='detail')state.detailPlan=null;clearTimeout(state.parseTimer);state.parseTimer=setTimeout(parseRequest,120);
        });
        one('#ecCustomQuantity').addEventListener('input',function(){
            state.customQuantity=this.value;state.quantityMode='custom';syncQuantityUi();if(activeOutputKind()==='detail')state.detailPlan=null;clearTimeout(state.parseTimer);state.parseTimer=setTimeout(parseRequest,180);
        });
        one('#ecDryRun').onclick=function(){startRun(true)};one('#ecStart').onclick=function(){startRun(false)};one('#ecPause').onclick=function(){action('pause')};one('#ecResume').onclick=function(){action('resume')};one('#ecCancel').onclick=function(){action('cancel')};one('#ecFactOnly').onclick=function(){action('fact-only')};one('#ecExport').onclick=exportRun;one('#ecViewDetail').onclick=function(){showViewer(0)};
    }
    function init(){
        if(state.initialized)return;
        if(!bridge()){
            state.initAttempts+=1;
            if(state.initAttempts<80)state.initTimer=setTimeout(init,125);
            else document.body.insertAdjacentHTML('beforeend','<div class="ec-startup-error">画布 Agent 未能连接当前画布。请刷新页面；如果仍然没有恢复，请重启本地服务。</div>');
            return;
        }
        state.initialized=true;
        document.body.insertAdjacentHTML('beforeend',html());bind();selectedPreview();
        Promise.all([loadBase(),checkHealth()]).then(function(){return loadHistory(true)}).catch(function(e){var target=one('#ecWarnings');if(target)target.innerHTML='<div class="ec-warning">'+esc(e.message)+'</div>'});
        if(window.lucide)lucide.createIcons();
        window.EcommerceAgentUI={open:open,close:close,refresh:selectedPreview};
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
