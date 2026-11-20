"""自我驗收：(1) 重跑分析與報告，輸出不變；(2) 報告的 30 格表和 results JSON 一致；(3) 沒有殘留的自己的 vLLM；(4) 沒有寫入受保護的資料夾。
用法： python3 -I devset_v0/verify.py
"""
import hashlib, json, os, re, subprocess, time
from pathlib import Path
D = Path(__file__).resolve().parent; R = D.parent
START = time.mktime(time.strptime('2026-11-16 15:29', '%Y-%m-%d %H:%M')) - time.timezone  # UTC
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()  # noqa: E731
files = [D / 'results/stage1_analysis.json', D / 'results/stage1_analysis.md', D / 'stage1/review_sample.json', D / 'REPORT_白話版.md']
ok = True
before = [md5(f) for f in files]
subprocess.run(['python3', '-I', str(D / 'stage1/analyze.py')], check=True, capture_output=True)
subprocess.run(['python3', '-I', str(D / 'make_report.py')], check=True, capture_output=True)
same = before == [md5(f) for f in files]; ok &= same
print('1. 重跑 analyze.py + make_report.py 後 4 個輸出檔 md5 相同：', same)
J = json.load(open(files[0])); rep = files[3].read_text(encoding='utf-8')
rows = [l for l in rep.splitlines() if re.match(r'\| [a-z/\-]+ × ', l) and l.count('|') == 10]
bad = 0
for l, (c, v) in zip(rows, J['cells'].items()):
    f = [x.strip() for x in l.strip('|').split('|')]
    exp = [f"{v['kw_hits']:,}", f"{v['after_title_dedup']:,}", f"{100*v['a_kw_accuracy']:.0f}%", f"{100*v['b_unanimous_style']:.0f}%",
           f"{100*v['c_qualified']:.0f}%（{v['c_qualified_k']}/30）", f"{100*v['c2_qualified_and_item_ok']:.0f}%（{v['c2_k']}/30）"]
    bad += f[1:7] != exp
pool = [json.loads(l) for l in open(D / 'stage0/pool.jsonl')]
CC = json.load(open(D / 'stage0/cell_counts.json'))
chk = {'30 格表列數 = 30': len(rows) == 30, '表格數字和 JSON 不一致的列 = 0': bad == 0,
       'pool.jsonl 筆數 = cell_counts n_pool': len(pool) == CC['n_pool'],
       'pool 的圖都存在': all((R / p['image_path']).exists() for p in pool),
       'pool parent_asin 不重複': len({p['parent_asin'] for p in pool}) == len(pool),
       '三位標註者各 900 筆': all(sum(1 for _ in open(D / 'stage1' / f)) == 900 for f in ('ann_claude.jsonl', 'ann_qwen38-27b.jsonl', 'ann_gemma4-12b.jsonl')),
       'Claude 實際模型只有 claude-opus-5-5': J['claude_cost']['models_seen'] == ['claude-opus-5-5'],
       'review_sample 60 件': len(json.load(open(files[2]))) == 60}
for k, v in chk.items():
    ok &= v; print('2.', k, '：', v)
ps = subprocess.run('ps -u $USER -o pid,cmd | grep -E "devset_2026-11-17" | grep -v grep; ss -ltn | grep -E ":808[1-9] "', shell=True, capture_output=True, text=True).stdout.strip()
ok &= not ps; print('3. 沒有殘留的 devset_2026-11-17 vLLM、8081–8089 沒有被佔用：', not ps, ps[:200])
touched = []
for root, dirs, fs in os.walk(R):
    rp = Path(root)
    if rp == D or D in rp.parents or rp == R / 'data/derived/devset_images':
        dirs[:] = []; continue
    dirs[:] = [d for d in dirs if d not in ('.venv', '.git')]
    for f in fs:
        try:
            if (rp / f).stat().st_mtime > START:
                touched.append(str((rp / f).relative_to(R)))
        except OSError:
            pass
ok &= not touched; print('4. 啟動後（11-16 15:29 UTC）R 底下、D 與 devset_images 以外被修改的檔案數：', len(touched), touched[:10])
print('ALL OK' if ok else 'SOMETHING FAILED')
