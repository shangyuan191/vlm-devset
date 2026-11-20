#!/usr/bin/env python3
"""工作項目 D：main table 的 metric 實作 + K=5 計算範例（不需要任何模型或資料，純 Python）。

統一定義（對應任務文件第 2.3 節與 D_main_table/main_table_draft.md 第 3 節）：
  每個商品 = {維度: 單一值}，維度固定為 DIMS。
  每題的限制寫成「允許值集合」A_d：
      等於限制  style == mid-century  →  A_style = {mid-century}
      不等於限制 category != chair     →  A_category = 全部值 − {chair}
      沒限制                           →  A_d = 全部值
  商品 i「合格」(valid) ⇔ 對每個有限制的維度 d，i[d] ∈ A_d。
  維度 d 是「固定維度」⇔ 合格候選在 d 上只剩 1 種值；其餘有 ≥2 種值的維度是「自由維度」。
  （所以等於限制 → 固定；不等於限制 → 仍是自由維度，只是少了一個值。）

  Align@K   = 選出的 K 個中合格的比例
  Div@K     = 只看選出的合格商品 V；對每個自由維度 d：
                 cov_d = |V 在 d 上的不同值| / min(|V|, n_d)
              n_d = 合格候選在 d 上實際存在的不同值數；Div@K = 自由維度平均。|V| < 2 時為 None（不定義）。
  EffCov@K  = 同上，但分母改為 min(K, n_d)；|V| = 0 時為 0。headline metric。

用法：python3 metrics.py            # 印出 K=5 兩個情境 + negation 的完整計算過程
"""
import itertools, random
from fractions import Fraction

DIMS = ("style", "category", "color", "material", "shape")


def is_valid(item, allowed):
    return all(item[d] in A for d, A in allowed.items())


def free_dims(pool, allowed):
    """回傳 {自由維度: n_d}；n_d = 合格候選在該維度的不同值數，只收 n_d >= 2 的維度。"""
    valid = [c for c in pool if is_valid(c, allowed)]
    out = {}
    for d in DIMS:
        n = len({c[d] for c in valid})
        if n >= 2: out[d] = n
    return out


def score(selected, pool, allowed, K, verbose=False):
    V = [i for i in selected if is_valid(i, allowed)]
    F = free_dims(pool, allowed)
    align = Fraction(len(V), K)
    div_terms, eff_terms = {}, {}
    for d, n_d in F.items():
        u = len({i[d] for i in V})
        if len(V) >= 2: div_terms[d] = Fraction(u, min(len(V), n_d))
        eff_terms[d] = Fraction(u, min(K, n_d))
        if verbose:
            print(f"    {d:9s} n_d={n_d}  選中合格商品的不同值={sorted({i[d] for i in V})} → u={u}"
                  f"  Div 項 = {u}/min({len(V)},{n_d})" + (f" = {float(div_terms[d]):.3f}" if d in div_terms else " = (|V|<2，不定義)")
                  + f"  EffCov 項 = {u}/min({K},{n_d}) = {float(eff_terms[d]):.3f}")
    div = (sum(div_terms.values()) / len(div_terms)) if div_terms else None
    eff = (sum(eff_terms.values()) / len(eff_terms)) if eff_terms else Fraction(0)
    return {"Align": float(align), "Div": None if div is None else float(div), "EffCov": float(eff), "n_valid": len(V), "free_dims": F}


def oracle(pool, allowed, K):
    """暴力窮舉所有 K 子集，取 EffCov 最高者（同分取 Align 高者）。上限。"""
    best = None
    valid = [c for c in pool if is_valid(c, allowed)]
    src = valid if len(valid) >= K else pool
    for S in itertools.combinations(src, K):
        s = score(list(S), pool, allowed, K)
        key = (s["EffCov"], s["Align"])
        if best is None or key > best[0]: best = (key, s, S)
    return best[1], best[2]


def random_expect(pool, allowed, K, n=20000, seed=0):
    """隨機選 K 個的期望值（蒙地卡羅，seed 固定可重跑）。Div 只對 |V|>=2 的抽樣平均。"""
    rng = random.Random(seed); a = e = 0.0; dv = []
    for _ in range(n):
        s = score(rng.sample(pool, K), pool, allowed, K)
        a += s["Align"]; e += s["EffCov"]
        if s["Div"] is not None: dv.append(s["Div"])
    return {"Align": a / n, "EffCov": e / n, "Div(|V|>=2)": sum(dv) / len(dv) if dv else None, "P(|V|>=2)": len(dv) / n}


