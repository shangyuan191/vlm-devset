"""自我驗收：python3 -I verify4.py > results/verify4.txt"""
import hashlib, json, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent; D = U.parent; R = D.parent
out = []
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()
a = (md5(U / 'results/scores4.json'), md5(U / 'results/scores4.md'))
subprocess.run([sys.executable, '-I', str(U / 'score4.py')], check=True)
out.append(f"1 重跑 score4.py 後 scores4.json / scores4.md 不變: {a == (md5(U / 'results/scores4.json'), md5(U / 'results/scores4.md'))}")
b = md5(U / 'questions4.json')
subprocess.run([sys.executable, '-I', str(U / 'build_questions4.py')], check=True, capture_output=True)
out.append(f"2 重跑 build_questions4.py 後 questions4.json 不變: {b == md5(U / 'questions4.json')}")
rb = md5(U / 'REPORT_白話版.md') if (U / 'REPORT_白話版.md').exists() else None
subprocess.run([sys.executable, '-I', str(U / 'make_report4.py')], check=True, capture_output=True)
out.append(f"3 重產報告與現有報告一致（數字全由 JSON 產生）: {rb == md5(U / 'REPORT_白話版.md')}")
sc = json.load(open(U / 'results/scores4.json'))
for m, r in sc['models'].items():
    for k, v in r.items():
        if k.startswith('tmpl_zh|') and k.count('|') == 1:
            out.append(f"4 完成題數 {m} {k}: " + ', '.join(f"{o}={x['n']}/{x['n_expected']}" for o, x in v['orders'].items()))
        if k.startswith('wording|'):
            out.append(f"4 完成題數 {m} {k}: " + ', '.join(f"{w}={x['n']}" for w, x in v['by_wording'].items()))
ps = subprocess.run("ps -u $USER -o args | grep '[v]llm serve' | grep -c 'devset4'", shell=True, capture_output=True, text=True).stdout.strip()
out.append(f"5 殘留 -devset4 vLLM 數: {ps}（應為 0）")
before = dict(l.split()[::-1] for l in open(D / 'stage2/stage1_sha256_before.txt') if l.strip())
bad = [p for p, h in before.items() if hashlib.sha256((D / p).read_bytes()).hexdigest() != h]
out.append(f"6 stage1 sha256 與 before 相同: {not bad} {bad}")
cmd = f"find {D}/stage0 {D}/stage1 {D}/stage2 {D}/stage3 {R}/pilot1 {R}/pilot2 {R}/overnight_2026-11-1* {R}/smoke_* {R}/models -newer {U}/RUNBOOK.md -type f 2>/dev/null | grep -v __pycache__ | head"
out.append('7 受保護資料夾 / stage2 / stage3 在階段 4 開始後被修改的檔案（應為空）: ' + repr(subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.split()))
qt = json.load(open(U / 'query_texts.json'))
out.append(f"8 query_texts.json：{len(qt)} 題；使用 tmpl_en 後備 {sum(1 for v in qt.values() if v['syn_source'] != 'llm')} 題")
print('\n'.join(out))
