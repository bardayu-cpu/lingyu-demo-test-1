/* =====================================================================
   demo-v2.0 · 试用意见（10/23 批）· 机构端
   1. 咨询次数：每学期 8 次免费正式咨询；负责咨询师申请加次（单次 ≤ 4），上级咨询师审批，学期总上限 20；
      危机干预中的学生不计次数。三个数在「权限与设置 · 流转设置 · 流转规则」里，由中心负责人修改
   2. 预咨询分派：学生只选时间，提交后「待分派」；L3 在「预约咨询 · 预咨询分派」指派，被指派的咨询师再确认；
      超过 24 小时没分派进待办池
   3. 预咨询摘要带「风险信息」（来自普测和访谈，学生看不到），分派时按话题、期待和风险推荐 1–2 位咨询师
   6. 行政督导（陈行政，原系统管理员账号）：只有工作台（统计 + 高危提醒）、数据看板、通知；没有权限与设置。
      能看到多少在「权限与设置 · 权限配置」里选配；配置交给中心负责人（兼系统管理员）
===================================================================== */
RULES.quota = { free: 8, add: 4, cap: 20 };
RULES.prePick = true;   // 学生第一次约预咨询时，除了「让中心安排」，是否也允许自己选老师
RULES.sup = { name: false, year: false, sms: true, data: true };
RULES.lim.disp = 24;

/* ---------- 6. 行政督导 ---------- */
STAFF.a1.role = 'SUP'; STAFF.a1.title = '行政督导'; ACCTS.a1 = ['SUP'];
RN.SUP = '行政督导'; COL.SUP = COL.ADM;
const supMenu = () => { MENUS.SUP = [['home', '工作台', 'home'], ...(RULES.sup.data ? [['data', '数据看板', 'chart']] : []), ['noti', '通知', 'bell', 'hide']]; };
supMenu();
CHIPS.SUP = ['今天先做什么？', '有哪些超时？'];
QUICK.splice(QUICK.findIndex(q => q[0] === 'a1'), 1, ['a1', 'SUP']);
QUICK.splice(QUICK.findIndex(q => q[0] === 'c5') + 1, 0, ['c5', 'ADM']);
MEMO.SUP = { home: ['试用意见：行政管理老师不需要权限与设置，只看统计和高危提醒，起监督作用。', '陈行政原来是系统管理员，现在是「行政督导」；配置工作交给朱静（中心负责人，兼系统管理员，快速登录里选「朱静 · 系统管理员」）。', '高危提醒只读，不能打开个案。默认只显示学院和处理状态，不显示姓名；朱静可以在「权限与设置 · 权限配置」里打开姓名、年级、短信提醒和数据看板。'],
  data: ['和系统管理员一样只看汇总，不能点进名单，也不能导出个人数据。'] };
const asRole = (r, f) => { const r0 = S.role; S.role = r; try { return f(); } finally { S.role = r0; } };
const _queues20 = queues; queues = function (u, r) { return (r || S.role) === 'SUP' ? [] : _queues20.apply(this, arguments); };
const _shell20 = shell; shell = function () { let h = _shell20.apply(this, arguments); if (S.role !== 'SUP') return h;
  return h.replace(/<label class="srch">[\s\S]*?<\/label>/, '').replace(/<button class="btn [^"]*" data-act="mo" data-arg="report:[^"]*">[\s\S]*?<\/button>/, ''); };
