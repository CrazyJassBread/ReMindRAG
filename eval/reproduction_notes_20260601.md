# ReMindRAG Hotpot 复现实验记录（2026-06-01）

## 记录范围

本记录整理截至 `2026-06-01 14:50:46 +08:00` 已经落盘的 HotpotQA 批量复现实验结果。数据严格来自以下结果文件和日志：

- 记忆版结果：`eval/database/repro_hotpot_batch_paperjudge_20260528/{index}/input_{question_type}.json`
- 无记忆基线结果：`eval/database/repro_hotpot_batch_nomemory_paperjudge_20260528/{index}/input_{question_type}.json`
- 异常样本日志：`eval/database/repro_hotpot_batch_paperjudge_20260528/15/log_2026-05-31_17-54-36.log`

判分方式：

- 正确性读取 `input_*.json` 中的 `check_response` 字段。
- 只有 `check_response == "True"` 计为正确。
- Token 统计读取 `usage.construction.total_tokens`、`usage.query_and_grade.total_tokens` 和 `usage.total.total_tokens`。

实验配置来自结果文件中的 `config` 字段：

- Backbone：`gpt-4o-mini`
- Judge：`gpt-4o-2024-11-20`
- 记忆阈值：`strong_connection_threshold=0.5`
- 并发数：`parallel=1`
- 记忆版运行名：`repro_hotpot_batch_paperjudge_20260528`
- 无记忆基线运行名：`repro_hotpot_batch_nomemory_paperjudge_20260528`

## 当前完成状态

| 运行 | 问题类型 | 范围 | 完成进度 | 正确数 | 缺失 index | 错误 index |
| --- | --- | --- | ---: | ---: | --- | --- |
| 记忆版 | origin | 1..30 | 30/30 | 23/30 | 无 | 2, 13, 14, 21, 22, 23, 26 |
| 记忆版 | similar | 1..30 | 30/30 | 21/30 | 无 | 2, 10, 13, 14, 19, 21, 22, 23, 26 |
| 记忆版 | different | 1..30 | 29/30 | 23/29 | 15 | 2, 7, 9, 21, 22, 25 |
| 无记忆版 | similar | 1..30 | 30/30 | 17/30 | 无 | 2, 3, 5, 6, 10, 13, 14, 15, 19, 21, 22, 23, 26 |
| 无记忆版 | different | 1..30 | 10/30 | 8/10 | 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 | 2, 7 |

## 分批统计

### 记忆版：origin

| 范围 | 完成进度 | 正确数 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 9/10 | 2 | 181,812 | 241,160 | 422,972 | 497 |
| 11..30 | 20/20 | 14/20 | 13, 14, 21, 22, 23, 26 | 334,044 | 857,278 | 1,191,322 | 1,134 |
| 1..30 | 30/30 | 23/30 | 2, 13, 14, 21, 22, 23, 26 | 515,856 | 1,098,438 | 1,614,294 | 1,631 |

### 记忆版：similar

| 范围 | 完成进度 | 正确数 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 8/10 | 2, 10 | 0 | 143,619 | 143,619 | 119 |
| 11..30 | 20/20 | 13/20 | 13, 14, 19, 21, 22, 23, 26 | 0 | 481,030 | 481,030 | 333 |
| 1..30 | 30/30 | 21/30 | 2, 10, 13, 14, 19, 21, 22, 23, 26 | 0 | 624,649 | 624,649 | 452 |

### 记忆版：different

| 范围 | 完成进度 | 正确数 | 缺失 index | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 7/10 | 无 | 2, 7, 9 | 0 | 51,533 | 51,533 | 60 |
| 11..30 | 19/20 | 16/19 | 15 | 21, 22, 25 | 0 | 333,771 | 333,771 | 244 |
| 1..30 | 29/30 | 23/29 | 15 | 2, 7, 9, 21, 22, 25 | 0 | 385,304 | 385,304 | 304 |

记忆版 `different` 的 `11..30` 已完成 index：

```text
11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30
```

记忆版 `different` 的 `11..30` 缺失 index：

