# 階段 2 分析（由 analyze.py 產生）

合格商品 891 / 目標 637；Claude 花費 $22.6722（主標註 $17.2673、單一商品欄位 $5.4049）

| 格子 | 已標 | Claude 正票 | 合格/目標 | 狀態 | 階段1合格率 | 階段2合格率 | queue 剩 | 單一商品候選 | 情境二自由維度 |
|---|---|---|---|---|---|---|---|---|---|
| mid_century|chair | 79 | 41 | 41/26 | 達標 | 53% | 51% | 221 | 26 | color:9, material:4, shape:2 |
| mid_century|table | 87 | 36 | 39/26 | 達標 | 50% | 42% | 213 | 36 | color:7, material:4, shape:3 |
| mid_century|lamp | 125 | 38 | 30/26 | 達標 | 43% | 18% | 175 | 25 | color:4, material:3, shape:4 |
| mid_century|chandelier_pendant | 59 | 34 | 42/26 | 達標 | 70% | 72% | 241 | 42 | color:2, material:2, shape:4 |
| mid_century|wall_art | 117 | 25 | 20/13 | 達標 | 17% | 17% | 183 | 16 | （不出情境二） |
| industrial|chair | 135 | 70 | 67/26 | 達標 | 53% | 49% | 41 | 16 | color:8, material:3, shape:2 |
| industrial|table | 55 | 33 | 32/26 | 達標 | 53% | 64% | 245 | 31 | color:4, material:3, shape:2 |
| industrial|lamp | 50 | 32 | 31/26 | 達標 | 60% | 65% | 250 | 27 | color:5, material:2, shape:5 |
| industrial|chandelier_pendant | 62 | 37 | 37/26 | 達標 | 50% | 69% | 238 | 33 | color:2, material:2, shape:5 |
| industrial|wall_art | 93 | 18 | 18/13 | 達標 | 23% | 17% | 68 | 14 | （不出情境二） |
| farmhouse_rustic|chair | 300 | 54 | 51/26 | 達標 | 10% | 18% | 0 | 30 | color:8, material:2, shape:2 |
| farmhouse_rustic|table | 105 | 34 | 30/26 | 達標 | 33% | 27% | 195 | 28 | color:5, shape:3 |
| farmhouse_rustic|lamp | 186 | 47 | 38/26 | 達標 | 10% | 22% | 114 | 21 | color:9, material:4, shape:4 |
| farmhouse_rustic|chandelier_pendant | 131 | 50 | 33/26 | 達標 | 30% | 24% | 169 | 31 | color:5, material:3, shape:5 |
| farmhouse_rustic|wall_art | 30 | 17 | 16/13 | 達標 | 53% | - | 270 | 14 | （不出情境二） |
| boho|chair | 59 | 32 | 33/26 | 達標 | 53% | 59% | 29 | 29 | color:7, material:2, shape:3 |
| boho|lamp | 146 | 37 | 29/26 | 達標 | 20% | 20% | 0 | 25 | color:8, material:4, shape:4 |
| boho|chandelier_pendant | 50 | 33 | 34/26 | 達標 | 70% | 65% | 121 | 28 | color:6, shape:4 |
| boho|wall_art | 30 | 20 | 19/13 | 達標 | 63% | - | 270 | 16 | （不出情境二） |
| coastal|chair | 153 | 29 | 30/26 | 達標 | 27% | 18% | 0 | 26 | color:5, material:5, shape:2 |
| coastal|table | 162 | 41 | 32/26 | 達標 | 20% | 20% | 11 | 30 | color:7, material:4, shape:2 |
| coastal|lamp | 75 | 38 | 31/26 | 達標 | 47% | 38% | 225 | 22 | color:7, material:6, shape:4 |
| coastal|wall_art | 30 | 26 | 23/13 | 達標 | 77% | - | 270 | 19 | （不出情境二） |
| traditional|chair | 85 | 32 | 31/26 | 達標 | 33% | 38% | 215 | 27 | color:8, material:4, shape:2 |
| traditional|table | 85 | 34 | 33/26 | 達標 | 37% | 40% | 215 | 31 | color:7, material:3, shape:3 |
| traditional|lamp | 98 | 38 | 37/26 | 達標 | 40% | 37% | 202 | 29 | color:5, material:4, shape:3 |
| traditional|chandelier_pendant | 87 | 36 | 34/26 | 達標 | 43% | 37% | 213 | 34 | color:5, material:2, shape:3 |

## 三方一致性（κ / 兩兩一致率）
- stage1_27cells：三位都成功 796 件
  - style: κ=0.672；claude-qwen=68%、claude-gemma=68%、qwen-gemma=76%
  - category: κ=0.933；claude-qwen=95%、claude-gemma=93%、qwen-gemma=95%
  - color: κ=0.714；claude-qwen=77%、claude-gemma=70%、qwen-gemma=78%
  - material: κ=0.787；claude-qwen=81%、claude-gemma=79%、qwen-gemma=88%
  - shape: κ=0.718；claude-qwen=86%、claude-gemma=77%、qwen-gemma=79%
- stage2_new：三位都成功 1831 件
  - style: κ=0.615；claude-qwen=62%、claude-gemma=64%、qwen-gemma=71%
  - category: κ=0.934；claude-qwen=95%、claude-gemma=94%、qwen-gemma=96%
  - color: κ=0.696；claude-qwen=73%、claude-gemma=68%、qwen-gemma=79%
  - material: κ=0.752；claude-qwen=78%、claude-gemma=77%、qwen-gemma=86%
  - shape: κ=0.64；claude-qwen=83%、claude-gemma=72%、qwen-gemma=72%
