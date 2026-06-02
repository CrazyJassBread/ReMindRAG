# HotpotQA 复现实验结果总汇（index 1..30）

生成日期：`2026-06-01`

## 数据来源

本文件汇总当前已经落盘的 HotpotQA index `1..30` 复现实验结果，数据来自：

- 记忆版：`eval/database/repro_hotpot_batch_paperjudge_20260528/{index}/input_{question_type}.json`
- 无记忆基线：`eval/database/repro_hotpot_batch_nomemory_paperjudge_20260528/{index}/input_{question_type}.json`
- 记忆版 `different index 15` 异常日志：`eval/database/repro_hotpot_batch_paperjudge_20260528/15/log_2026-05-31_17-54-36.log`

统计口径：

- 正确性读取 `check_response`，且仅 `check_response == "True"` 计为正确。
- Token 读取 `usage.construction.total_tokens`、`usage.query_and_grade.total_tokens` 和 `usage.total.total_tokens`。
- `similar` 和 `different` 的记忆版复用 `origin` 阶段写入的图，因此 Construction Tokens 为 `0`。
- 记忆版 `different index 15` 未生成 `input_different.json`，所以该组按 `29/30` 已完成样本统计。

实验配置：

| 配置项 | 值 |
| --- | --- |
| Backbone | `gpt-4o-mini` |
| Judge | `gpt-4o-2024-11-20` |
| `parallel` | `1` |
| `strong_connection_threshold` | `0.5` |
| 记忆版运行名 | `repro_hotpot_batch_paperjudge_20260528` |
| 无记忆基线运行名 | `repro_hotpot_batch_nomemory_paperjudge_20260528` |

## 总体结果

| 实验 | 问题类型 | 范围 | 完成进度 | 正确率 | 错误 index | 缺失 index | Construction Tokens | Query+Judge Tokens | Total Tokens |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 记忆版 | origin | 1..30 | 30/30 | 23/30 | 2, 13, 14, 21, 22, 23, 26 | 无 | 515,856 | 1,098,438 | 1,614,294 |
| 记忆版 | similar | 1..30 | 30/30 | 21/30 | 2, 10, 13, 14, 19, 21, 22, 23, 26 | 无 | 0 | 624,649 | 624,649 |
| 记忆版 | different | 1..30 | 29/30 | 23/29 | 2, 7, 9, 21, 22, 25 | 15 | 0 | 385,304 | 385,304 |
| 无记忆版 | similar | 1..30 | 30/30 | 17/30 | 2, 3, 5, 6, 10, 13, 14, 15, 19, 21, 22, 23, 26 | 无 | 499,940 | 516,343 | 1,016,283 |
| 无记忆版 | different | 1..30 | 30/30 | 23/30 | 2, 7, 15, 21, 22, 25, 27 | 无 | 0 | 1,596,177 | 1,596,177 |

## 分批结果

### 记忆版 origin

| 范围 | 完成进度 | 正确率 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 9/10 | 2 | 181,812 | 241,160 | 422,972 | 497 |
| 11..30 | 20/20 | 14/20 | 13, 14, 21, 22, 23, 26 | 334,044 | 857,278 | 1,191,322 | 1,134 |
| 1..30 | 30/30 | 23/30 | 2, 13, 14, 21, 22, 23, 26 | 515,856 | 1,098,438 | 1,614,294 | 1,631 |

### 记忆版 similar

| 范围 | 完成进度 | 正确率 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 8/10 | 2, 10 | 0 | 143,619 | 143,619 | 119 |
| 11..30 | 20/20 | 13/20 | 13, 14, 19, 21, 22, 23, 26 | 0 | 481,030 | 481,030 | 333 |
| 1..30 | 30/30 | 21/30 | 2, 10, 13, 14, 19, 21, 22, 23, 26 | 0 | 624,649 | 624,649 | 452 |

### 记忆版 different

| 范围 | 完成进度 | 正确率 | 错误 index | 缺失 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 7/10 | 2, 7, 9 | 无 | 0 | 51,533 | 51,533 | 60 |
| 11..30 | 19/20 | 16/19 | 21, 22, 25 | 15 | 0 | 333,771 | 333,771 | 244 |
| 1..30 | 29/30 | 23/29 | 2, 7, 9, 21, 22, 25 | 15 | 0 | 385,304 | 385,304 | 304 |

### 无记忆版 similar

| 范围 | 完成进度 | 正确率 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 5/10 | 2, 3, 5, 6, 10 | 163,977 | 150,044 | 314,021 | 402 |
| 11..30 | 20/20 | 12/20 | 13, 14, 15, 19, 21, 22, 23, 26 | 335,963 | 366,299 | 702,262 | 851 |
| 1..30 | 30/30 | 17/30 | 2, 3, 5, 6, 10, 13, 14, 15, 19, 21, 22, 23, 26 | 499,940 | 516,343 | 1,016,283 | 1,253 |

