"""Shared browser fixtures and click evidence for the B2–B5 acceptance checks."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL = Path(os.environ.get('TRIAL_HTML', ROOT.parent / 'index.html')).resolve()


def launch(p):
    choices = [os.environ.get('CHROMIUM_PATH'), '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/opt/pw-browsers/chromium']
    exe = next((x for x in choices if x and Path(x).is_file()), None)
    return p.chromium.launch(**({'executable_path': exe} if exe else {}))


class Case:
    def __init__(self, browser, name):
        self.name, self.steps, self.errors, self.checks = name, [], [], 0
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('https://script.google.com/**', lambda route: route.fulfill(status=200, body='ok'))
        self.page.goto(TRIAL.as_uri())
        self.page.fill('#nm', name)
        self.page.click('[data-do=nameOk]')
        self.page.wait_for_selector('iframe[title="机构端"]', state='attached')
        self.a = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '机构端')
        self.s = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '学生端')
        self.s.wait_for_function('typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
        self.out = Path(os.environ.get('QA_DIR', ROOT / '自动测试/shots')) / name
        self.out.mkdir(parents=True, exist_ok=True)

    def side(self, side):
        self.page.locator(f'[data-side="{side}"]').click()

    def click(self, frame, selector, label=None, **options):
        self.side('学生端' if frame == self.s else '机构端')
        target = frame.locator(selector).first
        action = label or target.inner_text()
        target.click(**options)
        self.steps.append({'操作': action, '控件': selector, '看到': frame.locator('body').inner_text()[-5000:]})
        print('CLICK', self.name, action, flush=True)

    def select(self, frame, selector, value):
        self.side('学生端' if frame == self.s else '机构端')
        frame.locator(selector).select_option(value)
        self.steps.append({'操作': f'{selector} 选择 {value}', '看到': frame.locator('body').inner_text()[-5000:]})

    def login(self, value='c5|L3'):
        self.select(self.a, '#roleSel', value)
        self.select(self.a, '#jump', 'booking')

    def student(self, scene='A', page='home'):
        self.select(self.s, '#scen', scene)
        self.select(self.s, '#jump', page)

    def check(self, condition, label):
        assert condition, label
        self.checks += 1
        print('PASS', self.name, label, flush=True)

    def wait(self, frame, expression):
        frame.wait_for_function(expression, timeout=10000)

    def shot(self, label):
        self.page.screenshot(path=str(self.out / (label + '.png')), full_page=True, animations='disabled')

    def book(self, scene='A', cid='c1', day=6, time=2):
        self.student(scene, 'book')
        self.click(self.s, f'[data-act=day][data-arg="{day}"]')
        self.click(self.s, f'[data-act=pickSlot][data-arg="{cid}:{day}:{time}"]')
        self.click(self.s, '[data-act=bookSubmit]')
        key = {'A': 'lin', 'B': 'chen', 'C': 'huang', 'D': 'wang'}[scene]
        self.wait(self.a, f'LY_snap().{key} && LY_snap().{key}.st==="confirm"')
        return self.a.evaluate(f'LY_snap().{key}.id')

    def move(self, bid, day, time):
        self.click(self.a, f'[data-arg="bMove:{bid}"]')
        self.check(self.a.locator('[data-act=bMoveOk]').count() == 0 and self.a.locator('[data-arg^="slot|"]').count() == 0, '打开只列日期，尚无时段或确认按钮')
        self.click(self.a, f'[data-act=mvDay][data-arg="{day}"]')
        self.check(self.a.locator('[data-act=bMoveOk]').count() == 0, '仅选日期时仍无确认按钮')
        self.click(self.a, f'[data-act=fset][data-arg="slot|{day}-{time}"]')
        self.shot('日期与当天时段')
        self.click(self.a, '[data-act=bMoveOk]')

    def close(self):
        self.shot('最后界面')
        self.check(not self.errors, '无浏览器脚本异常 ' + str(self.errors))
        (self.out / '点击步骤.json').write_text(json.dumps(self.steps, ensure_ascii=False, indent=2))
        self.context.close()
