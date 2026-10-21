"""Batch 2 UI and cross-frame acceptance checks."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def moves(browser):
    total = 0
    for adjusted in [False, True]:
        c = Case(browser, 'B2-1-中心调整' if adjusted else 'B2-1-普通申请')
        try:
            c.login('c1|L2')
            bid = c.book()
            if adjusted:
                c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
                c.wait(c.s, 'S.bk.st==="已确认"')
                c.click(c.a, '[data-act=btab][data-arg=sched]')
                c.click(c.a, '[data-arg="schedReg:"]')
                for arg in ['rgc|c1', 'rgt|病假停诊', 'rgd|7', 'rga|all']:
                    c.click(c.a, f'[data-act=fset][data-arg="{arg}"]')
                c.click(c.a, '[data-act=schedRegGo]')
                c.wait(c.s, 'S.bk===null')
                c.click(c.a, '[data-act=btab][data-arg=man]')
                c.click(c.a, '[data-act=bsub][data-arg=adjust]')
            c.move(bid, 5, 0)
            c.wait(c.s, 'S.bk && S.bk.st==="已改约"')
            c.check(c.a.evaluate('(id)=>BOOK.find(b=>b.id===id).st', bid) == 'move', '老师提出时间后未提前确认')
            row = c.a.locator('.bkpin tr').filter(has=c.a.locator(f'[data-act=bOpen][data-arg="{bid}"]'))
            c.check(row.locator('button').count() == 1 and '看学生信息' in row.inner_text(), '等待学生确认的行只留学生信息')
            c.side('学生端')
            c.shot('学生收到新时间')
            if adjusted:
                c.check('点「接受新时间」就约好了' in c.s.inner_text('#modal'), '中心调整通知说明接受动作')
                c.click(c.s, '#modal [data-act=movedOk]')
            else:
                c.click(c.s, '#modal .ov', '关闭老师改约通知', position={'x': 2, 'y': 2})
                c.click(c.s, '[data-act=go][data-arg=mybook]', '打开我的预约')
                c.check('不用操作' not in c.s.inner_text('#app'), '预约卡不再提示不用操作')
                c.click(c.s, '[data-act=movedOk]')
            c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).st==="ok"')
            c.check(c.s.evaluate('S.bk.st') == '已确认', '学生接受后双端已确认')
            c.check(c.a.evaluate('(id)=>NOTI.some(n=>n.ref===id && n.to==="c1" && n.t.includes("接受了新时间"))', bid), '老师收到接受通知')
            if adjusted:
                c.check(c.a.evaluate("SCHM.c1['10/21'].every(x=>x==='off')"), '接受后原病假日四格仍关闭')
            c.select(c.s, '#jump', 'mybook')
            c.click(c.s, '[data-act=resch]')
            c.click(c.s, '[data-act=reschOk]')
            c.check(c.s.locator('[data-act=pickSlot]').count() == 0, '学生改期也先列日期')
            c.click(c.s, '[data-act=day]')
            c.check(c.s.locator('[data-act=pickSlot]').count() > 0, '选择日期后才显示当天时段')
            c.shot('学生改期按日期选时')
        finally:
            c.close()
            total += c.checks
    return total


def declines(browser):
    c = Case(browser, 'B2-2-邀约婉拒后重选')
    try:
        c.login('c1|L2')
        c.student('A', 'home')
        c.s.locator('#zapT').check()
        c.click(c.s, '[data-act=zIvc]')
        c.click(c.s, '[data-act=ivAcc]')
        c.intake()
        c.click(c.s, '[data-act=day][data-arg="6"]')
        c.click(c.s, '[data-act=pickSlot][data-arg="c1:6:2"]')
        c.click(c.s, '[data-act=bookSubmit]')
        c.wait(c.a, 'LY_snap().lin && LY_snap().lin.st==="confirm"')
        bid = c.a.evaluate('LY_snap().lin.id')
        due = c.s.evaluate('S.ivc.edue')
        c.click(c.a, f'[data-arg="bNo:{bid}"]')
        c.click(c.a, '[data-act=fset][data-arg="why|时段冲突"]')
        note = '这周我要出差，下周再约'
        c.a.locator('[data-bind="form.note"]').fill(note)
        c.click(c.a, '[data-act=bNoOk]')
        c.wait(c.s, 'S.bk===null && S.ivc.st==="entry"')
        c.check(note in c.s.inner_text('#modal') and '原因：时段冲突' in c.s.inner_text('#modal'), '弹窗显示实际原因和老师的话')
        c.check(note in c.s.evaluate('S.inbox[0].d[0]'), '站内信也保留老师的话')
        c.check(c.s.evaluate('S.ivc.edue') == due, '婉拒保留原入口期限')
        c.side('学生端')
        c.shot('婉拒原因和留言')
        c.click(c.s, '#modal [data-act=go]')
        c.check('可以选和老师见面的时间了' in c.s.inner_text('#app'), '通知按钮返回有效的选时入口')
        c.click(c.s, '[data-act=go][data-arg=home]')
        c.check('选和老师见面的时间' in c.s.inner_text('#app'), '首页重新出现选时间入口')
        c.shot('婉拒后首页继续选时')
    finally:
        c.close()
    return c.checks


def drafts(browser):
    c = Case(browser, 'B2-3-草稿隐私')
    try:
        c.login('c1|L2')
        bid = c.book()
        c.click(c.s, '[data-act=ikYes]')
        c.click(c.s, '[data-act=ikTog]')
        c.click(c.s, '[data-act=ikNextQ]')
        c.s.locator('#ikTxt').fill('这段正在填写的内容暂时不想发给老师。')
        c.click(c.s, '[data-act=ikX]')
        c.click(c.s, '[data-act=ikSave]')
        c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).intake.st==="draft"')
        c.check(c.s.evaluate('S.bk.intake.sum.length') > 0, '学生本地仍保存有内容的草稿')
        c.check(c.a.evaluate('(id)=>!BOOK.find(b=>b.id===id).intake.sum', bid), '老师端预约不含草稿摘要')
        c.click(c.a, '[data-act=btab][data-arg=ai]')
        row = c.a.locator('tr').filter(has_text='林晓')
        c.check('已保存，未发送' in row.inner_text() and row.locator('button').count() == 0, '草稿行显示状态且无摘要按钮')
        c.shot('老师端草稿不可打开')
        c.a.evaluate('LY_in({t:"intake",core:"lin",intake:{st:"draft",ver:1,sum:[{k:"secret",v:"PRIVATE_DRAFT"}],ans:{secret:"PRIVATE_DRAFT"}}})')
        c.check(c.a.evaluate('(id)=>{const it=BOOK.find(b=>b.id===id).intake;return !it.sum&&!it.ans}', bid), '接收端也丢弃直接传入的草稿内容')
        c.click(c.s, '[data-act=ikGo]')
        c.intake()
        c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).intake.st==="sent"')
        row = c.a.locator('tr').filter(has_text='林晓')
        c.click(c.a, f'[data-arg="intake:{bid}"]')
        c.check('最近学习压力有些大' in c.a.inner_text('#modal'), '学生确认发送后老师能打开完整摘要')
        c.shot('确认发送后的摘要')
    finally:
        c.close()
    return c.checks


TESTS = {'B2-1': moves, 'B2-2': declines, 'B2-3': drafts}
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
    print(f'fix_b2: {total} passed, 0 failed', flush=True)
