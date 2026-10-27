/* =====================================================================
   demo-v2.0 · 试用意见（10/23 批）· 学生端
   1. 每学期 8 次免费咨询（只算正式咨询）：完成或爽约计 1 次，预咨询、老师改约、按规则取消不计；
      加次由负责咨询师申请、上级咨询师批准，学期总上限 20 次；危机支持期间的咨询不计次数
   2. 预咨询只选时间：还没有负责咨询师时，预约中心只按校区和时间列空档，不显示老师；
      提交后「中心安排中」，中心指派老师、老师确认后才约好
===================================================================== */
const SESS = { free: 8, cap: 20 };
const sess = () => S.sess || (S.sess = { used: SCENES[S.scen].returning ? 6 : 0, extra: 0 });
const sessCrisis = () => (S.tasks || []).some(t => t.crisis) || !!(S.ik && S.ik.crisis) || !!S.callback;
const sessTotal = () => Math.min(SESS.cap, SESS.free + sess().extra);
const sessLeft = () => sessTotal() - sess().used - (S.bk && S.bk.kind === '正式咨询' ? 1 : 0);
function sessSetExtra(n) { const q = sess(), add = n - q.extra; q.extra = n;
  if (add > 0) addMsg('cal', [`本学期的咨询次数增加了 ${add} 次`, `${add} more sessions this semester`], [`你的咨询师为你申请、中心已批准。本学期还可以约 ${sessLeft()} 次。`, `Your counsellor asked and UCC approved. You can book ${sessLeft()} more this semester.`], 'book'); }
const _reset20 = reset; reset = function () { const r = _reset20.apply(this, arguments); S.sess = null; sess(); return r; };
/* 次数说明：只在有负责咨询师（约的是正式咨询）时出现 */
function sessLine() { if (!S.owner) return ''; const n = sessLeft(), cr = sessCrisis(), x = sess().extra;
  const t = cr ? L('现在这段时间的咨询不计入次数，需要的时候随时约。', 'Sessions right now don’t count toward your limit — book whenever you need.')
    : n > 0 ? L(`本学期还可以约 <b>${n}</b> 次咨询（每学期 ${SESS.free} 次${x ? `，另加 ${x} 次` : ''}）`, `You can book <b>${n}</b> more session${n > 1 ? 's' : ''} this semester (${SESS.free} per semester${x ? `, plus ${x}` : ''})`)
    : L('本学期的咨询次数已经约满。如果还需要，可以和你的咨询师商量，由 TA 向中心申请增加。', 'You’ve used this semester’s sessions. If you need more, talk to your counsellor — they can ask UCC for extra sessions.');
  return `<div class="sess ${n <= 0 && !cr ? 'out' : ''}">${I('cal', 's')}<span class="grow">${t}</span>${!cr && n <= 2 && sessTotal() < SESS.cap ? `<span class="zap" data-act="zQuota">⚡ ${L('演示 · 模拟加次通过', 'Demo: extra sessions approved')}</span>` : ''}</div>`; }
const _quotaBox20 = quotaBox; quotaBox = function () { return sessLine() + _quotaBox20.apply(this, arguments); };
const _pick20 = ACT.pickSlot; ACT.pickSlot = function () {
  if (S.owner && !S.resch && !sessCrisis() && sessLeft() <= 0) { S.info = { ico: 'cal', title: L('本学期的咨询次数已经约满', 'You’ve used this semester’s sessions'), body: L(`每学期可以约 ${SESS.free} 次咨询。如果还需要，可以和你的咨询师商量，由 TA 向中心申请增加。<br>需要马上和人聊聊，可以拨打 24 小时热线 1767。`, `You can book ${SESS.free} sessions each semester. If you need more, talk to your counsellor — they can ask UCC for extra sessions.<br>Need to talk now? Call 1767, 24 hours.`) }; S.modal = 'info'; return; }
  const r = _pick20.apply(this, arguments); if (S.pick && preMode()) S.pick.pre = true; return r; };
const _done20 = ACT.zDone; ACT.zDone = function () { if (S.bk && S.bk.kind === '正式咨询' && !sessCrisis()) sess().used++; return _done20.apply(this, arguments); };
ACT.zQuota = () => { sessSetExtra(Math.min(SESS.cap - SESS.free, sess().extra + 4)); toast(L('演示：加次已通过', 'Demo: extra sessions approved')); };

