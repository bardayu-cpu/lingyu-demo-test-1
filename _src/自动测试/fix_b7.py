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
        self.page.fill('#nm', name)
        self.page.click('[data-do=nameOk]')
        self.page.wait_for_selector('iframe[title="机构端"]', state='attached')
        self.a = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '机构端')
        self.s = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '学生端')
        self.s.wait_for_function('typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
        self.out = Path(os.environ.get('QA_DIR', ROOT / '自动测试/shots')) / name
        self.out.mkdir(parents=True, exist_ok=True)


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


TESTS = {'home': home_messages}
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