const _data20 = PAGES.data; PAGES.data = function () { return S.role === 'SUP' ? asRole('ADM', () => _data20.apply(this, arguments)) : _data20.apply(this, arguments); };
const _noti20 = PAGES.noti; PAGES.noti = function () { return S.role === 'SUP' ? asRole('ADM', () => _noti20.apply(this, arguments)) : _noti20.apply(this, arguments); };
/* 高危提醒：新危机、升级时发给行政督导；文字按可见范围脱敏 */
const supWho = s => { const o = RULES.sup; return s ? `${s.college}${o.year ? ` ${s.year}` : ''}${o.name ? ` ${s.name}` : ' 一名学生'}` : '一名学生'; };
const supNotify = (k, t, at) => notify('a1', RULES.sup.sms ? '站内 + 短信' : '站内', t, k.id, '已送达', at);
CRISES.forEach(k => supNotify(k, `高危提醒：${supWho(SU(k.sid))}进入危机通道（${k.type}）`, k.at));
const _crisisNotify20 = crisisNotify; crisisNotify = function (k, at) { const r = _crisisNotify20.apply(this, arguments); supNotify(k, `高危提醒：${supWho(SU(k.sid))}进入危机通道（${k.type}）`, at); return r; };
const kSt = k => k.st === 'closed' ? '<span class="pill g">已结束</span>' : k.st === 'new' ? (cLeft(k) < 0 ? `<span class="pill r">超时未接收 ${dur(cLeft(k))}</span>` : `<span class="pill w">待接收 · 剩 ${dur(cLeft(k))}</span>`) : '<span class="pill">处理中</span>';
function supHome() { const o = RULES.sup, sv = SURV(), done = sv.filter(s => s.done).length, ks = CRISES.slice().sort((a, b) => b.at - a.at);
  const lv = [5, 4, 3, 2, 1].map(n => [n, sv.filter(s => curLv(s) === n).length]), act = BOOK.filter(b => ['disp', 'audit', 'confirm', 'ok', 'change', 'pool'].includes(b.st)).length;
  const late = CRISES.filter(k => k.st === 'new' && cLeft(k) < 0).length + STU.filter(overdue).length + BOOK.filter(b => b.st === 'pool').length;
  const kpi = (n, t, sub) => `<div class="kpi"><b>${n}</b><span>${t}</span>${sub ? `<small>${sub}</small>` : ''}</div>`;
  return `<div class="card"><h3>${I('chart')}今天的情况<span class="sp"></span><small>统计到 ${fmt(NOW)} · 只读</small></h3><div class="kpis" style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
      ${kpi(`${ROSTER ? Math.round(done / ROSTER * 100) : 0}%`, '普测完成率', `${done} / ${ROSTER} 人`)}${kpi(lv.filter(x => x[0] >= 4).reduce((n, x) => n + x[1], 0), '密切关注及以上', lv.map(([n, c]) => `${n} 级 ${c}`).join(' · '))}${kpi(act, '进行中的预约', `待分派 ${BOOK.filter(b => b.st === 'disp').length}`)}${kpi(late, '超时未处理', '危机未接收、复核超时、预约待办池')}</div></div>
    <div class="card"><h3>${I('alert')}高危提醒<span class="sp"></span><small>${ks.filter(k => k.st !== 'closed').length} 条进行中</small></h3>
      <table class="t"><tr><th>时间</th>${o.name ? '<th>学生</th>' : ''}<th>学院${o.year ? ' · 年级' : ''}</th><th>类型</th><th>状态</th><th>接收</th><th>升级</th><th>已用时</th></tr>${ks.map(k => { const s = SU(k.sid) || {};
        return `<tr class="${k.st === 'new' && cLeft(k) < 0 ? 'crit' : ''}"><td>${fmt(k.at)}</td>${o.name ? `<td>${s.name || '—'}<small>${s.sid || ''}</small></td>` : ''}<td>${s.college || '—'}${o.year ? `<small>${s.year || ''}</small>` : ''}</td><td>${esc(k.type)}</td><td>${kSt(k)}</td><td>${k.recv ? `${ST(k.recv.by).name}<small>${fmt(k.recv.at)}</small>` : '—'}</td><td>${k.esc >= 2 ? '分管领导' : k.esc ? '中心负责人' : '—'}</td><td>${dur(hrs(k.at))}</td></tr>`; }).join('') || '<tr><td colspan="8" class="note">没有高危提醒</td></tr>'}</table>
      <p class="note">只读：起监督作用，不能打开个案，也不参与处理。${o.name ? '' : '不显示姓名。'}能看到哪些信息由中心负责人在「权限与设置 · 权限配置」里设定，新危机和升级会${o.sms ? '通过站内信和短信' : '通过站内信'}提醒你。</p></div>`; }
const _home20 = PAGES.home; PAGES.home = function () { return S.role === 'SUP' ? supHome() : _home20.apply(this, arguments); };
/* 设置 · 权限配置：行政督导能看到什么（中心负责人或系统管理员修改） */
const SUPOPT = [['name', '高危提醒显示学生姓名和学号', '默认关：只显示学院和处理状态'], ['year', '高危提醒显示年级', ''], ['sms', '新危机和升级时短信提醒', '关掉只发站内信'], ['data', '可以看数据看板（汇总）', '始终不能看个人名单和导出']];
const supCard = () => { const ed = isAdm(); return `<div class="card" style="margin-top:14px"><h3>${I('eye')}行政督导能看到什么<span class="sp"></span><small>${ed ? '中心负责人修改，改动记入操作记录' : '只读：由中心负责人修改'}</small></h3>
  <table class="t">${SUPOPT.map(([k, n, sub]) => `<tr><td>${n}${sub ? `<small>${sub}</small>` : ''}</td><td style="width:80px"><span class="sw ${RULES.sup[k] ? 'on' : ''} ${ed ? '' : 'lk'}" ${ed ? `data-act="supT" data-arg="${k}"` : ''} style="cursor:${ed ? 'pointer' : 'default'}"></span></td></tr>`).join('')}</table>
  <p class="note">行政督导只看统计和高危提醒，不能处理个案，也没有权限与设置。</p></div>`; };
