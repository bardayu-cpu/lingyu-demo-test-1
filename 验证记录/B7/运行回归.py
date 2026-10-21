"""Run unchanged business checks with the existing local Chrome cleanup adapter."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
OUT = Path(os.environ.get('B7_LOG_DIR', BASE))
OUT.mkdir(parents=True, exist_ok=True)
PY = sys.executable
ADAPTER = BASE / '回归驱动.py'
results = []
for name in ['fix_b1.py', 'fix_b2.py', 'fix_b3.py', 'fix_b4.py', 'fix_b5.py', 'fix_b6.py', 'fix_b7.py', 'run_checks.py']:
    env = dict(os.environ, QA_DIR=str(ROOT / '_src/自动测试/shots/B7回归' / name[:-3]), QA_SHOTS=str(ROOT / '_src/自动测试/shots/B7回归' / name[:-3]))
    log = OUT / (name[:-3] + '.log')
    print('RUN', name, flush=True)
    with log.open('w') as f:
        proc = subprocess.Popen([PY, str(ADAPTER), str(ROOT / '_src/自动测试' / name)], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            code = 124
    lines = log.read_text().splitlines()
    summary = [s for s in lines if 'passed,' in s or s.startswith(('RESULT ', 'SUITE:', 'ERROR '))]
    results.append({'script': name, 'exit': code, 'summary': summary})
    (OUT / '回归结果.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(name, code, summary, flush=True)
print('ALL', all(r['exit'] == 0 for r in results), flush=True)
raise SystemExit(0 if all(r['exit'] == 0 for r in results) else 1)
