"""階段 0 第 3 步：下載主圖到 R/data/derived/devset_images/<parent_asin>.jpg。可續跑（已有且可開啟的跳過）。

平行 8、每張最多試 3 次、失敗記錄在 stage0/download_log.jsonl。總大小 > 5 GB 或 /mnt/raid0 可用 < 250 GB 就停。
用法： .venv/bin/python -B devset_v0/stage0/s0_download.py
"""
import hashlib, io, json, os, shutil, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
IMG = HERE.parents[1] / 'data' / 'derived' / 'devset_images'
IMG.mkdir(parents=True, exist_ok=True)
LOG = HERE / 'download_log.jsonl'
MAX_BYTES, MIN_FREE = 5 * 1024**3, 250 * 1024**3
lock = threading.Lock(); stop = threading.Event(); total = [0]


def ok_image(data):
    try:
        im = Image.open(io.BytesIO(data)); im.load(); return im
    except Exception:
        return None


def fetch(r):
    if stop.is_set():
        return None
    asin, url = r['parent_asin'], r['img_url']
    dst = IMG / f'{asin}.jpg'
    err = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=30).read()
            im = ok_image(data)
            if im is None:
                raise ValueError('not an image')
            converted = False
            if im.format != 'JPEG':            # 少數是 PNG / GIF / WebP：轉成 JPEG 存
                buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=95); data = buf.getvalue(); converted = True
            tmp = dst.with_suffix('.part'); tmp.write_bytes(data); os.replace(tmp, dst)
            with lock:
                total[0] += len(data)
                if total[0] > MAX_BYTES or shutil.disk_usage('/mnt/raid0').free < MIN_FREE:
                    stop.set()
            return {'parent_asin': asin, 'ok': True, 'bytes': len(data), 'attempts': attempt, 'converted': converted,
                    'size': im.size, 'url': url}
        except Exception as e:  # noqa
            err = f'{type(e).__name__}: {e}'[:200]; time.sleep(2 * attempt)
    return {'parent_asin': asin, 'ok': False, 'error': err, 'attempts': 3, 'url': url}


def main():
    rows = [json.loads(l) for l in open(HERE / 'download_list.jsonl')]
    done = {}
    if LOG.exists():
        for l in open(LOG):
            d = json.loads(l); done[d['parent_asin']] = d
    todo = [r for r in rows if not (done.get(r['parent_asin'], {}).get('ok') and (IMG / f"{r['parent_asin']}.jpg").exists())
            and not (done.get(r['parent_asin']) and not done[r['parent_asin']]['ok'] and '--retry-failed' not in sys.argv)]
    total[0] = sum(p.stat().st_size for p in IMG.glob('*.jpg'))
    print(f'{len(rows)} in list, {len(todo)} to download, {total[0]/1e9:.2f} GB on disk', flush=True)
    n = 0
    with ThreadPoolExecutor(8) as ex, open(LOG, 'a') as log:
        for res in ex.map(fetch, todo):
            if res is None:
                continue
            log.write(json.dumps(res) + '\n'); log.flush(); n += 1
            if n % 500 == 0:
                print(n, f'{total[0]/1e9:.2f} GB', flush=True)
    print('done', n, f'{total[0]/1e9:.2f} GB', 'STOPPED_BY_LIMIT' if stop.is_set() else '', flush=True)


if __name__ == '__main__':
    main()
