# ReMindRAG 论文复现实验报告：HotpotQA index 1..30

日期：`2026-06-01`

## 1. 论文概述

原论文 **ReMindRAG: Low-Cost LLM-Guided Knowledge Graph Traversal for Efficient RAG** 关注复杂问答场景中的检索增强生成问题。传统 RAG 往往依赖向量相似度召回，面对多跳推理、长距离依赖或查询改写时，容易召回不完整证据，或需要反复扩大检索范围而增加成本。

ReMindRAG 的核心思想是把文档构造成异构知识图，并让 LLM 在图上进行受控遍历：

1. 对文档切分成 chunks。
2. 从 chunk 中抽取实体与关系，构建包含实体节点、chunk 节点、关系边和连接边的异构图。
3. 查询时，先定位初始实体/节点，再由 LLM 判断当前证据是否足够。
4. 若信息不足，LLM 继续选择下一跳节点，直到信息足够或达到搜索限制。
5. 对成功遍历路径进行记忆更新，增强有用边、惩罚无效边，使后续相似或相关查询可以更低成本地重用路径。

论文声称，这种 “Retrieve and Memorize” 机制不需要额外训练，就可以在相似查询和后续查询中降低检索成本，并在多跳问答与长依赖任务中保持或提升准确率。

## 2. 原论文实验设置与目标

原论文在多个任务上评估 ReMindRAG，其中与本次复现最相关的是 HotpotQA 多跳问答实验。论文中将 HotpotQA 对应为 **Multi-Hop QA**，并使用 LLM-as-judge 评估预测答案与标准答案的语义一致性。

原论文相关设置包括：

- Dataset：HotpotQA，用于多跳问答。
- Backbone LLM：包括 `gpt-4o-mini` 和 `DeepSeek-V3`。
- Judge LLM：论文使用 GPT-4o 作为判分模型。
- 成本指标：论文表格中的 token 主要统计 traversal 过程中 LLM 消耗的平均 token 数。
- 对比目标：比较无记忆查询、记忆后的相同查询、相似查询、不同查询在准确率和 token 成本上的变化。

论文报告的趋势是：ReMindRAG 在多跳 QA 中可以保持较高准确率，并且随着记忆轮次增加，相似查询和后续查询的 token 消耗下降。

需要说明的是，本次复现不是完整复现论文所有数据集和所有 baselines，而是聚焦 HotpotQA 的小批量复现，用于验证代码流程、记忆机制和成本变化趋势。

## 3. 本次复现范围

本次复现范围为 HotpotQA index `1..30`。

复现了以下几组实验：

| 运行 | 问题类型 | 含义 |
| --- | --- | --- |
| 记忆版 `origin` | 原始问题 | 构图并回答原始 Hotpot 问题，同时写入记忆 |
| 记忆版 `similar` | 相似改写问题 | 复用 origin 阶段构建的图和记忆，不重新构图 |
| 记忆版 `different` | 不同改写问题 | 复用 origin 阶段构建的图和记忆，不重新构图 |
| 无记忆版 `similar` | 相似改写问题 | 不复用记忆，每个样本重新构图并回答 |
| 无记忆版 `different` | 不同改写问题 | 不复用记忆，每个样本重新构图并回答 |

本次没有完成的内容：

- 未复现 DeepSeek-V3 设置。
- 未复现 LooGLE 完整实验，只完成过流程烟测。
- 未复现论文中所有 baselines。
- 记忆版 `different index 15` 多次出现图搜索循环，未生成最终 `input_different.json`，因此记忆版 `different` 按 `29/30` 已完成样本统计。

## 4. 实验环境与关键配置

实验仓库：

```text
D:\codes2026\NLP\hw2\kilgrims-ReMindRAG
```

主要配置：

| 配置项 | 本次复现设置 |
| --- | --- |
| Backbone | `gpt-4o-mini` |
| Judge | `gpt-4o-2024-11-20` |
| Embedding | `nomic-ai/nomic-embed-text-v2-moe` |
| `parallel` | `1` |
| `strong_connection_threshold` | `0.5` |
| 记忆版运行名 | `repro_hotpot_batch_paperjudge_20260528` |
| 无记忆基线运行名 | `repro_hotpot_batch_nomemory_paperjudge_20260528` |

判分和 token 统计口径：

- 正确性读取结果 JSON 中的 `check_response`。
- 仅 `check_response == "True"` 计为正确。
- Token 读取 `usage.construction.total_tokens`、`usage.query_and_grade.total_tokens` 和 `usage.total.total_tokens`。
- 记忆版 `similar/different` 复用已构建图，因此对应 Construction Tokens 为 `0`。

