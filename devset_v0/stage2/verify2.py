"""階段 2 自我驗收（重跑分析 → 輸出 md5 相同；報告數字 = JSON；無殘留 vLLM；階段 1 sha256 不變；D 底下 S 以外沒被改）。"""
import hashlib, json, subprocess, re, os, time
from pathlib import Path
S = Path(__file__).resolve().parent; D = S.parent
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
files = [S/'results/stage2_analysis.json', S/'results/stage2_analysis.md', S/'REPORT_白話版.md']
b = [md5(f) for f in files]
subprocess.run(['python3','-I',str(S/'compute_qualified.py')],check=True,capture_output=True)
subprocess.run(['python3','-I',str(S/'analyze.py')],check=True,capture_output=True)
subprocess.run(['python3','-I',str(S/'make_report2.py')],check=True,capture_output=True)
print('1 重跑後輸出 md5 相同:', b == [md5(f) for f in files])
J = json.load(open(files[0])); rep = files[2].read_text(encoding='utf-8'); bad = 0
for c, v in J['cells'].items():
    ZH = {'mid_century':'mid-century','industrial':'industrial','farmhouse_rustic':'farmhouse/rustic','boho':'boho','coastal':'coastal','traditional':'traditional','chair':'chair','table':'table','lamp':'lamp','chandelier_pendant':'吊燈','wall_art':'wall art'}
    nm = ' × '.join(ZH[x] for x in c.split('|'))
    m = [l for l in rep.splitlines() if l.startswith(f'| {nm} | ') and f"{v['qualified']} / {v['target']} | {v['status']}" in l]
    bad += len(m) != 1 or f"| {v['single_item_yes_conf2']} | {v['queue_left']} |" not in m[0]
print('2 報告每格列與 JSON 不一致的格數:', bad, '；總合格', J['summary']['qualified_total'], f"{J['summary']['qualified_total']} 件" in rep, f"${J['cost']['claude_total_usd']:.2f}" in rep)
r = subprocess.run('cd %s && sha256sum stage1/*.jsonl | diff - stage2/stage1_sha256_before.txt' % D, shell=True, capture_output=True, text=True)
print('3 階段 1 的 jsonl sha256 與 before 相同:', r.returncode == 0)
ps = subprocess.run('ps -u $USER -o pid,cmd | grep -E "devset2" | grep -v grep; ss -ltn | grep -E ":808[1-9] "', shell=True, capture_output=True, text=True).stdout.strip()
print('4 沒有殘留 devset2 vLLM / 8081-8089 沒被佔用:', not ps, ps[:200])
t0 = time.mktime(time.strptime('2026-11-17 07:11', '%Y-%m-%d %H:%M')) - time.timezone
touched = []
for root, dirs, fs in os.walk(D):
    rp = Path(root)
    if rp == S or S in rp.parents: dirs[:] = []; continue
    for f in fs:
        try:
            if (rp / f).stat().st_mtime > t0: touched.append(str((rp / f).relative_to(D)))
        except OSError: pass
print('5 D 底下 S 以外啟動後被修改的檔案:', touched)