/* 设置 · 流转规则：咨询次数 */
const QOPT = [['free', '每学期免费咨询次数', 1, 20], ['add', '单次加次上限', 1, 8], ['cap', '每学期总上限（含加次）', 1, 40]];
const quotaCard = () => { const ed = isAdm(), q = RULES.quota; return `<div class="card" style="margin-top:14px"><h3>${I('cal')}咨询次数<span class="sp"></span><small>${ed ? '中心负责人修改，改动记入操作记录' : '只读：由中心负责人修改'}</small></h3>
  <table class="t">${QOPT.map(([k, n]) => `<tr><td>${n}</td><td style="width:170px">${ed ? `<button class="btn ghost xs" data-act="qCfg" data-arg="${k}|-1">−</button> <b style="display:inline-block;min-width:28px;text-align:center">${q[k]}</b> <button class="btn ghost xs" data-act="qCfg" data-arg="${k}|1">+</button>` : `<b>${q[k]}</b>`} 次</td></tr>`).join('')}</table>
  <p style="margin:12px 0 0"><span class="sw ${RULES.prePick ? 'on' : ''} ${ed ? '' : 'lk'}" ${ed ? 'data-act="prePickT"' : ''} style="cursor:${ed ? 'pointer' : 'default'};vertical-align:middle"></span> 允许学生第一次约预咨询时自己选老师（默认开）</p>
  <p class="note">学生约预咨询时，先建议「由中心安排老师」，学生只选时间；开着这一项时，学生仍可以改成自己选老师，按原来的方式直接约初级咨询师，不进「预咨询分派」。关掉后只能走中心安排。两种方式都不计入咨询次数。</p>
  <p class="note">只算正式咨询：完成或爽约计 1 次；预咨询、老师改约、学生按规则取消不计（开始前 24 小时内取消只用掉一次取消机会）。加次由负责咨询师申请，上级咨询师审批（负责咨询师是 L3 时由中心负责人审批）。危机干预中的学生不计次数。</p></div>`; };
const _settings20 = PAGES.settings; PAGES.settings = function () { let h = _settings20.apply(this, arguments);
  const on = k => h.includes(`class="on" data-act="settab" data-arg="${k}"`);
  if (on('perm')) h = h.replace(/<\/div>$/, supCard() + '</div>'); else if (on('tiers')) h = h.replace(/<\/div>$/, quotaCard() + '</div>');
  return h; };
Object.assign(ACT, {
  supT(k) { if (!isAdm()) return; RULES.sup[k] = !RULES.sup[k]; supMenu(); log(`行政督导可见范围：${SUPOPT.find(x => x[0] === k)[1]} → ${RULES.sup[k] ? '开' : '关'}`, null, { cat: '配置' }); toast('已保存'); },
  prePickT() { if (!isAdm()) return; RULES.prePick = !RULES.prePick; log(`预咨询：允许学生自己选老师 → ${RULES.prePick ? '开' : '关'}`, null, { cat: '配置' }); toast('已保存'); },
  qCfg(a) { if (!isAdm()) return; const [k, d] = a.split('|'), o = QOPT.find(x => x[0] === k), q = RULES.quota, v = Math.max(o[2], Math.min(o[3], q[k] + +d));
    if (k === 'cap' && v < q.free || k === 'free' && v > q.cap) return toast('总上限不能少于免费次数'); q[k] = v; log(`咨询次数：${o[1]} 改为 ${v} 次`, null, { cat: '配置' }); },
});

