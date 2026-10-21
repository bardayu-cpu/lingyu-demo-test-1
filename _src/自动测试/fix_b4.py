"""Batch 4: click checks for invitation counts, configuration, audit and interface."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def counters(browser):
    c = Case(browser, 'B4-1-八张统计卡与名单')
    try:
        c.login()
        for key in ['sent', 'acc', 'no', 'ik', 'queue', 'entry', 'sub', 'ok']:
            card = c.a.locator(f'[data-act=ivF][data-arg="{key}"]')
            n = int(card.locator('b').inner_text())
            c.click(c.a, f'[data-act=ivF][data-arg="{key}"]')
            table = c.a.locator('.card').filter(has=c.a.locator('h3').filter(has_text='当前筛选')).locator('table')
            c.check(table.locator('tr').filter(has=c.a.locator('td b')).count() == n, key + ' 名单人数等于数字卡')
            c.check(f'· {n} 人' in c.a.locator('h3').filter(has_text='当前筛选').inner_text(), key + ' 标明当前筛选及人数')
        c.check('累计 · 其中待回复' in c.a.inner_text('#pg'), '累计发卡和待回复口径写清')
        c.shot('统计筛选与人数')
    finally:
        c.close()
    return c.checks


def eligibility(browser):
    c = Case(browser, 'B4-2-主动邀约等级')
    try:
        c.login()
        before = c.a.evaluate('ivb().list.map(x=>({sid:x.sid,st:x.st}))')
        student = c.a.evaluate('STU.find(s=>curLv(s)===3 && !ivb().list.some(x=>x.sid===s.id))')
        c.check(bool(student), '使用未在批次的三级学生验证新增门槛')
        c.click(c.a, '[data-act=btab][data-arg=pool]')
        c.select(c.a, '[data-pool=ivLv]', '4')
        c.click(c.a, '[data-act=btab][data-arg=inv]')
        c.click(c.a, '[data-arg="ivAdd:"]')
        c.check(c.a.locator('[data-act=ivPickT]').evaluate_all('(els)=>els.every(e=>curLv(SU(e.dataset.arg))>=4)'), '勾选候选只列四级及以上')
        c.click(c.a, '[data-act=fset][data-arg="ivt|paste"]')
        c.a.locator('[data-bind="form.ivIds"]').fill(student['sid'])
        c.steps.append({'操作':'粘贴三级学生学号','内容':student['sid']})
        c.click(c.a, '[data-act=ivAddGo]')
        c.check('未达主动邀约等级（4 级及以上）' in c.a.inner_text('#modal'), '核对解释等级不够，进入对不上')
        c.check(c.a.evaluate('ivb().list.map(x=>({sid:x.sid,st:x.st}))') == before, '学生未加入且原批次学生与状态不变')
        c.shot('未达等级核对结果')
    finally:
        c.close()
    return c.checks


def piles(browser):
    c = Case(browser, 'B4-3-核对结果留在批次')
    try:
        c.login()
        people = c.a.evaluate("""(()=>{const B=ivb(), crisis=STU.find(s=>curLv(s)>=RULES.pool.ivLv && inCrisis(s.id)), booked=STU.find(s=>curLv(s)>=RULES.pool.ivLv && !inCrisis(s.id) && activeBook(s));
          // Isolate first-time exclusion of these two seeded students; keep all other existing piles.
          B.piles.skip=B.piles.skip.filter(x=>x.sid!==crisis.id); B.piles.has=B.piles.has.filter(x=>x.sid!==booked.id);
          return {crisis,booked,before:Object.fromEntries(Object.entries(B.piles).map(([k,v])=>[k,v.length]))};})()""")
        ids = 'NO-SUCH-STUDENT\n' + people['crisis']['sid'] + '\n' + people['booked']['sid']
        c.steps.append({'测试准备':'将两名种子学生从对应核对堆移出，用于验证首次追加；其他既有条目保留'})
        for repeat in [False, True]:
            c.click(c.a, '[data-arg="ivAdd:"]')
            c.click(c.a, '[data-act=fset][data-arg="ivt|paste"]')
            c.a.locator('[data-bind="form.ivIds"]').fill(ids)
            c.steps.append({'操作':'粘贴不存在、危机中、已有预约的三个学号','内容':ids})
            c.click(c.a, '[data-act=ivAddGo]')
            for label in ['对不上（1）', '不走预约队列（1）', '已有安排（1）']:
                c.check(label in c.a.inner_text('#modal'), '核对弹窗：' + label)
            c.click(c.a, '[data-act=moClose]')
            after = c.a.evaluate('Object.fromEntries(Object.entries(ivb().piles).map(([k,v])=>[k,v.length]))')
            c.check(all(after[k] == people['before'][k] + 1 for k in ['bad','skip','has']), '关闭后各堆加一；再次加入按学号去重' if repeat else '关闭后批次三堆人数各加一')
        c.check(c.a.evaluate('ivb().piles.bad.some(x=>x.id==="NO-SUCH-STUDENT" && x.why==="不在名册")'), '对不上保留学号和具体原因')
        c.shot('关闭弹窗后保留核对人数')
    finally:
        c.close()
    return c.checks


def pool_notifications(browser):
    c = Case(browser, 'B4-4-号池变更通知')
    try:
        c.login()
        c.click(c.a, '[data-act=btab][data-arg=pool]')
        def changes(label, action):
            n = c.a.evaluate('NOTI.length')
            action()
            notices = c.a.evaluate('(n)=>NOTI.slice(0,NOTI.length-n)', n)
            text = c.a.evaluate('AUDIT[0].t')
            c.check(all(sum(x['to']==uid and x['t']==text for x in notices)==1 for uid in ['c1','c2','c3','c4']), label + '中心其他四位老师各收到一条与日志相同的站内通知')
        def quota():
            field = c.a.locator('[data-pool^="col|"]').first
            field.fill('8')
            field.press('Tab')
            c.steps.append({'操作':'修改学院额度为8并移开焦点'})
        changes('学院额度：', quota)
        changes('主动邀约等级：', lambda: c.select(c.a, '[data-pool=ivLv]', '4'))
        changes('暂留额度：', lambda: c.click(c.a, '[data-act=poolH][data-arg="-2"]'))
        c.login('c1|L2')
        c.click(c.a, '[data-act=btab][data-arg=inv]')
        for why in ['需要本周接待一位学生', '申请下一个窗口接待']:
            c.click(c.a, '[data-arg="ivApp:"]')
            c.click(c.a, '[data-act=fset][data-arg^="apc|"]')
            c.a.locator('[data-bind="form.apn"]').fill('1')
            c.a.locator('[data-bind="form.apw"]').fill(why)
            c.steps.append({'操作':'填写额度申请','数量':1,'原因':why})
            c.click(c.a, '[data-act=ivAppGo]')
        ids = c.a.evaluate('RULES.pool.apps.slice(-2).map(x=>x.id)')
        c.login()
        c.click(c.a, '[data-act=btab][data-arg=pool]')
        changes('批准申请：', lambda: c.click(c.a, f'[data-act=poolAppOk][data-arg="{ids[0]}"]'))
        changes('不批申请：', lambda: c.click(c.a, f'[data-act=poolAppNo][data-arg="{ids[1]}"]'))
        c.check(c.a.evaluate('NOTI.some(n=>n.to==="c1" && n.t.includes("你申请的 1 个额度已批准")) && NOTI.some(n=>n.to==="c1" && n.t==="你的额度申请没有批准")'), '批准与不批仍分别通知申请人')
        c.shot('额度申请处理结果')
    finally:
        c.close()
    return c.checks


def audits(browser):
    c = Case(browser, 'B4-5-每次查看摘要记审计')
    try:
        c.login()
        x = c.a.evaluate('ivb().list.find(x=>x.ik && x.ik.st==="sent" && x.ik.sum && !x.bid && ["c1","c4"].includes(x.resp))')
        sid = x['sid']
        audit = lambda: c.a.evaluate('(sid)=>AUDIT.filter(a=>a.sid===sid && a.t==="查看预咨询摘要（主动邀约）").length', sid)
        before = audit()
        for _ in range(2):
            c.click(c.a, f'[data-act=ivIkOpen][data-arg="{sid}"]')
            c.check('高危咨询题库' in c.a.inner_text('#modal'), '从批次打开的是已发送的邀约摘要')
            c.click(c.a, '[data-act=moClose]')
        c.login(x['resp'] + ('|L2' if x['resp']=='c1' else '|L3'))
        c.click(c.a, '[data-act=btab][data-arg=ai]')
        c.click(c.a, f'[data-act=ivIkOpen][data-arg="{sid}"]')
        c.check(audit() == before + 3, '同一摘要两次打开，再换老师从AI列表打开，共三条审计')
        c.check(c.a.evaluate('(sid)=>ivb().list.find(x=>x.sid===sid).ik.viewed', sid), '摘要已读标记保留')
        c.shot('换老师第三次查看摘要')
        c.click(c.a, '[data-act=moClose]')
        c.check(audit() == before + 3, '弹窗关闭和页面重绘不产生额外查看日志')
    finally:
        c.close()
    return c.checks


def duty_readonly(browser):
    c = Case(browser, 'B4-6-管理员只读值班表')
    try:
        c.select(c.a, '#roleSel', 'a1|ADM')
        c.select(c.a, '#jump', 'home')
        c.click(c.a, '[data-act=setTab][data-arg=duty]')
        text = c.a.inner_text('#modal')
        c.check('值班表 · 只读' in text and '预约咨询 · 排班表' in text, '工作台按钮打开只读值班表并说明维护位置')
        c.check(c.a.locator('#modal table tr').count() == c.a.evaluate('DUTY.length') + 1, '表格列出同一份全部值班周')
        c.check(c.a.locator('#modal input, #modal select, #modal [data-act=save]').count() == 0, '没有可修改控件')
        c.check(c.a.locator('#jump option[value=booking]').count() == 0 and c.a.locator('.side [data-arg=booking]').count() == 0, '管理员仍没有预约咨询入口')
        c.shot('管理员只读值班表')
    finally:
        c.close()
    return c.checks


def high_preview(browser):
    c = Case(browser, 'B4-7-高危预览时点')
    try:
        c.login()
        c.click(c.a, '[data-act=btab][data-arg=ai]')
        c.click(c.a, '[data-act=aisub][data-arg=bank]')
        c.click(c.a, '[data-act=ikBank][data-arg=h]')
        c.click(c.a, '[data-arg="iktPrev:t1"]')
        text = c.a.inner_text('#modal')
        c.check('学生视角预览 · 高危咨询' in text and '接受邀约后马上看到' in text, '预览标题及发生时点正确')
        c.check('这次先不用' not in text and '好的，开始' not in text, '高危预览没有普通预约的欢迎按钮')
        c.check('发完就可以选和老师见面的时间' in text, '最后一步明确发送后选时间')
        c.shot('高危题库预览')
        c.click(c.a, '[data-act=moClose]')
        c.click(c.a, '[data-act=ikBank][data-arg=n]')
        c.click(c.a, '[data-arg="iktPrev:t1"]')
        c.check('这次先不用' in c.a.inner_text('#modal'), '普通题库预览保留原欢迎按钮')
        c.student('A')
        c.s.locator('#zapT').check()
        c.click(c.s, '[data-act=zIvc]')
        c.click(c.s, '[data-act=ivAcc]')
        c.check(c.s.evaluate('S.ik.inv && S.ik.i===0') and '心理中心邀请你聊一聊' in c.s.inner_text('body'), '学生实际接受后直接进入带开场白的第一题')
        c.shot('学生实际第一题')
    finally:
        c.close()
    return c.checks


TESTS = {'B4-1': counters, 'B4-2': eligibility, 'B4-3': piles, 'B4-4': pool_notifications, 'B4-5': audits, 'B4-6': duty_readonly, 'B4-7': high_preview}
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=list(TESTS))
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = launch(p)
        try:
            total = sum(fn(browser) for name, fn in TESTS.items() if not args.only or name == args.only)
        finally:
            browser.close()
    print(f'fix_b4: {total} passed, 0 failed', flush=True)