## 5. 复现流程

复现流程与论文方法保持一致，但缩小了样本规模：

1. 对 HotpotQA 原始问题运行 `origin`。
2. 在 `origin` 阶段完成 chunking、实体/关系抽取、异构图构建、图遍历问答和记忆写入。
3. 对相似改写问题运行 `similar`，复用图与记忆，验证相似查询重放效果。
4. 对不同改写问题运行 `different`，复用图与记忆，验证记忆对相关但不同查询的泛化效果。
5. 使用无记忆基线分别运行 `similar` 和 `different`，作为成本和准确率对比。

## 6. 总体实验结果

下表汇总 HotpotQA index `1..30` 的当前落盘结果。

| 实验 | 问题类型 | 完成进度 | 正确率 | 错误 index | 缺失 index | Construction Tokens | Query+Judge Tokens | Total Tokens |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 记忆版 | origin | 30/30 | 23/30 | 2, 13, 14, 21, 22, 23, 26 | 无 | 515,856 | 1,098,438 | 1,614,294 |
| 记忆版 | similar | 30/30 | 21/30 | 2, 10, 13, 14, 19, 21, 22, 23, 26 | 无 | 0 | 624,649 | 624,649 |
| 记忆版 | different | 29/30 | 23/29 | 2, 7, 9, 21, 22, 25 | 15 | 0 | 385,304 | 385,304 |
| 无记忆版 | similar | 30/30 | 17/30 | 2, 3, 5, 6, 10, 13, 14, 15, 19, 21, 22, 23, 26 | 无 | 499,940 | 516,343 | 1,016,283 |
| 无记忆版 | different | 30/30 | 23/30 | 2, 7, 15, 21, 22, 25, 27 | 无 | 0 | 1,596,177 | 1,596,177 |

## 7. 与无记忆基线的对比

### 7.1 Similar 查询

| 指标 | 记忆版 | 无记忆版 | 对比 |
| --- | ---: | ---: | ---: |
| 完成进度 | 30/30 | 30/30 | - |
| 正确率 | 21/30 | 17/30 | 记忆版 +4 |
| Query+Judge Tokens | 624,649 | 516,343 | 记忆版多 108,306 |
| Total Tokens | 624,649 | 1,016,283 | 记忆版少 391,634 |
| Total Token 节省比例 | - | - | 38.54% |

Similar 结果说明：

- 记忆版正确率高于无记忆版，说明记忆路径对相似改写问题确实有帮助。
- 如果只看 Query+Judge Tokens，记忆版反而更高；但无记忆版需要为每个样本重新构图，因此 Total Tokens 明显更高。
- 按 Total Tokens 统计，记忆版节省 `391,634` tokens，节省比例约 `38.54%`。

这与原论文的总体结论部分一致：记忆机制可以在后续相似查询中降低总成本，并提升或保持效果。但本次小样本中，traversal/query 阶段 token 并没有稳定低于无记忆版，这一点和论文中平均 traversal token 下降的现象不完全一致。

### 7.2 Different 查询

由于记忆版 `different index 15` 未完成，完整 `1..30` 无法直接逐样本闭合比较。因此这里比较共同完成的 `29` 个样本。

| 指标 | 记忆版 | 无记忆版（排除 index 15） | 对比 |
| --- | ---: | ---: | ---: |
| 完成进度 | 29/29 | 29/29 | - |
| 正确率 | 23/29 | 23/29 | 持平 |
| Query+Judge Tokens | 385,304 | 1,508,597 | 记忆版少 1,123,293 |
| Total Token 节省比例 | - | - | 74.46% |

Different 结果说明：

- 在共同完成样本上，记忆版和无记忆版正确数持平。
- 记忆版 Query+Judge Tokens 显著更少，少消耗 `1,123,293` tokens。
- 需要注意，无记忆版 `different index 2` 单条消耗 `1,030,069` tokens，是总体节省比例很高的重要原因。

这与论文中“记忆可减少后续查询成本”的趋势一致。不过，由于本次样本量较小且存在极端 token outlier，因此不能把 `74.46%` 直接推广到完整 HotpotQA 结果。

## 8. 与原论文结果的关系

原论文中，ReMindRAG 在 HotpotQA/Multi-Hop QA 上报告了 GPT-4o-mini 设置下约 `74.22%` 的原始多跳问答准确率，并进一步比较了无记忆、相同查询、相似查询和不同查询在记忆轮次增加后的准确率与 traversal token 成本。