```text
15
```

### 无记忆版：similar

| 范围 | 完成进度 | 正确数 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 5/10 | 2, 3, 5, 6, 10 | 163,977 | 150,044 | 314,021 | 402 |
| 11..30 | 20/20 | 12/20 | 13, 14, 15, 19, 21, 22, 23, 26 | 335,963 | 366,299 | 702,262 | 851 |
| 1..30 | 30/30 | 17/30 | 2, 3, 5, 6, 10, 13, 14, 15, 19, 21, 22, 23, 26 | 499,940 | 516,343 | 1,016,283 | 1,253 |

说明：`start_Hotpot.py` 在本轮重新运行 `similar 11..30` 时输出了 `Total correct answers: 0/0`，原因是这些 `input_similar.json` 已经存在，脚本跳过已完成样本但不会把跳过样本计入本轮汇总。上表直接读取 `input_similar.json`，因此反映实际已落盘结果。

### 无记忆版：different

| 范围 | 完成进度 | 正确数 | 缺失 index | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 8/10 | 无 | 2, 7 | 0 | 1,152,270 | 1,152,270 | 640 |
| 11..30 | 0/20 | 0/0 | 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 | 无 | 0 | 0 | 0 | 0 |
| 1..30 | 10/30 | 8/10 | 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 | 2, 7 | 0 | 1,152,270 | 1,152,270 | 640 |

## 已闭合对比

### Similar：1..30

| 运行 | 完成进度 | 正确数 | Query+Judge Tokens | Total Tokens |
| --- | ---: | ---: | ---: | ---: |
| 记忆版 | 30/30 | 21/30 | 624,649 | 624,649 |
| 无记忆版 | 30/30 | 17/30 | 516,343 | 1,016,283 |

### Similar：11..30

| 运行 | 完成进度 | 正确数 | Query+Judge Tokens | Total Tokens |
| --- | ---: | ---: | ---: | ---: |
| 记忆版 | 20/20 | 13/20 | 481,030 | 481,030 |
| 无记忆版 | 20/20 | 12/20 | 366,299 | 702,262 |

### Different：1..10

| 运行 | 完成进度 | 正确数 | Query+Judge Tokens | Total Tokens |
| --- | ---: | ---: | ---: | ---: |
| 记忆版 | 10/10 | 7/10 | 51,533 | 51,533 |
| 无记忆版 | 10/10 | 8/10 | 1,152,270 | 1,152,270 |

`different 11..30` 尚未闭合，因为记忆版缺失 index `15`，无记忆版 `different 11..30` 尚未开始。

## 异常样本：记忆版 different index 15

记忆版 `different index 15` 目前没有生成：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/input_different.json
```

最新日志文件：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/log_2026-05-31_17-54-36.log
```

日志统计：

| 项目 | 数值 |
| --- | ---: |
| 最后更新时间 | 2026-05-31 23:38:08 |
| 文件大小 | 10,518,192 bytes |
| 行数 | 138,069 |
| `Data Enough? False` | 2,152 |
| `Jumps: 7` | 2,132 |
| `Select Next Node` | 2,152 |
| `No node was identified` | 305 |
| `Traceback` | 0 |
| `Exception` | 0 |
| `RateLimit` | 0 |
| `insufficient_quota` | 0 |
| `APIConnectionError` | 0 |
| 日志尾部是否包含最终答案或判分 | False |

根据日志尾部，模型反复在 `anchor-3`、`anchor-10`、`Brown County`、`United States`、`Hiawatha` 等节点之间选择下一跳，并持续判断 `Data Enough? False`。日志中没有 API 限额或连接异常，因此当前证据表明这是图搜索循环/无法收敛导致的未完成样本，而不是 API 调用失败。

## 后续未完成项

仍需补齐的部分：

1. 记忆版 `different index 15`。
2. 无记忆版 `different index 11..30`。

建议优先运行无记忆版 `different 11..30`，因为记忆版 `different index 15` 已经多次显示异常长搜索，继续硬跑可能再次消耗大量 token 且无结果。