/* ---------- 2. 预咨询只选时间 ---------- */
const preMode = () => !S.owner && !S.resch;
const okPre = c => canB(c) && c.pool === 'pre' && c.campus === S.campus;
const preCampuses = () => DATA.campuses.filter(x => DATA.counsellors.some(c => canB(c) && c.pool === 'pre' && c.campus === x));
const _cal20 = calendar; calendar = function () { if (!preMode()) return _cal20.apply(this, arguments);
  if (!preCampuses().includes(S.campus)) S.campus = preCampuses()[0] || S.campus;
  const chips = `<div class="chips" style="margin-bottom:14px">${preCampuses().map(x => `<button class="${S.campus === x ? 'on' : ''}" data-act="bCampus" data-arg="${x}">${I('pin', 's')} ${T(x)}</button>`).join('')}</div>`;
  return chips + _cal20.call(this, okPre).replace(/<span class="avs">[\s\S]*?<\/span><\/button>/g, '</button>').replace(/ title="[^"]*"/g, ''); };
/* 同一时间只列一个按钮：哪位老师有空由系统先替学生留着，中心再指派 */
const _slots20 = daySlots; daySlots = function () { if (!preMode()) return _slots20.apply(this, arguments);
  if (S.day < 0) return `<div class="empty">${L('这个校区未来 30 天暂时没有可约时段', 'No openings at this campus in the next 30 days')}</div>`;
  const cs = DATA.counsellors.filter(okPre), ts = DATA.times.map((_, ti) => { const c = cs.find(x => slotState(ci(x.id), S.day, ti) === 'open'); return [ti, c, !c && cs.some(x => slotState(ci(x.id), S.day, ti) === 'taken')]; }).filter(x => x[1] || x[2]);
  return `<div class="sect" id="slots" style="margin-top:6px">${fmtDay(DAYS[S.day])}</div><div class="crow"><div class="who"><span class="pre-av">${I('users')}</span><div><b>${L('由中心安排老师', 'UCC arranges your counsellor')}</b><small>${T(S.campus)}${SEP()}${L('预咨询约 30 分钟', 'Intake chat, about 30 min')}</small></div></div>
    <div class="times">${ts.map(([ti, c]) => c ? slotBtn(c, S.day, ti, 'open') : `<button class="tm full" disabled>${DATA.times[ti]} ${L('已约满', 'Full')}</button>`).join('')}</div></div>`; };
const _book20 = PAGES.book; PAGES.book = function () { const pre = preMode(); if (pre) S.bookTab = 'time';
  let h = _book20.apply(this, arguments);
  if (pre) h = h.replace(/<button class="[^"]*" data-act="bTab" data-arg="\w+">[^<]*<\/button>/g, '').replace(L('只显示你可以预约的老师。需至少提前 24 小时预约。', 'Showing counsellors you can book. Book at least 24 hours ahead.'), L('第一次见面由中心根据你的情况安排老师，你只需要选时间。需至少提前 24 小时预约。', 'For your first meeting, UCC picks the right counsellor for you — just choose a time. Book at least 24 hours ahead.'));
  else if (!S.resch) h = h.replace('<div class="tabs">', sessLine() + '<div class="tabs">');
  return h; };
const _submitM20 = MODALS.submit; MODALS.submit = function () { const h = _submitM20.apply(this, arguments), p = S.pick; if (!p || !p.pre) return h; const c = C(p.cid);
  return h.replace(`${who(c)}${SEP()}${T(c.role)}`, L('由中心安排老师（提交后通知你）', 'Arranged by UCC — we’ll let you know')); };
const _bookSubmit20 = ACT.bookSubmit; ACT.bookSubmit = function () { const pre = !!(S.pick && S.pick.pre && !S.resch && !S.bk), r = _bookSubmit20.apply(this, arguments);
  if (pre && S.bk && S.bk.kind === '预咨询') S.bk.wait = true; return r; };
/* 中心安排好老师（机构端指派或演示按钮）；演示里直接点「老师确认」也算安排好了 */
ACT.zAssign = cid => { const b = S.bk; if (!b || !b.wait) return; if (cid && C(cid)) b.cid = cid; b.wait = false;
  addMsg('users', [`中心为你安排了${whoZ(b.cid)}`, `UCC arranged ${C(b.cid).name} for you`], [`预咨询 ${bkWhen(b)}，等老师确认后就约好了。`, `Intake chat ${bkWhen(b)}. It’s booked once they confirm.`], 'mybook');
  toast(L(`中心为你安排了${who(C(b.cid))}`, `UCC arranged ${C(b.cid).name}`)); };
const _confirm20 = ACT.zConfirm; ACT.zConfirm = function () { if (S.bk && S.bk.wait) S.bk.wait = false; return _confirm20.apply(this, arguments); };
const _myBook20 = PAGES.mybook; PAGES.mybook = function () { let h = _myBook20.apply(this, arguments); const b = S.bk; if (!b || !b.wait) return h;
  return h.replace(/<span class="zap" data-act="z(Confirm|Decline|Late|Move)">[^<]*<\/span>/g, '').replace('<div class="bb">', `<div class="bb"><div class="warnbar"><span class="ico">${I('users')}</span><div class="grow"><b>${L('中心正在为你安排老师', 'UCC is arranging your counsellor')}</b><small>${L('通常 1 个工作日内安排好，安排好会通知你，之后老师确认就约好了。这个时段一直为你保留。', 'Usually within 1 working day. We’ll let you know, then the counsellor confirms. This time is held for you.')}</small></div><span class="zap" data-act="zAssign">⚡ ${L('演示 · 模拟中心安排老师', 'Demo: UCC arranges')}</span></div>`); };
/* 安排好之前，学生看到的都是「中心安排的老师」，不出现留位老师的名字和头像 */
const waitMask = h => { const b = S && S.bk; if (typeof h !== 'string' || !b || !b.wait) return h; const c = C(b.cid); if (!c) return h;
  return h.split(avatar(c)).join(`<span class="pre-av">${I('users', 's')}</span>`).split(`data-act="cp" data-arg="${c.id}"`).join('disabled')
    .split(whoZ(b.cid)).join(L('中心安排的老师', 'your UCC counsellor')).split(who(c)).join(L('中心安排的老师', 'your UCC counsellor')); };
[PAGES, MODALS].forEach(o => Object.keys(o).forEach(k => { const f = o[k]; if (typeof f === 'function') o[k] = function () { return waitMask(f.apply(this, arguments)); }; }));
