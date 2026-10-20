"""Run the original review checks on Linux or macOS, with real failure exit codes.

pip install playwright
python 自动测试/run_checks.py adm19.py
CHROMIUM_PATH may select an installed Chrome/Chromium executable.
ADM_HTML, STU_HTML and TRIAL_HTML may override the rebuilt defaults.
"""
import os
from pathlib import Path
import runpy
import sys

from playwright.sync_api import BrowserType

ROOT = Path(__file__).resolve().parents[1]
VER = 'v1.19.2-gpt'
os.environ.setdefault('ADM_HTML', str(ROOT / '机构端' / f'灵屿2.0-机构端演示-{VER}.html'))
os.environ.setdefault('STU_HTML', str(ROOT / '试用版外壳/trial_parts/stu.html'))
os.environ.setdefault('TRIAL_HTML', str(ROOT.parent / 'index.html'))

original_launch = BrowserType.launch
def launch(self, *args, **kwargs):
    if kwargs.get('executable_path') == '/opt/pw-browsers/chromium':
        choices = [os.environ.get('CHROMIUM_PATH'), '/opt/pw-browsers/chromium',
                   '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
        executable = next((p for p in choices if p and Path(p).is_file()), None)
        kwargs.pop('executable_path')
        if executable:
            kwargs['executable_path'] = executable
    return original_launch(self, *args, **kwargs)
BrowserType.launch = launch

tests = sys.argv[1:] or ['adm19.py', 'stu19.py', 'trial_v119.py', 'trial_ik.py', 'trial.py', 'stu_reg.py', 'adm13.py']
test_dir = Path(__file__).resolve().parent
shots = Path(os.environ.get('QA_SHOTS', test_dir / 'shots')).resolve()
shots.mkdir(parents=True, exist_ok=True)
os.environ['QA_SHOTS'] = str(shots)
os.chdir(shots)
failed = []
for name in tests:
    path = test_dir / name
    print(f'RUN {name}', flush=True)
    sys.argv = [str(path)]
    try:
        result = runpy.run_path(str(path), run_name='__main__')
        failures, errors = result.get('fails', []), result.get('errs', [])
        if failures or errors:
            failed.append(name)
        passed = result.get('ok')
        if not isinstance(passed, int):
            passed = sum(line.startswith('  OK') for line in result.get('log', []))
        print(f'RESULT {name}: {passed} passed, {len(failures)} failed, {len(errors)} browser errors', flush=True)
    except Exception as exc:
        failed.append(name)
        print(f'ERROR {name}: {type(exc).__name__}: {exc}', flush=True)
print(f'SUITE: {len(tests) - len(failed)}/{len(tests)} passed', flush=True)
if failed:
    raise SystemExit(1)