/* ---------- 1. 咨询次数与加次审批 ---------- */
CORE.wang.qSeed = 6;   // 王思远本学期已经用了 6 次
const QREQ = [];       // { id, sid, by, n, why, st: 待审批 / 已批准 / 已驳回, at, ap: { by, at, why } }
const qCrisis = s => s.stage === 'crisis' || CRISES.some(k => k.sid === s.id && k.st !== 'closed');
const qExtra = s => QREQ.filter(r => r.sid === s.id && r.st === '已批准').reduce((n, r) => n + r.n, 0);
const qTotal = s => Math.min(RULES.quota.cap, RULES.quota.free + qExtra(s));
const qUsed = s => (s.qSeed || 0) + BOOK.filter(b => b.sid === s.id && b.kind === '正式咨询' && ['record', 'done'].includes(b.st) && !b.qFree).length;
const qHeld = s => BOOK.filter(b => b.sid === s.id && b.kind === '正式咨询' && ['audit', 'confirm', 'ok', 'change', 'move', 'adjust', 'pool'].includes(b.st) && !b.qFree).length;
const qLeft = s => qTotal(s) - qUsed(s) - qHeld(s);
const qPend = s => QREQ.find(r => r.sid === s.id && r.st === '待审批');
const qApprovers = by => STAFF[by] && STAFF[by].role === 'L3' ? (by === 'c5' ? ['c4'] : ['c5']) : ['c4', 'c5'];
const qCanAsk = s => S.role !== 'SUP' && s.owner === me() && !qPend(s) && qTotal(s) < RULES.quota.cap;
const qMayApprove = r => S.role === 'L3' && r.by !== me() && qApprovers(r.by).includes(me());
const qCard = s => { const q = RULES.quota, p = qPend(s), L = QREQ.filter(r => r.sid === s.id), x = qExtra(s);
  return `<div class="card"><h3>${I('cal')}本学期咨询次数<span class="sp"></span>${qCrisis(s) ? '<span class="pill r">危机干预中 · 不计次数</span>' : `<small>剩 ${qLeft(s)} 次</small>`}</h3>
    <div class="kv"><span>已用</span><b>${qUsed(s)} 次</b><span>已约未开始</span><b>${qHeld(s)} 次</b><span>本学期共</span><b>${qTotal(s)} 次（免费 ${q.free}${x ? ` + 加次 ${x}` : ''}，上限 ${q.cap}）</b></div>
    ${L.length ? `<table class="t dense" style="margin-top:8px"><tr><th>申请</th><th>次数</th><th>理由</th><th>结果</th></tr>${L.map(r => `<tr><td>${ST(r.by).name}<small>${fmt(r.at)}</small></td><td>+${r.n}</td><td>${esc(r.why)}</td><td>${r.st === '待审批' ? `<span class="pill w">待审批</span>${qMayApprove(r) ? ` <button class="btn pri xs" data-act="qOk" data-arg="${r.id}">批准</button> <button class="btn ghost xs" data-act="mo" data-arg="qNo:${r.id}">驳回</button>` : ''}` : r.st === '已批准' ? `<span class="pill g">已批准</span><small>${ST(r.ap.by).name} ${fmt(r.ap.at)}</small>` : `<span class="pill">已驳回</span><small>${ST(r.ap.by).name}：${esc(r.ap.why)}</small>`}</td></tr>`).join('')}</table>` : ''}
    ${qCanAsk(s) ? `<div style="margin-top:10px"><button class="btn sec xs" data-act="mo" data-arg="qAdd:${s.id}">${I('plus', 's')}申请加次</button></div>` : ''}
    <p class="note">${p ? `已提交加次申请，等${qApprovers(p.by).map(u => ST(u).name).join(' / ')}审批。` : qTotal(s) >= q.cap ? `本学期已到上限 ${q.cap} 次，不能再申请。` : s.owner ? `加次由负责咨询师 ${ST(s.owner).name} 申请，每次最多 ${q.add} 次。` : '有负责咨询师后才能申请加次。'}</p></div>`; };
const _drawer20 = drawer; drawer = function () { let h = _drawer20.apply(this, arguments); const s = S.dw && SU(S.dw.sid);
  if (s && S.dw.tab === 'bk' && !isL1()) h = h.replace('<div class="card"><h3>预约与咨询', qCard(s) + '<div class="card"><h3>预约与咨询'); return h; };
