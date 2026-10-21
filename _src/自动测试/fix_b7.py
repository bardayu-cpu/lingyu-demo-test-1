"""B7 student notifications: real clicks, 1440 × 1000, local or QA_URL."""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from qa_support import Case, ROOT, TRIAL, launch


class B7Case(Case):
    def __init__(self, browser, name):
        self.name, self.steps, self.errors, self.checks = name, [], [], 0
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('https://script.google.com/**', lambda r: r.fulfill(status=200, body='ok'))
        self.page.goto(os.environ.get('QA_URL') or TRIAL.as_uri())
        self.check('同一个页面' in self.page.locator('#ov').inner_text() and '分开两个标签页不会同步' in self.page.locator('#ov').inner_text(), '原使用说明标注同页切换要求')
        self.page.fill('#nm', name)
        self.page.click('[data-do=nameOk]')
        self.page.wait_for_selector('iframe[title="机构端"]', state='attached')
        self.a = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '机构端')
        self.s = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '学生端')
        self.s.wait_for_function('typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
        self.out = Path(os.environ.get('QA_DIR', ROOT / '自动测试/shots')) / name
        self.out.mkdir(parents=True, exist_ok=True)
        self.check(self.a.evaluate('LY_VER') == 'demo-v2.0' and self.s.evaluate('LY_VER') == 'demo-v2.0' and 'demo-v2.0' in self.page.locator('#tb').inner_text(), '两端和外壳均为 demo-v2.0')
        self.steps.append({'打开': self.page.url, '视口': {'width': 1440, 'height': 1000}, '版本': 'demo-v2.0'})


def home_messages(browser):
    c = B7Case(browser, 'B7-1-首页新消息')
    try:
        c.student()
        c.check(c.s.locator('.home-messages .home-msg').count() == 2, '初始两条未读在首页显示')
        c.check(c.s.locator('.home-messages').evaluate('(el)=>el.previousElementSibling.matches(".hero")'), '新消息紧接问候语，排在我的待办前')
        c.s.locator('#zapT').check()
        for _ in range(3):
            c.click(c.s, '[data-act=zDue][data-arg=t1]', '演示产生任务提醒')
        c.check(c.s.locator('.home-msg').count() == 3, '五条未读只列最新三条')
        c.check('还有 2 条 · 查看全部' in c.s.locator('.home-msg-more').inner_text(), '剩余条数准确')
        c.check(c.s.locator('.home-msg').first.locator('svg').count() == 2 and c.s.locator('.home-msg small').first.inner_text() == '刚刚', '每条有图标、标题、相对时间')
        idx = int(c.s.locator('.home-msg').first.get_attribute('data-arg'))
        c.click(c.s, '.home-msg')
        c.check(c.s.evaluate(f'S.inbox[{idx}].read && S.task.id==="t1" && S.page==="intro"'), '点击同一条消息标已读并跳到对应任务')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.check('还有 1 条' in c.s.locator('.home-msg-more').inner_text(), '回首页后按剩余未读更新')
        c.click(c.s, '[data-act=lang]')
        text = c.s.locator('.home-messages').inner_text()
        c.check('New messages' in text and '1 more · View all' in text and 'Just now' in text, '英文标题、溢出条数和相对时间完整')
        c.shot('英文新消息')
        c.click(c.s, '.home-msg-more')
        c.check(c.s.evaluate('S.page') == 'msgs', '查看全部进入消息中心')
        c.click(c.s, '[data-act=readAll]')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.check(c.s.locator('.home-messages').count() == 0, '全部读完后整块消失且不留占位')
    finally:
        c.close()
    return c.checks


def todo_badges(browser):
    c = B7Case(browser, 'B7-2-预约邀约新标记')
    try:
        c.login('c1|L2')
        bid = c.book()
        c.side('学生端')
        c.click(c.s, '[data-act=ikNo]')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
        c.wait(c.s, 'S.bk.st==="已确认"')
        c.side('学生端')
        row = c.s.locator('.notice-todo[data-arg=booking]')
        c.check(row.locator('.todo-new').count() == 1, '老师确认后预约待办显示新')
        c.click(c.s, '.notice-todo[data-arg=booking] .grow', '点预约待办标题打开')
        c.check(c.s.evaluate('S.page==="mybook" && !S.inbox.some(x=>!x.read && x.link==="mybook")'), '打开预约行即读对应消息并进入我的预约')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.check(row.locator('.todo-new').count() == 0, '返回首页新标记消失')
        # A's standalone invitation demo remains allowed; it does not enter the core batch.
        c.s.locator('#zapT').check()
        c.click(c.s, '[data-act=zIvc]')
        c.click(c.s, '#modal [data-act=close]')
        c.check(c.s.locator('.notice-todo[data-arg=ivc] .todo-new').count() == 1, '未读邀约卡也标新')
        c.click(c.s, '[data-act=lang]')
        c.check(c.s.locator('.notice-todo[data-arg=ivc] .todo-new').inner_text() == 'New', '英文新标记')
        c.click(c.s, '.hd [data-act=inbox]')
        c.click(c.s, '.msg[data-act=msgOpen]', '在消息中心打开邀约消息')
        c.click(c.s, '#modal [data-act=close]')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.check(c.s.locator('.notice-todo[data-arg=ivc] .todo-new').count() == 0, '从消息中心阅读后邀约新标记同步消失')
    finally:
        c.close()
    return c.checks


def start_home_booking(c, english=False):
    c.login('c1|L2')
    bid = c.book()
    c.click(c.s, '[data-act=ikNo]')
    c.click(c.s, '.hd [data-act=go][data-arg=home]')
    if english:
        c.click(c.s, '[data-act=lang]')
    return bid


def confirmations(browser):
    total = 0
    for action, english in [('dismiss', False), ('view', False), ('view', True)]:
        c = B7Case(browser, 'B7-3-后台确认-' + action + ('-英文' if english else '-中文'))
        try:
            bid = start_home_booking(c, english)
            c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
            c.wait(c.s, 'S.bk.st==="已确认" && S.noticeIds && S.noticeIds.length===1')
            c.check(c.s.locator('.notice-card').count() == 0, '机构端显示时尚未渲染学生提醒卡')
            c.page.wait_for_timeout(5500)
            c.steps.append({'操作': '保持机构端等待 5.5 秒，再切回学生端'})
            c.check(c.s.locator('.notice-card').count() == 0 and c.s.evaluate('S.noticeIds.length') == 1, '超过短提示时长后后台仍保留重要提醒')
            c.side('学生端')
            c.s.wait_for_selector('.notice-card')
            card = c.s.locator('.notice-card')
            c.check(card.count() == 1 and c.s.locator('#modal .mo').count() == 0, '切回后恰好一张确认提醒，没有重复整页弹窗')
            c.check(c.s.locator('#toast .toast').count() == 0, '老师确认不再使用 2.4 秒短提示')
            c.check(c.s.locator('.home-msg').count() == 3 and c.s.locator('.notice-todo[data-arg=booking] .todo-new').count() == 1, '首页新消息和预约新标记同时出现')
            c.page.wait_for_timeout(3000)
            c.check(card.count() == 1, '学生端等待三秒后提醒仍持续显示')
            if english:
                text = card.inner_text()
                c.check('confirmed your appointment' in text and 'Got it' in text and 'View' in text and not any('\u4e00' <= ch <= '\u9fff' for ch in text), '英文提醒标题、详情和两个按钮均无中文')
            c.shot('延迟切回看到提醒卡与首页新消息')
            if action == 'dismiss':
                c.click(c.s, '[data-act=noticeDismiss]')
                c.check(card.count() == 0 and c.s.evaluate('S.inbox.some(x=>!x.read && x.link==="mybook")'), '知道了仅关闭提醒卡，消息中心仍保留未读')
                c.s.locator('#zapT').check()
                c.click(c.s, '[data-act=zIvQ]')
                c.check(c.s.locator('#toast .toast').count() == 1, '学生自己的操作仍使用短提示')
                c.page.wait_for_timeout(2700)
                c.check(c.s.locator('#toast .toast').count() == 0, '学生操作短提示照旧自动消失')
            else:
                c.click(c.s, '[data-act=noticeView]')
                c.check(c.s.evaluate('S.page==="mybook" && S.inbox.find(x=>x.noticeId).read'), '提醒查看进入我的预约并标记对应消息已读')
                c.check(card.count() == 0, '查看后提醒卡关闭')
                c.click(c.s, '.hd [data-act=go][data-arg=home]')
                c.check(c.s.locator('.notice-todo[data-arg=booking] .todo-new').count() == 0, '提醒查看后首页预约新标记消失')
        finally:
            c.close()
        total += c.checks
    return total


def confirmation_during_intake(browser):
    c = B7Case(browser, 'B7-3-预咨询欢迎窗未关闭时收到确认')
    try:
        c.login('c1|L2')
        bid = c.book()
        c.check(c.s.evaluate('S.modal') == 'ikWelcome', '提交后保留原有预咨询欢迎窗，不先关闭')
        c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
        c.wait(c.s, 'S.bk.st==="已确认" && S.noticeIds.length===1')
        c.page.wait_for_timeout(5500)
        c.side('学生端')
        c.s.wait_for_selector('.notice-card')
        c.check(c.s.locator('.notice-card').count() == 1 and c.s.evaluate('S.modal') == 'ikWelcome', '切回后确认卡立即可见，原预咨询欢迎窗保留')
        c.check(c.s.locator('[data-act=noticeDismiss]').evaluate('(e)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}'), '确认卡按钮实际位于欢迎窗遮罩之上，可以点击')
        c.shot('预咨询欢迎窗上方的老师确认提醒')
        c.click(c.s, '[data-act=noticeDismiss]')
        c.check(c.s.locator('.notice-card').count() == 0 and c.s.evaluate('S.modal') == 'ikWelcome', '知道了只关闭提醒，仍可继续原预咨询')
        c.click(c.s, '[data-act=ikNo]')
        c.check(c.s.evaluate('S.bk.st') == '已确认', '跳过预咨询后预约确认状态保持')
    finally:
        c.close()
    return c.checks


def existing_modals(browser):
    total = 0
    for event in ['move', 'decline', 'rearr']:
        c = B7Case(browser, 'B7-3-已有完整弹窗-' + event)
        try:
            bid = start_home_booking(c, english=True)
            if event == 'rearr':
                c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
                c.wait(c.s, 'S.bk.st==="已确认"')
                c.side('学生端')
                c.s.wait_for_selector('[data-act=noticeView]')
                c.click(c.s, '[data-act=noticeView]')
                c.click(c.s, '.hd [data-act=go][data-arg=home]')
                c.click(c.a, '[data-act=btab][data-arg=sched]')
                c.click(c.a, '[data-arg="schedReg:"]')
                for arg in ['rgc|c1', 'rgt|病假停诊', 'rgd|7', 'rga|all']:
                    c.click(c.a, f'[data-act=fset][data-arg="{arg}"]')
                c.click(c.a, '[data-act=schedRegGo]')
                c.wait(c.s, 'S.bk===null')
                c.side('学生端')
                c.check('Your appointment time has changed' in c.s.locator('#modal').inner_text() and c.s.locator('.notice-card').count() == 0, '中心调整保留完整英文弹窗，不叠提醒卡')
                c.click(c.s, '#modal [data-act=go]')
                c.click(c.s, '.hd [data-act=go][data-arg=home]')
                c.click(c.a, '[data-act=btab][data-arg=man]')
                c.click(c.a, '[data-act=bsub][data-arg=adjust]')
            if event in ['move', 'rearr']:
                c.move(bid, 5, 0)
                c.wait(c.s, 'S.bk && S.bk.st==="已改约"')
            else:
                c.click(c.a, f'[data-arg="bNo:{bid}"]')
                c.click(c.a, '[data-act=fset][data-arg="why|时段冲突"]')
                c.a.locator('[data-bind="form.note"]').fill('Please choose another time next week.')
                c.click(c.a, '[data-act=bNoOk]')
                c.wait(c.s, 'S.bk===null')
            c.page.wait_for_timeout(5500)
            c.side('学生端')
            c.check(c.s.locator('#modal .mo').count() == 1 and c.s.locator('.notice-card').count() == 0, '延迟切回保留既有完整弹窗，不给同一事件重复提醒卡')
            c.check(c.s.locator('#toast .toast').count() == 0, '重要事件没有短提示')
            c.shot('学生收到完整通知-无重复提醒')
            if event == 'move':
                c.check('Accept new time' in c.s.locator('#modal').inner_text(), '改时间说明学生需要接受')
                c.click(c.s, '#modal [data-act=movedOk]')
                c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).st==="ok"')
                c.check(c.s.evaluate('S.bk.st') == '已确认', '学生接受新时间后两端确认')
            elif event == 'rearr':
                c.check('Your counsellor arranged a new time' in c.s.locator('#modal').inner_text(), '重新安排明确告诉学生新时间')
                c.click(c.s, '#modal [data-act=movedOk]')
                c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).st==="ok"')
                c.check(c.a.evaluate("SCHM.c1['10/21'].every(x=>x==='off')"), '接受重新安排后病假日仍关闭')
            else:
                c.check('Please choose another time next week.' in c.s.locator('#modal').inner_text(), '婉拒完整弹窗保留老师留言')
                c.click(c.s, '#modal [data-act=go]')
                c.check(c.s.evaluate('S.page') == 'book', '婉拒后可以继续选时间')
            c.check(c.s.locator('.notice-card').count() == 0, '处理整页弹窗后不补一张同事件提醒卡')
            c.shot('完整弹窗处理后的学生界面')
        finally:
            c.close()
        total += c.checks
    return total