# ----------------------------------------------------------------------------- 範例資料
def item(id_, style, category, color, material, shape):
    return dict(id=id_, style=style, category=category, color=color, material=material, shape=shape)


# query：一張 mid-century 風格的單人扶手椅（query 商品本身與同 parent_asin 的變體不放進候選）
POOL = [
    # 合格（情境二）：mid-century 的椅子 —— 在顏色 / 材質 / 形狀上刻意有 ≥4 種值，另放兩張很像的（c1、c2）
    item("c1", "mid-century", "chair", "brown", "wood", "curved"),
    item("c2", "mid-century", "chair", "brown", "wood", "curved"),     # 和 c1 幾乎一樣（測重複）
    item("c3", "mid-century", "chair", "beige", "fabric", "boxy"),
    item("c4", "mid-century", "chair", "green", "velvet", "round"),
    item("c5", "mid-century", "chair", "black", "leather", "angular"),
    item("c6", "mid-century", "chair", "white", "plastic", "round"),
    # 同品項、不同風格（困難干擾項）
    item("d1", "farmhouse", "chair", "white", "wood", "boxy"),
    item("d2", "industrial", "chair", "black", "metal", "angular"),
    item("d3", "glam", "chair", "pink", "velvet", "curved"),
    # 同風格、不同品項（情境二的干擾項；情境一的合格商品）
    item("s1", "mid-century", "lamp", "brass", "metal", "round"),
    item("s2", "mid-century", "table", "brown", "wood", "round"),
    item("s3", "mid-century", "sofa", "orange", "fabric", "boxy"),
    item("s4", "mid-century", "rug", "beige", "wool", "angular"),
    # 隨機
    item("r1", "boho", "rug", "multicolor", "jute", "round"),
    item("r2", "coastal", "lamp", "white", "ceramic", "round"),
]
BY = {c["id"]: c for c in POOL}
ALL = {d: {c[d] for c in POOL} for d in DIMS}


def show(title, allowed, picks, K=5):
    print(f"\n=== {title} ===")
    print("限制（允許值）:", {d: (sorted(A) if len(A) <= 2 else f"全部值 − {sorted(ALL[d] - A)}") for d, A in allowed.items()})
    sel = [BY[x] for x in picks]
    for i in sel: print(f"  選 {i['id']}: {i['style']:11s} {i['category']:6s} {i['color']:6s} {i['material']:8s} {i['shape']:8s} 合格={is_valid(i, allowed)}")
    s = score(sel, POOL, allowed, K, verbose=True)
    print(f"  → 合格 {s['n_valid']}/{K}；Align@5 = {s['Align']:.3f}；Div@5 = {s['Div'] if s['Div'] is None else round(s['Div'], 3)}；EffCov@5 = {s['EffCov']:.3f}；自由維度 = {s['free_dims']}")
    o, S = oracle(POOL, allowed, K)
    print(f"  Oracle：選 {[x['id'] for x in S]} → Align {o['Align']:.3f} Div {o['Div']:.3f} EffCov {o['EffCov']:.3f}")
    print(f"  Random 期望值（2 萬次抽樣，seed 0）：{ {k: (round(v, 3) if v is not None else None) for k, v in random_expect(POOL, allowed, K).items()} }")
    return s


if __name__ == "__main__":
    # 情境二：同風格的「椅子」→ 限制 style、category；自由維度 color、material、shape
    s2 = {"style": {"mid-century"}, "category": {"chair"}}
    show("情境二（模型 A：挑到重複款 + 1 個風格錯 + 1 個品項錯）", s2, ["c1", "c2", "c3", "d1", "s1"])
    show("情境二（模型 B：5 個都合格，但顏色材質重複）", s2, ["c1", "c2", "c3", "c4", "c5"])
    # 情境一：同風格的「家具」→ 只限制 style；自由維度 category、color、material、shape
    s1 = {"style": {"mid-century"}}
    show("情境一（模型 C：錨定偏誤，4 張椅子 + 1 盞燈）", s1, ["c1", "c3", "c4", "c5", "s1"])
    show("情境一（模型 D：品項分散）", s1, ["c3", "s1", "s2", "s3", "s4"])
    # Negation：同風格的家具，但「不要椅子」→ category 是 ≠ 限制，仍是自由維度
    neg = {"style": {"mid-century"}, "category": ALL["category"] - {"chair"}}
    show("Negation（同風格、不要椅子）", neg, ["s1", "s2", "s3", "s4", "c1"])
    # 邊界：沒有任何合格商品
    show("邊界情況：5 個都不合格（情境二）", s2, ["d1", "d2", "d3", "r1", "r2"])