const qMax = s => Math.min(RULES.quota.add, RULES.quota.cap - qTotal(s));
const _modal20 = modal; modal = function () { const [k, id] = (S.mo || '').split(':'), F = S.form;
  if (S.role === 'SUP' && k === 'nDet') return asRole('ADM', () => _modal20.apply(this, arguments));
  if (k === 'qAdd') { const s = SU(id), n = +F.qn || 0;
    return mbox(`申请加次 · ${nm(s)}`, `本学期已用 ${qUsed(s)} 次、已约 ${qHeld(s)} 次，共 ${qTotal(s)} 次。审批人：${qApprovers(me()).map(u => ST(u).name).join(' / ')}`,
      `<p style="margin:6px 0">加几次</p><div class="chips">${Array.from({ length: qMax(s) }, (_, i) => i + 1).map(i => `<button class="${n === i ? 'on' : ''}" data-act="fset" data-arg="qn|${i}">+${i}</button>`).join('')}</div>
      <p style="margin:12px 0 6px">理由（审批人能看到，学生看不到）</p><textarea class="in" style="width:100%;min-height:72px" data-bind="form.qwhy" placeholder="例如：正在处理的议题还需要 3–4 次巩固">${esc(F.qwhy || '')}</textarea>
      <p class="note">每次最多 ${RULES.quota.add} 次，本学期总上限 ${RULES.quota.cap} 次；批准后学生会收到「咨询次数增加了」的消息。</p>`, '提交申请', 'qAddGo', id); }
  if (k === 'qNo') return mbox('驳回加次申请', '', `<textarea class="in" style="width:100%;min-height:72px" data-bind="form.qno" placeholder="写一句原因，申请人能看到">${esc(F.qno || '')}</textarea>`, '驳回', 'qNoGo', id);
  if (k === 'disp') return dispBox(id);
  let h = _modal20.apply(this, arguments);
  if (h && h.includes('预咨询摘要 · ')) { const b = BOOK.find(x => x.id === id), s = b ? SU(b.sid) : SU(id); if (s && !isL1()) h = h.replace(/(<h3>预咨询摘要 · [\s\S]*?<\/h3>)/, `$1${riskBox(s)}`); }
  return h; };
Object.assign(ACT, {
  qAddGo(sid) { const s = SU(sid), F = S.form, n = +F.qn || 0; if (!qCanAsk(s)) return toast('现在不能申请');
    if (n < 1 || n > qMax(s)) return toast('请选择加几次'); if (!(F.qwhy || '').trim()) return toast('请写一句理由');
    const r = { id: 'qr' + (QREQ.length + 1), sid, by: me(), n, why: F.qwhy.trim(), st: '待审批', at: new Date(NOW) }; QREQ.push(r);
    log(`申请加次 +${n}：${r.why}`, s, { cat: '预约', k: 'book' }); qApprovers(me()).forEach(u => notify(u, '站内', `${ST(me()).name} 申请为 ${nm(s)} 加 ${n} 次咨询，请审批`, s.id));
    S.mo = null; S.form = {}; toast('已提交，等上级咨询师审批'); },
  qOk(id) { const r = QREQ.find(x => x.id === id), s = SU(r.sid); if (!qMayApprove(r)) return toast('你不能审批这条申请');
    r.n = Math.min(r.n, RULES.quota.cap - qTotal(s)); r.st = '已批准'; r.ap = { by: me(), at: new Date(NOW) };
    log(`批准加次 +${r.n}（${ST(r.by).name} 申请）`, s, { cat: '预约', k: 'book' }); notify(r.by, '站内', `${nm(s)} 的加次申请已批准：+${r.n} 次`, s.id); toast(`已批准，${nm(s)} 本学期共 ${qTotal(s)} 次`); },
  qNoGo(id) { const r = QREQ.find(x => x.id === id), s = SU(r.sid), why = (S.form.qno || '').trim(); if (!qMayApprove(r)) return toast('你不能审批这条申请'); if (!why) return toast('请写一句原因');
    r.st = '已驳回'; r.ap = { by: me(), at: new Date(NOW), why }; log(`驳回加次申请：${why}`, s, { cat: '预约', k: 'book' }); notify(r.by, '站内', `${nm(s)} 的加次申请未通过：${why}`, s.id); S.mo = null; S.form = {}; toast('已驳回'); },
});
/* 工作台：等我审批的加次、我的学生次数快用完、待分派的预咨询 */
const homeQCard = () => { if (!['L2', 'L3'].includes(S.role)) return '';
  const ap = QREQ.filter(r => r.st === '待审批' && qMayApprove(r)), low = STU.filter(s => s.owner === me() && !qCrisis(s) && qLeft(s) <= 2 && !qPend(s)), dp = S.role === 'L3' ? BOOK.filter(b => b.st === 'disp') : [];
  if (!ap.length && !low.length && !dp.length) return '';
  return `<div class="card"><h3>${I('cal')}咨询次数与预咨询分派</h3>
    ${ap.map(r => { const s = SU(r.sid); return `<div style="display:flex;gap:10px;align-items:center;padding:6px 0"><span class="pill w">待审批</span><b>${nm(s)}</b><span>${ST(r.by).name} 申请 +${r.n} 次 · ${esc(r.why)}</span><span class="sp" style="flex:1"></span><button class="btn pri xs" data-act="qOk" data-arg="${r.id}">批准</button><button class="btn ghost xs" data-act="mo" data-arg="qNo:${r.id}">驳回</button></div>`; }).join('')}
    ${low.map(s => `<div style="display:flex;gap:10px;align-items:center;padding:6px 0"><span class="pill">剩 ${qLeft(s)} 次</span><b>${nm(s)}</b><span>本学期次数快用完了，评估一下是否需要加次</span><span class="sp" style="flex:1"></span><button class="btn sec xs" data-act="open" data-arg="${s.id}">打开档案</button></div>`).join('')}
    ${dp.length ? `<div style="display:flex;gap:10px;align-items:center;padding:6px 0"><span class="pill w">待分派</span><b>${dp.length} 个预咨询</b><span>学生已选好时间，等中心指派老师</span><span class="sp" style="flex:1"></span><button class="btn pri xs" data-act="dispGoTab">去分派</button></div>` : ''}</div>`; };