def request_results(browser):
    total = 0
    for kind in ['cancel', 'resch']:
        for approved in [False, True]:
            c = B7Case(browser, f'B7-3-{kind}-' + ('同意' if approved else '不同意'))
            try:
                bid = start_home_booking(c, english=True)
                c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
                c.wait(c.s, 'S.bk.st==="已确认"')
                c.side('学生端')
                c.s.wait_for_selector('[data-act=noticeView]')
                c.click(c.s, '[data-act=noticeView]')
                if kind == 'cancel':
                    c.click(c.s, '[data-act=modal][data-arg=cancel]')
                    c.click(c.s, '[data-act=cancelOk]')
                else:
                    c.click(c.s, '[data-act=resch]')
                    c.click(c.s, '[data-act=reschOk]')
                    pick = c.s.evaluate("(()=>{for(let d=0;d<DAYS.length;d++)for(let t=0;t<DATA.times.length;t++)if(slotState(ci('c1'),d,t)==='open')return {d,t};throw Error('No opening')})()")
                    c.click(c.s, f'[data-act=day][data-arg="{pick["d"]}"]')
                    c.click(c.s, f'[data-act=pickSlot][data-arg="c1:{pick["d"]}:{pick["t"]}"]')
                    c.click(c.s, '[data-act=bookSubmit]')
                    c.click(c.s, '#modal [data-act=go][data-arg=mybook]')
                c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).st==="change"')
                c.click(c.s, '.hd [data-act=go][data-arg=home]')
                c.click(c.a, '[data-act=bsub][data-arg=change]')
                if approved:
                    c.click(c.a, f'[data-act=bAgree][data-arg="{bid}"]')
                    c.wait(c.s, 'S.modal==="appr"')
                else:
                    c.click(c.a, f'[data-arg="bDeny:{bid}"]')
                    c.a.locator('[data-bind="form.note"]').fill('Please keep the original appointment.')
                    c.click(c.a, '[data-act=bDenyOk]')
                    c.wait(c.s, 'S.bk && !S.bk.pend && S.noticeIds.length===1')
                c.page.wait_for_timeout(5500)
                c.side('学生端')
                c.check(c.s.locator('#toast .toast').count() == 0, '申请结果不使用短提示')
                if approved:
                    c.check(c.s.locator('#modal .mo').count() == 1 and c.s.locator('.notice-card').count() == 0, '同意结果保留完整弹窗，没有重复卡片')
                    c.check('approved' in c.s.locator('#modal').inner_text(), '同意弹窗使用英文')
                    c.click(c.s, '#modal [data-act=close]')
                    c.check(c.s.locator('.notice-todo[data-arg=booking] .todo-new').count() == 1, '未读的同意结果在待办标新，取消后仍能找到结果')
                    c.click(c.s, '.notice-todo[data-arg=booking] .grow')
                else:
                    c.check(c.s.locator('.notice-card').count() == 1 and 'not approved' in c.s.locator('.notice-card').inner_text(), '不同意结果延迟切回后显示英文持久提醒')
                    c.click(c.s, '[data-act=noticeView]')
                c.check(c.s.evaluate('S.page==="mybook" && !S.inbox.some(x=>!x.read && x.link==="mybook")'), '结果入口进入我的预约并已读')
                c.shot('结果已到学生端')
            finally:
                c.close()
            total += c.checks
    return total


