"""Batch 5: core student invitation round trips using real 1440px UI clicks."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def scope(browser):
    c = Case(browser, 'B5-1-核心范围与演示入口')
    try:
        c.login()
        c.check(list(c.a.evaluate('Object.keys(LY_snap().__ivc)')) == ['chen'], '仅符合等级且非危机中的核心陈嘉怡联动')
        c.check(c.a.evaluate('ivb().list.filter(x=>x.sid===LY_CORE().chen.id).length') == 1, '核心学生按学号去重补入一次')
        c.student('B')
        c.wait(c.s, 'S._ivcManaged===true')
        c.s.locator('#zapT').check()
        c.check(c.s.locator('[data-act=zIvc]').count()==0 and c.s.locator('[data-act=zIvQ]').count()==1, '陈嘉怡由机构发卡，保留没号演示开关')
        c.student('A')
        c.wait(c.s, '!S._ivcManaged')
        c.check(c.s.locator('[data-act=zIvc]').count()==1, '林晓继续使用学生演示卡入口')
        c.shot('林晓保留演示卡')
    finally:
        c.close()
    return c.checks


def send_card(c):
    c.login()
    c.student('B')
    c.wait(c.s, 'S._ivcManaged===true')
    c.click(c.a, '[data-arg="ivSend:4"]')
    c.check('确认后才发' in c.a.inner_text('#modal'), '机构发卡先确认')
    c.click(c.a, '[data-act=ivSendGo]')
    c.wait(c.s, 'S.ivc && S.ivc.st==="wait"')
    x = c.a.evaluate('ivb().list.find(x=>x.sid===LY_CORE().chen.id)')
    c.check(c.s.evaluate('S.ivc.due') == x['due'] and x['due'] in c.s.inner_text('#modal'), '卡片截止与机构端一致')
    text = c.s.inner_text('#modal')
    c.check(all(w not in text for w in ['等级','分数','普测筛出','排队名次']), '学生邀约卡没有敏感分层信息')
    return x


def entry(c, sid, previous):
    c.click(c.a, f'[data-act=ivEntryGo][data-arg="{sid}"]')
    c.check(c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).st', sid) == previous, '点给入口只打开确认弹窗')
    c.check('入口 48 小时有效' in c.a.inner_text('#modal') and '老师确认' in c.a.inner_text('#modal'), '确认弹窗解释有效期与提交后仍等老师确认')
    c.click(c.a, '[data-act=ivEntryOk]')
    c.wait(c.s, 'S.ivc.st==="entry"')
    c.check(c.s.evaluate('S.ivc.edue') == c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).edue', sid), '老师确认后两端入口截止一致')
    c.select(c.s, '#jump', 'home')
    c.check('选和老师见面的时间' in c.s.inner_text('#app'), '学生首页出现明确的选时间待办')
    c.click(c.s, '.todo [data-act=go][data-arg=book]')
    c.check('提交后等老师确认' in c.s.inner_text('#app'), '选时间页提示提交申请后仍等老师确认')


def full_roundtrip(browser):
    c = Case(browser, 'B5-1-陈嘉怡邀约完整来回')
    try:
        x = send_card(c)
        sid, responsible = x['sid'], x['resp']
        c.shot('学生收到机构邀约卡')
        c.click(c.s, '#modal [data-act=close]')
        c.s.locator('#zapT').check()
        c.click(c.s, '[data-act=zIvQ]')
        c.check(c.s.evaluate('S.ivQ'), '实际开启没号要排队')
        c.click(c.s, '[data-act=ivcOpen]')
        c.click(c.s, '[data-act=ivNo]')
        c.check('之后想聊可以随时' in c.s.inner_text('#modal'), '不参加确认说明后续仍可预约')
        c.click(c.s, '#modal [data-act=ivcOpen]')
        c.click(c.s, '[data-act=ivAcc]')
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).st==="ik"')
        c.check(c.s.evaluate('S.ik.inv && S.ik.i===0'), '接受即进入高危预咨询第一题')
        c.click(c.s, '[data-act=ikTog]')
        c.click(c.s, '[data-act=ikNextQ]')
        draft = '最近学习任务比较多，希望和老师聊聊学习安排以及休息方法。'
        c.s.locator('#ikTxt').fill(draft)
        c.steps.append({'操作':'填写当前第二题后中途保存','内容':draft})
        c.click(c.s, '[data-act=ikX]')
        c.check('首页' in c.s.inner_text('#modal'), '关闭说明指出从首页续办')
        c.click(c.s, '[data-act=ikSave]')
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).ik.st==="draft"')
        c.check(c.a.evaluate('(sid)=>{const it=ivb().list.find(x=>x.sid===sid).ik;return !it.sum && !it.ans}', sid), '老师端只收到草稿状态，不收到回答')
        c.click(c.a, '[data-act=btab][data-arg=ai]')
        row = c.a.locator('tr').filter(has_text='陈嘉怡').filter(has_text='主动邀约')
        c.check(row.locator('button').count()==0 and '已保存，未发送' in row.inner_text(), 'AI列表草稿不能打开摘要')
        c.click(c.s, '[data-act=ivIkGo]')
        c.check(c.s.locator('#ikTxt').input_value()==draft, '中途关掉后从首页恢复第二题原输入')
        c.intake(text=draft)
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).st==="queue"')
        c.check(c.s.evaluate('S.ivc.st')=='queue', '发送后两端进入排队状态')
        c.check(c.a.evaluate('(sid)=>{const x=ivb().list.find(x=>x.sid===sid);return x.ik.st==="sent" && x.ik.sum.some(r=>r.v.includes("学习安排"))}', sid), '已确认发送的摘要回到批次')
        c.check(c.a.evaluate('([sid,to])=>NOTI.some(n=>n.to===to && n.ref===sid && n.t.includes("排队等入口"))', [sid,responsible]), '排队通知负责老师')
        c.shot('学生排队提示')
        c.click(c.s, '#modal [data-act=close]')
        c.click(c.a, '[data-act=btab][data-arg=inv]')
        c.click(c.a, f'[data-act=ivIkOpen][data-arg="{sid}"]')
        c.check(draft in c.a.inner_text('#modal'), '老师能实际打开完整已发送摘要')
        c.shot('机构排队学生摘要')
        c.click(c.a, '[data-act=moClose]')
        entry(c, sid, 'queue')
        c.click(c.s, '[data-act=ivFit]')
        args = c.s.locator('[data-act=ivFitT]').evaluate_all('(els)=>els.slice(0,4).map(e=>e.dataset.arg)')
        for arg in args[:3]:
            c.click(c.s, f'[data-act=ivFitT][data-arg="{arg}"]')
        c.click(c.s, f'[data-act=ivFitT][data-arg="{args[3]}"]')
        c.check(c.s.evaluate('S.ivFitSel.length')==3, '最多选择三个方便时间')
        c.click(c.s, '[data-act=ivFitOk]')
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).st==="nofit"')
        c.check(c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).fit', sid)==args[:3], '三个方便时间原样回到机构端')
        row = c.a.locator('tr').filter(has=c.a.locator(f'[data-act=ivEntryGo][data-arg="{sid}"]'))
        c.check(all(arg in row.inner_text() for arg in args[:3]), '批次名单实际显示三个方便时间')
        c.check(c.a.evaluate('([sid,to])=>NOTI.some(n=>n.to===to && n.ref===sid && n.t.includes("时间都不合适"))', [sid,responsible]), '时间不合适通知负责老师')
        c.shot('机构方便时间与给入口')
        entry(c, sid, 'nofit')
        pick = c.s.evaluate("(()=>{for(let d=0;d<DAYS.length;d++)for(let t=0;t<DATA.times.length;t++)if(slotState(ci('c1'),d,t)==='open')return {d,t};throw Error('No real opening')})()")
        c.click(c.s, f'[data-act=day][data-arg="{pick["d"]}"]')
        c.click(c.s, f'[data-act=pickSlot][data-arg="c1:{pick["d"]}:{pick["t"]}"]')
        c.click(c.s, '[data-act=bookSubmit]')
        c.wait(c.a, 'LY_snap().chen && LY_snap().chen.st==="confirm"')
        bid = c.a.evaluate('LY_snap().chen.id')
        c.check(c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).st', sid)=='sub', '批次显示已申请，人工咨询中仍待确认')
        c.check(c.a.evaluate('(id)=>{const b=BOOK.find(x=>x.id===id);return b.src==="主动邀约" && b.intake.st==="sent"}', bid), '申请保留主动邀约来源及已发送摘要')
        c.check('申请' in c.s.inner_text('#modal') and '确认' in c.s.inner_text('#modal'), '学生提交弹窗说明申请和老师确认')
        c.shot('学生申请已提交')
        c.login('c1|L2')
        c.click(c.a, '[data-act=btab][data-arg=man]')
        c.check(c.a.locator('.bkpin').locator(f'[data-act=bOk][data-arg="{bid}"]').count()==1, '对应咨询师待确认区出现这条申请')
        c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
        c.wait(c.s, 'S.bk.st==="已确认"')
        c.check(c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).st', sid)=='ok' and c.s.evaluate('S.ivc.st')=='ok', '老师确认后批次和学生预约均已确认')
        c.select(c.s, '#jump', 'mybook')
        c.check('已确认' in c.s.inner_text('#app'), '学生我的预约显示已确认')
        c.shot('学生已确认的邀约预约')
    finally:
        c.close()
    return c.checks


def declined(browser):
    c = Case(browser, 'B5-1-不参加回到负责老师')
    try:
        x = send_card(c)
        c.click(c.s, '[data-act=ivNo]')
        c.click(c.s, '[data-act=ivNoOk]')
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={x["sid"]!r}).st==="no"')
        c.check(c.a.evaluate('([sid,to])=>NOTI.some(n=>n.to===to && n.ref===sid && n.t.includes("这次不参加"))', [x['sid'],x['resp']]), '不参加同步到批次并通知负责老师')
        c.shot('学生不参加后')
    finally:
        c.close()
    return c.checks


TESTS = {'scope': scope, 'full': full_roundtrip, 'no': declined}
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=list(TESTS))
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = launch(p)
        try:
            total = sum(fn(browser) for name,fn in TESTS.items() if not args.only or name==args.only)
        finally:
            browser.close()
    print(f'fix_b5: {total} passed, 0 failed', flush=True)