const _home20b = PAGES.home; PAGES.home = function () { const h = _home20b.apply(this, arguments), c = homeQCard(); return c ? h.replace(/(<div class="tabs htabs">[\s\S]*?<\/div>)/, `$1${c}`) : h; };
/* 打开档案时默认在「预约与咨询」页签 */
const _open20 = ACT.open; ACT.open = function (id) { const r = _open20.apply(this, arguments); if (S.dw && homeQCard && S.page === 'home' && STU.some(s => s.id === id && s.owner === me() && qLeft(s) <= 2)) S.dw.tab = 'bk'; return r; };

/* ---------- 2 + 3. 预咨询分派、风险信息与推荐 ---------- */
BST.disp = '<span class="pill w">待分派</span>';
LY_ACTIVE.push('disp');
BKT.splice(BKT.findIndex(x => x[0] === 'ai') + 1, 0, ['disp', '预咨询分派']);
/* 咨询师擅长和常用的咨询方式（和学生端 DATA.counsellors 的标签对应） */
const CFIT = { c1: { tags: ['学业', '人际', '新生适应'], sch: ['人本倾听', '认知行为'] }, c2: { tags: ['情绪', '睡眠'], sch: ['认知行为', '正念'] }, c3: { tags: ['家庭', '恋爱', '生涯'], sch: ['家庭系统', '人本倾听'] },
  c4: { tags: ['情绪', '睡眠', '学业'], sch: ['认知行为'], senior: 1 }, c5: { tags: ['情绪'], sch: ['认知行为'], senior: 1 } };
const ikSumOf = b => (b && b.intake && b.intake.sum) || [];
const ikV = (b, k) => (ikSumOf(b).find(r => r.k === k) || {}).v || '';
const riskOf = s => { const lv = curLv(s), i9 = s.item9 || 0, cr = qCrisis(s), kN = CRISES.filter(k => k.sid === s.id).length; return { lv, i9, ai: s.ai >= 5, cr, kN, high: lv >= 4 || i9 >= 1 || cr || s.ai >= 5 }; };
const riskBox = s => { const r = riskOf(s), has = s.done || s.walkin === undefined;
  return `<div class="dbox" style="background:${r.high ? 'var(--warn-bg,#fff6e8)' : '#fff'}"><b>${I('alert', 's')}风险信息<span class="sp"></span><small class="note">来自普测和访谈，学生看不到</small></b>
    ${s.done ? `<p>关注等级 ${lvB(r.lv)} · PHQ-9 第 9 题：${['完全不会', '好几天', '一半以上的天数', '几乎每天'][r.i9]} · 访谈危机表达：${r.ai ? '有' : '无'} · 危机记录：${r.kN ? `${r.kN} 条${r.cr ? '（进行中）' : ''}` : '无'}</p>` : '<p>没有普测记录（名单外或 3 个月内没做），请分派的老师自己判断。</p>'}</div>`; };
const slotFree = (u, b) => u === b.cid || (SCHED[u] && SCHED[u][b.day] ? SCHED[u][b.day][b.t] === 'open' : false);
const recoOf = b => { const s = SU(b.sid), r = riskOf(s), tp = ikV(b, 'topics') + ' ' + (s.dirs || []).join(' '), sc = ikV(b, 'school');
  return Object.keys(CFIT).filter(u => (STAFF[u].pre || r.high && CFIT[u].senior) && u !== s.excl && slotFree(u, b)).map(u => { const f = CFIT[u], why = [];
    const tg = f.tags.filter(t => tp.includes(t)); if (tg.length) why.push(`擅长${tg.join('、')}`);
    const sh = f.sch.filter(x => sc.includes(x)); if (sh.length) why.push(`学生想试${sh.join('、')}`);
    if (r.high && f.senior) why.push('风险较高，建议高级咨询师');
    return { u, why, score: tg.length * 2 + sh.length * 2 + (r.high ? (f.senior ? 3 : 0) : (STAFF[u].pre ? 1 : 0)) }; }).sort((a, b) => b.score - a.score); };