def invitation_entry(browser):
    c = B7Case(browser, 'B7-3-邀约卡与选时间入口')
    try:
        c.login()
        c.student('B')
        c.click(c.s, '[data-act=lang]')
        c.click(c.a, '[data-arg="ivSend:4"]')
        c.click(c.a, '[data-act=ivSendGo]')
        c.wait(c.s, 'S.ivc && S.ivc.st==="wait"')
        c.side('学生端')
        c.check('UCC invites you to talk' in c.s.locator('#modal').inner_text() and c.s.locator('.notice-card').count() == 0, '收到邀约卡保留完整英文卡片，不重复出提醒')
        sid = c.a.evaluate('LY_CORE().chen.id')
        c.click(c.s, '#modal [data-act=close]')
        c.s.locator('#zapT').check()
        c.click(c.s, '[data-act=zIvQ]')
        c.click(c.s, '[data-act=ivcOpen]')
        c.click(c.s, '[data-act=ivAcc]')
        c.intake('I would like to discuss study pressure and a better daily routine.')
        c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).st==="queue"')
        c.click(c.s, '#modal [data-act=close]')
        for attempt in range(2):
            c.click(c.a, f'[data-act=ivEntryGo][data-arg="{sid}"]')
            c.click(c.a, '[data-act=ivEntryOk]')
            c.wait(c.s, 'S.ivc.st==="entry" && S.noticeIds.length===1')
            c.check(c.s.locator('.notice-card').count() == 0, '入口在机构端操作时先等待切回')
            c.page.wait_for_timeout(5500)
            c.side('学生端')
            c.s.wait_for_selector('.notice-card')
            text = c.s.locator('.notice-card').inner_text()
            c.check('You can now pick a time to meet' in text and 'Got it' in text and not any('\u4e00' <= ch <= '\u9fff' for ch in text), '新入口持久提醒为完整英文')
            c.check(c.s.locator('.notice-todo[data-arg=ivc] .todo-new').count() == 1, '入口更新对应的邀约待办标新')
            c.shot('老师给入口后的英文提醒')
            c.click(c.s, '[data-act=noticeView]')
            c.check(c.s.evaluate('S.page==="book" && !S.inbox.some(x=>!x.read && x.link==="book")'), '入口查看跳到选时间并读对应消息')
            if attempt == 0:
                c.click(c.s, '[data-act=ivFit]')
                for _ in range(3):
                    target = c.s.locator('[data-act=ivFitT]:not(.on)').first
                    c.click(c.s, f'[data-act=ivFitT][data-arg="{target.get_attribute("data-arg")}"]')
                c.click(c.s, '[data-act=ivFitT]:not(.on)')
                c.check(c.s.locator('#toast').inner_text() == 'Pick up to 3', '学生最多选三项提示仍为英文短提示')
                c.click(c.s, '[data-act=ivFitOk]')
                c.wait(c.a, f'ivb().list.find(x=>x.sid==={sid!r}).st==="nofit"')
        c.click(c.s, '.hd [data-act=go][data-arg=home]')
        c.check(c.s.locator('.notice-todo[data-arg=ivc] .todo-new').count() == 0, '读过入口消息后邀约新标记消失')
    finally:
        c.close()
    return c.checks


