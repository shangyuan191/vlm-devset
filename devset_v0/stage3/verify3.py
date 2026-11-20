"""自我驗收：python3 -I verify3.py > results/verify3.txt"""
import hashlib, json, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; D = T.parent; R = D.parent
out = []
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()
a = (md5(T / 'results/scores.json'), md5(T / 'results/scores.md'))
subprocess.run([sys.executable, '-I', str(T / 'score.py')], check=True)
out.append(f"1 重跑 score.py 後 scores.json / scores.md 不變: {a == (md5(T / 'results/scores.json'), md5(T / 'results/scores.md'))}")
rep_before = md5(T / 'REPORT_白話版.md') if (T / 'REPORT_白話版.md').exists() else None
subprocess.run([sys.executable, '-I', str(T / 'make_report3.py')], check=True, capture_output=True)
out.append(f"2 重產報告與現有報告一致（數字全由 JSON 產生）: {rep_before == md5(T / 'REPORT_白話版.md')}")
sc = json.load(open(T / 'results/scores.json'))
for m, r in sc['models'].items():
    for c in ('img', 'style_given'):
        for s in ('S1', 'S2'):
            x = r.get(f'{c}|{s}')
            if x:
                out.append(f"3 完成題數 {m} {c} {s}: " + ', '.join(f"{o}={v['n']}/{v['n_expected']}" for o, v in x['orders'].items()))
ps = subprocess.run("ps -u $USER -o args | grep '[v]llm serve' | grep -c 'devset3'", shell=True, capture_output=True, text=True).stdout.strip()
out.append(f"4 殘留 -devset3 vLLM 數: {ps}（應為 0）")
before = dict(l.split()[::-1] for l in open(D / 'stage2/stage1_sha256_before.txt') if l.strip())
bad = [p for p, h in before.items() if hashlib.sha256((D / p).read_bytes()).hexdigest() != h]
out.append(f"5 stage1 sha256 與 before 相同: {not bad} {bad}")
cmd = f"find {D}/stage0 {D}/stage1 {R}/pilot1 {R}/pilot2 {R}/overnight_2026-11-1* {R}/smoke_* {R}/models -newer {T}/budget_base.json -type f 2>/dev/null | head"
out.append('6 受保護資料夾在階段 3 開始後被修改的檔案（應為空；overnight_2026-11-16 若有請檢查是否為別人的）: ' + repr(subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.split()))
spent = sum((json.loads(l).get('total_cost_usd') or 0) for f in ('claude_calls.jsonl', 'single_item_calls.jsonl') for l in open(D / 'stage2' / f)) - json.load(open(T / 'budget_base.json'))['spent_at_start']
out.append(f"7 階段 3 Claude 花費 ${spent:.2f}（上限 $5）")
print('\n'.join(out))