/* 演示数据：1 个已经选好时间、等分派的预咨询 */
(() => { const s = STU.find((x, i) => i > 24 && !CORE_IDS().includes(x.id) && !activeBook(x) && x.stage !== 'crisis'); if (!s) return;
  for (let d = 1; d < DAYS.length; d++) for (let t = 0; t < TIMES.length; t++) if (SCHED.c2[d] && SCHED.c2[d][t] === 'open') { SCHED.c2[d][t] = 'bk';
    BOOK.push(bk({ id: 'bd1', sid: s.id, cid: 'c2', day: d, t, st: 'disp', src: '学生端提交 · 待中心分派' }, 3)); return; } })();
function CORE_IDS() { return Object.values(CORE).map(s => s.id); }
const dispPage = () => { const L = BOOK.filter(b => b.st === 'disp').sort((a, b) => a.at - b.at);
  return `<div class="card"><h3>${I('inbox')}预咨询待分派（${L.length}）<span class="sp"></span><small>学生只选时间，中心指派老师；指派后老师确认才算约好</small></h3>
    ${L.length ? `<table class="t"><tr><th>学生</th><th>想约的时间</th><th>等了多久</th><th>风险</th><th>预咨询摘要</th><th>推荐</th><th></th></tr>${L.map(b => { const s = SU(b.sid), r = riskOf(s), rc = recoOf(b).slice(0, 2), it = b.intake;
      return `<tr class="${hrs(b.at) > RULES.lim.disp - 4 ? 'crit' : ''}"><td><b>${nm(s)}</b><small>${s.college}</small></td><td>${slotTxt(b)}<small>${b.mode}${STAFF[b.cid] ? ` · ${STAFF[b.cid].campus || ''}` : ''}</small></td><td>${dur(hrs(b.at))}<small>${RULES.lim.disp} 小时内分派</small></td>
        <td>${r.high ? '<span class="pill r">较高</span>' : '<span class="pill">一般</span>'}<small>${lvB(r.lv)}</small></td><td>${it && it.st === 'sent' ? '<span class="pill g">已发送</span>' : it && it.st === 'draft' ? '<span class="pill">没聊完</span>' : '<span class="note">还没聊</span>'}</td>
        <td>${rc.map(x => `${ST(x.u).name}<small>${x.why.join('；') || '这个时间有空'}</small>`).join('') || '<span class="note">这个时间没有合适的老师</span>'}</td><td><button class="btn pri xs" data-act="mo" data-arg="disp:${b.id}">指派</button></td></tr>`; }).join('')}</table>` : `<div class="empty"><img src="${MASCOT}" alt="">没有等待分派的预咨询</div>`}
    <p class="note">推荐按学生选的话题、想要的咨询方式、风险信息和这个时段谁有空排序；风险较高的学生优先推荐高级咨询师。推荐只给分派的人看，学生看不到。超过 ${RULES.lim.disp} 小时没分派，自动进入待办池。</p></div>`; };
function dispBox(id) { const b = BOOK.find(x => x.id === id), s = SU(b.sid), rc = recoOf(b), top = rc.slice(0, 2).map(x => x.u), pick = S.form.dc || top[0] || '';
  const it = ikSumOf(b).filter(r => r.v);
  return mbox(`指派预咨询 · ${nm(s)}`, `${slotTxt(b)} · ${b.mode} · 学生 ${fmt(b.at)} 提交`, riskBox(s)
    + (it.length ? `<div class="dbox" style="background:#fff"><b>${I('chat', 's')}预咨询摘要</b>${it.map(r => `<p><b>${esc(r.name)}</b>：${esc(r.v)}</p>`).join('')}</div>` : '<p class="note">学生还没和预咨询小屿聊完，可以先按普测信息分派。</p>')
    + `<p style="margin:10px 0 6px">指派给（只列这个时段有空的老师）</p>${rc.map(x => `<button class="acc ${pick === x.u ? 'on' : ''}" style="width:100%;text-align:left;margin-bottom:6px" data-act="fset" data-arg="dc|${x.u}"><span><b>${ST(x.u).name} · ${STAFF[x.u].title}</b>${top.includes(x.u) ? ' <span class="pill g">推荐</span>' : ''}<small>${x.why.join('；') || '这个时间有空'}</small></span></button>`).join('') || '<p class="note">这个时段没有老师有空，可以先联系学生改时间。</p>'}
    <p class="note">指派后会通知这位老师，老师确认后学生才看到老师的名字。</p>`, rc.length ? '指派' : '', 'dispGo', id, 1); }