def talk_stack(browser):
    c = B7Case(browser, 'B7-3-谈心多条提醒堆叠')
    try:
        c.login()
        c.student('A')
        sid = c.a.evaluate('LY_CORE().lin.id')
        owner = c.a.evaluate('sid=>{const x=ITEMS.find(x=>x.sid===sid && x.st==="open");return x && x.to}', sid)
        if not owner:
            c.select(c.a, '#jump', 'talk')
            c.click(c.a, '[data-act=tktab][data-arg=all]')
            c.click(c.a, '[data-arg="tkMk:"]')
            c.a.locator('[data-bind="form.q"]').fill('林晓')
            c.a.locator('[data-bind="form.q"]').press('Tab')
            c.click(c.a, f'[data-act=fset][data-arg="sid|{sid}"]')
            c.a.locator('[data-bind="form.note"]').fill('请和学生聊聊近期的学习安排。')
            c.click(c.a, '[data-act=fset][data-arg="due|7 天内"]')
            c.click(c.a, '[data-act=tkMkGo]')
            owner = c.a.evaluate('sid=>ITEMS.find(x=>x.sid===sid && x.st==="open").to', sid)
        role = c.a.evaluate('uid=>STAFF[uid].role', owner)
        c.select(c.a, '#roleSel', owner + '|' + role)
        c.select(c.a, '#jump', 'talk')
        for attempt in range(2):
            c.click(c.a, '[data-act=tktab][data-arg=todo]')
            c.click(c.a, f'.tkrow[data-act=tkX][data-arg="{sid}"]', '在待谈心名单选择林晓')
            c.click(c.a, f'[data-arg="tkInv:{sid}"]')
            # Pick tomorrow/a later working day using the actual date buttons.
            day = c.a.locator('[data-act=fset][data-arg^="day|"]').nth(2).get_attribute('data-arg')
            c.click(c.a, f'[data-act=fset][data-arg="{day}"]')
            c.click(c.a, '[data-act=tkInvGo]')
            c.wait(c.s, f'(S.noticeIds||[]).length==={attempt * 2 + 1}')
            iid = c.a.evaluate('sid=>INV.filter(v=>v.sid===sid).slice(-1)[0].id', sid)
            c.click(c.a, '[data-act=tktab][data-arg=inv]')
            c.click(c.a, f'[data-act=tkInvCancel][data-arg="{iid}"]')
            c.wait(c.s, f'S.noticeIds.length==={attempt * 2 + 2}')
        c.page.wait_for_timeout(5500)
        c.side('学生端')
        c.s.wait_for_selector('.notice-card')
        c.check(c.s.locator('.notice-card').count() == 3 and '还有 1 条' in c.s.locator('.notice-more').inner_text(), '四条谈心更新只叠三张，多余一条有提示')
        ids = c.s.locator('.notice-card').evaluate_all('(els)=>els.map(e=>e.dataset.notice)')
        c.click(c.s, '[data-act=lang]')
        c.check(c.s.locator('.notice-more').inner_text() == '1 more update', '英文溢出提示')
        c.click(c.s, f'[data-act=noticeDismiss][data-arg="{ids[0]}"]')
        c.check(c.s.locator('.notice-card').count() == 3 and c.s.locator('.notice-more').count() == 0, '知道了后补上等候的第四条，没有丢失')
        text = c.s.locator('#notices').inner_text()
        # Teachers' supplied names keep their original spelling; surrounding UI must be English.
        for who in c.s.evaluate('(S.invs||[]).map(v=>v.who)'):
            text = text.replace(who, '')
        c.check('View' in text and 'Got it' in text and not any('\u4e00' <= ch <= '\u9fff' for ch in text), '堆叠谈心提醒切英文后没有中文')
        c.shot('三张谈心提醒堆叠')
        expected = c.s.locator('[data-act=noticeView]').first.get_attribute('data-arg')
        link = c.s.evaluate('id=>S.inbox.find(x=>x.noticeId===id).link', expected)
        c.click(c.s, '[data-act=noticeView]')
        c.check(c.s.evaluate('S.modal') == 'inv' and c.s.locator(f'.notice-card[data-notice="{expected}"]').count() == 0, '谈心查看打开对应邀约，对应提醒卡已关闭')
        c.check(c.s.evaluate('S.inv') == link[4:], '多次插入新消息后查看仍定位卡片对应的谈心邀约')
        c.check(c.s.evaluate('S.inbox.filter(x=>x.noticeId && x.read).length') >= 1, '谈心查看标记对应消息已读')
        c.click(c.s, '#modal [data-act=close]')
        while c.s.locator('[data-act=noticeDismiss]').count():
            c.click(c.s, '[data-act=noticeDismiss]')
        c.click(c.a, '[data-act=tktab][data-arg=todo]')
        c.click(c.a, f'.tkrow[data-act=tkX][data-arg="{sid}"]')
        c.click(c.a, f'[data-arg="tkInv:{sid}"]')
        c.click(c.a, f'[data-act=fset][data-arg="{day}"]')
        c.click(c.a, '[data-act=tkInvGo]')
        c.wait(c.s, 'S.noticeIds.length===1')
        c.click(c.s, '[data-act=noticeView]')
        iid = c.s.evaluate('S.inv')
        c.click(c.a, '[data-act=tktab][data-arg=inv]')
        c.click(c.a, f'[data-arg="tkInvEdit:{iid}"]')
        later = c.a.locator('[data-act=fset][data-arg^="day|"]').nth(3).get_attribute('data-arg')
        c.click(c.a, f'[data-act=fset][data-arg="{later}"]')
        c.click(c.a, '[data-act=tkInvEditGo]')
        c.wait(c.s, 'S.inbox[0].t[1].includes("confirm again")')
        c.side('学生端')
        c.check(c.s.evaluate('S.modal==="inv" && S.noticeIds.length===0'), '学生已打开的谈心弹窗收到改时更新，也不排入重复提醒卡')
        c.click(c.s, '#modal [data-act=ovClose]', '关闭谈心弹窗', position={'x': 2, 'y': 2})
        c.check(c.s.locator('.notice-card').count() == 0, '关掉更新后的谈心弹窗不会补出同事件卡片')
    finally:
        c.close()
    return c.checks


TESTS = {'home': home_messages, 'badges': todo_badges, 'confirm': confirmations, 'intake': confirmation_during_intake, 'modals': existing_modals,
         'requests': request_results, 'entry': invitation_entry, 'stack': talk_stack}
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
    print(f'fix_b7: {total} passed, 0 failed', flush=True)
