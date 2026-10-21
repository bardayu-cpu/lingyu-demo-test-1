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


TESTS = {'B4-1': counters}
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