本次复现的对应关系如下：

| 对应项 | 原论文关注点 | 本次复现观察 |
| --- | --- | --- |
| 原始多跳问答 | 评估 KG traversal 能否完成多跳推理 | `origin 1..30` 正确率为 `23/30`，约 `76.67%` |
| 相似查询记忆复用 | 检查记忆对改写问题是否有效 | `similar` 记忆版 `21/30`，无记忆版 `17/30` |
| 不同查询记忆泛化 | 检查记忆对相关但不同问题是否仍有帮助 | 共同完成的 `different` 29 个样本中，记忆版与无记忆版均为 `23/29` |
| 成本下降 | 检查记忆是否减少后续检索/遍历成本 | `similar` 按 Total Tokens 节省 `38.54%`；`different` 共同样本按 Query+Judge Tokens 节省 `74.46%` |

总体来看，本次复现支持论文的两个主要趋势：

1. 图遍历式 RAG 在 HotpotQA 多跳问题上可以取得可用准确率。
2. 记忆复用在后续查询中能够减少总 token 成本，尤其在 `different` 任务中减少了长路径搜索带来的极端消耗。

同时，本次复现也观察到一些和论文整体平均结果不同的现象：

1. `similar` 中，记忆版 Query+Judge Tokens 高于无记忆版，但由于省去了重新构图，Total Tokens 仍更低。
2. `different` 的大幅节省受到无记忆版 `index 2` 极端 outlier 影响。
3. 记忆版 `different index 15` 出现图搜索循环，说明当前实现缺少更强的停止条件或异常保护。

## 9. 异常样本分析

记忆版 `different index 15` 未生成结果文件：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/input_different.json
```

最新异常日志：

```text
eval/database/repro_hotpot_batch_paperjudge_20260528/15/log_2026-05-31_17-54-36.log
```

日志统计如下：

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

日志显示模型反复在 `anchor-3`、`anchor-10`、`Brown County`、`United States`、`Hiawatha` 等节点之间选择下一跳，并持续判断信息不足。日志中没有 API 报错，因此更可能是图搜索循环或停止条件不足导致的无法收敛。

这个异常说明：ReMindRAG 的 LLM-guided traversal 虽然可以减少很多查询的成本，但在某些样本上，如果图中缺少关键答案信息，或者 LLM 不断选择已访问但看似相关的节点，就可能产生很长的无效搜索路径。

## 10. 局限性

本次复现有以下局限：

1. 样本规模只有 HotpotQA index `1..30`，不是论文完整实验规模。
2. 没有复现 DeepSeek-V3，也没有复现其他 baseline 方法。
3. 成本统计口径与论文不完全一致：本次记录同时统计 Construction、Query+Judge、Total，而论文主要关注 traversal token。
4. 使用了 `gpt-4o-2024-11-20` 作为 judge，和论文中 GPT-4o judge 的具体版本可能不完全一致。
5. `different index 15` 未完成，因此 `different` 的完整 30 条记忆版结果存在一个异常缺口。

## 11. 结论

本次 HotpotQA index `1..30` 小批量复现基本验证了 ReMindRAG 的核心流程：文档切分、实体/关系抽取、异构图构建、LLM-guided traversal、路径记忆更新和后续查询复用。

实验结果显示：

- 原始问题 `origin` 的正确率为 `23/30`，说明图遍历式 RAG 能够处理一部分多跳问答。
- `similar` 中，记忆版正确率 `21/30`，高于无记忆版 `17/30`，并且 Total Tokens 少 `391,634`。
- `different` 中，在共同完成的 `29` 个样本上，记忆版与无记忆版正确数持平，但记忆版少消耗 `1,123,293` Query+Judge tokens。
- 记忆机制总体上降低了后续查询的总成本，尤其能缓解无记忆图遍历中的极端长搜索。
- 但当前实现也存在搜索循环风险，`different index 15` 就是一个典型未收敛样本。

因此，本次复现支持论文关于“记忆增强图遍历可以降低后续查询成本”的主要结论；但由于样本规模较小、存在异常样本和 token outlier，本实验结果更适合作为课程复现与代码验证，而不能直接等同于论文完整实验结果。

## 参考资料

- 原论文：ReMindRAG: Low-Cost LLM-Guided Knowledge Graph Traversal for Efficient RAG, arXiv: `2510.13193`
- 官方仓库：`kilgrims/ReMindRAG`
- 本次实验汇总：`eval/hotpot_experiment_summary_20260601.md`