Object.assign(ACT, {
  dispGoTab() { go('booking'); S.tabs.booking = 'disp'; },
  dispGo(id) { const b = BOOK.find(x => x.id === id), s = SU(b.sid), rc = recoOf(b), u = S.form.dc || (rc[0] && rc[0].u); if (!u || !rc.some(x => x.u === u)) return toast('请选择老师');
    if (u !== b.cid) { setSlot(b.cid, b.day, b.t, 'open'); setSlot(u, b.day, b.t, 'bk'); }
    b.cid = u; b.st = 'confirm'; b.at = new Date(NOW); b.src = '中心分派'; b.disp = { by: me(), at: new Date(NOW) };
    log(`指派预咨询给 ${ST(u).name}，${slotTxt(b)}`, s, { cat: '预约', k: 'book' }); notify(u, '站内 + 短信', `中心指派给你 1 个预咨询：${nm(s)} ${slotTxt(b)}，请确认`, b.id);
    S.mo = null; S.form = {}; toast(`已指派给 ${ST(u).name}，等老师确认`); },
});
const _booking20 = PAGES.booking; PAGES.booking = function () { if (isL1()) return _booking20.apply(this, arguments);
  const disp = S.tabs.booking === 'disp' && S.role === 'L3'; if (S.tabs.booking === 'disp' && !disp) S.tabs.booking = 'man';
  if (disp) S.tabs.booking = 'man'; let h; try { h = _booking20.apply(this, arguments); } finally { if (disp) S.tabs.booking = 'disp'; }
  const n = BOOK.filter(b => b.st === 'disp').length;
  h = h.replace(/<button class="[^"]*" data-act="btab" data-arg="disp">预咨询分派<\/button>/, S.role === 'L3' ? `<button class="${disp ? 'on' : ''}" data-act="btab" data-arg="disp">预咨询分派${n ? `<i class="r">${n}</i>` : ''}</button>` : '');
  if (!disp) return h;
  const i = h.indexOf('</div>', h.indexOf('<div class="tabs">')) + 6;
  return h.slice(0, i).replace('class="on" data-act="btab" data-arg="man"', 'class="" data-act="btab" data-arg="man"') + dispPage(); };
/* 超时进待办池；危机升级同时提醒行政督导 */
const _tick20 = tick; tick = function () { const e0 = CRISES.map(k => k.esc || 0), r = _tick20.apply(this, arguments);
  CRISES.forEach((k, i) => { if ((k.esc || 0) > (e0[i] || 0)) supNotify(k, `高危提醒：${supWho(SU(k.sid))}的危机已 ${dur(hrs(k.urgAt || k.at))} 无人接收，已升级到${k.esc >= 2 ? '分管领导' : '中心负责人'}`); });
  BOOK.forEach(b => { if (b.st === 'disp' && hrs(b.at) >= RULES.lim.disp) { b.st = 'pool'; b.src = '预咨询超时未分派 → 待办池'; notify('c5', '站内', '1 个预咨询超时未分派，进入待办池', b.id); log('预咨询超时未分派，自动进入待办池', SU(b.sid), { sys: 1, cat: '预约', k: 'book' }); } });
  return r; };
/* 两端联动：学生提交的预咨询是「待分派」；加次结果同步给学生端 */
const _lyIn20 = LY_in; LY_in = function (ev) { const r = _lyIn20.apply(this, arguments);
  if (ev.t === 'book' && ev.wait) { const s = LY_CORE()[ev.core], b = s && lyBook(s);
    if (b && b.kind === '预咨询') { b.st = 'disp'; b.fresh = false; b.src = '学生端提交 · 待中心分派'; for (let i = NOTI.length - 1; i >= 0; i--) if (NOTI[i].ref === b.id && NOTI[i].to === b.cid) NOTI.splice(i, 1);
      notify('c5', '站内', `${nm(s)} 选好了预咨询时间，等中心分派老师`, b.id); render();   /* 未登录也重画一次，让外壳拿到「待分派」的状态 */ return `${s.name} 选好了预咨询时间，已出现在「预约咨询 · 预咨询分派」里`; } }
  return r; };
const _lySnap20 = LY_snap; LY_snap = function () { const o = _lySnap20.apply(this, arguments); o.__cfg = Object.assign({}, o.__cfg, { prePick: RULES.prePick }); o.__quota = Object.fromEntries(Object.entries(LY_CORE()).map(([k, s]) => [k, qExtra(s)])); return o; };
