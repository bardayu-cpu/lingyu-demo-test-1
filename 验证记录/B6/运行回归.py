"""Run unchanged business checks with the existing local Chrome cleanup adapter."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PY = sys.executable
ADAPTER = OUT / '回归驱动.py'
results = []
for name in ['fix_b1.py', 'fix_b2.py', 'fix_b3.py', 'fix_b4.py', 'fix_b5.py', 'run_checks.py']:
    env = dict(os.environ, QA_DIR=str(OUT / '回归截图' / name[:-3]), QA_SHOTS=str(OUT / '回归截图' / name[:-3]))
    log = OUT / (name[:-3] + '.log')
    print('RUN', name, flush=True)
    with log.open('w') as f:
        proc = subprocess.Popen([PY, str(ADAPTER), str(ROOT / '_src/自动测试' / name)], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=720)
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