### 无记忆版 different

| 范围 | 完成进度 | 正确率 | 错误 index | Construction Tokens | Query+Judge Tokens | Total Tokens | Requests |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1..10 | 10/10 | 8/10 | 2, 7 | 0 | 1,152,270 | 1,152,270 | 640 |
| 11..30 | 20/20 | 15/20 | 15, 21, 22, 25, 27 | 0 | 443,907 | 443,907 | 322 |
| 1..30 | 30/30 | 23/30 | 2, 7, 15, 21, 22, 25, 27 | 0 | 1,596,177 | 1,596,177 | 962 |

## 记忆版与无记忆版对比

### Similar：完整 index 1..30

| 指标 | 记忆版 | 无记忆版 | 差值 |
| --- | ---: | ---: | ---: |
| 完成进度 | 30/30 | 30/30 | - |
| 正确率 | 21/30 | 17/30 | 记忆版 +4 |
| Query+Judge Tokens | 624,649 | 516,343 | 记忆版多 108,306 |
| Total Tokens | 624,649 | 1,016,283 | 记忆版少 391,634 |
| Total Token 节省比例 | - | - | 38.54% |

说明：`similar` 中，记忆版查询阶段本身比无记忆版多消耗 `108,306` tokens，但由于复用 `origin` 阶段构建的图，记忆版 Total Tokens 仍比无记忆版少 `391,634`。

### Similar：index 11..30

| 指标 | 记忆版 | 无记忆版 | 差值 |
| --- | ---: | ---: | ---: |
| 完成进度 | 20/20 | 20/20 | - |
| 正确率 | 13/20 | 12/20 | 记忆版 +1 |
| Query+Judge Tokens | 481,030 | 366,299 | 记忆版多 114,731 |
| Total Tokens | 481,030 | 702,262 | 记忆版少 221,232 |
| Total Token 节省比例 | - | - | 31.50% |

### Different：index 1..10

| 指标 | 记忆版 | 无记忆版 | 差值 |
| --- | ---: | ---: | ---: |
| 完成进度 | 10/10 | 10/10 | - |
| 正确率 | 7/10 | 8/10 | 记忆版 -1 |
| Query+Judge Tokens | 51,533 | 1,152,270 | 记忆版少 1,100,737 |
| Total Token 节省比例 | - | - | 95.53% |

### Different：index 11..30 共同完成样本

共同完成样本排除记忆版缺失的 index `15`，即比较 `19` 个 index。

| 指标 | 记忆版 | 无记忆版（排除 index 15） | 差值 |
| --- | ---: | ---: | ---: |
| 完成进度 | 19/19 | 19/19 | - |
| 正确率 | 16/19 | 15/19 | 记忆版 +1 |
| Query+Judge Tokens | 333,771 | 356,327 | 记忆版少 22,556 |
| Total Token 节省比例 | - | - | 6.33% |

### Different：index 1..30 共同完成样本

共同完成样本排除记忆版缺失的 index `15`，即比较 `29` 个 index。

| 指标 | 记忆版 | 无记忆版（排除 index 15） | 差值 |
| --- | ---: | ---: | ---: |
| 完成进度 | 29/29 | 29/29 | - |
| 正确率 | 23/29 | 23/29 | 持平 |
| Query+Judge Tokens | 385,304 | 1,508,597 | 记忆版少 1,123,293 |
| Total Token 节省比例 | - | - | 74.46% |

需要注意：无记忆版 `different index 2` 单条消耗 `1,030,069` tokens，是 `different 1..30` 总体 token 节省比例很高的主要原因。

## 异常与未完成样本

### 记忆版 different index 15

该样本未生成：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/input_different.json
```

最新异常日志：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/log_2026-05-31_17-54-36.log
```

日志摘要：

| 日志项 | 数值 |
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

日志显示该样本反复在 `anchor-3`、`anchor-10`、`Brown County`、`United States`、`Hiawatha` 等节点之间选择下一跳，并持续判断 `Data Enough? False`。没有 API 限额或连接异常证据，因此当前记录中将其标为图搜索循环/无法收敛导致的异常未完成样本。

## 当前结论

- `origin 1..30` 的图构建与原始问题查询已完成，正确率为 `23/30`。
- `similar 1..30` 已完成闭合对比：记忆版正确率 `21/30`，无记忆版 `17/30`；记忆版 Total Tokens 少 `391,634`。
- `different 1..30` 中，记忆版缺失异常样本 index `15`。在共同完成的 `29` 个样本上，记忆版与无记忆版正确数均为 `23/29`，但记忆版少消耗 `1,123,293` Query+Judge tokens。
- 目前唯一未落盘结果是记忆版 `different index 15`；其他 Hotpot index `1..30` 相关结果均已落盘。
