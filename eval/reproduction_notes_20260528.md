# ReMindRAG 复现实验记录 - 2026-05-28

## 环境

- Conda 环境：`ReMindRag`
- OpenAI API：`api_key.json` 的第 0 条配置，`https://api.openai.com/v1`
- 主模型 smoke test：`gpt-4o-mini`
- HotpotQA 论文对齐判分模型：`gpt-4o-2024-11-20`
- Embedding 模型缓存目录：`../model_cache`

注意：不要提交 `api_key.json`。这个文件在上游仓库中是 tracked 状态，但本地里面包含 API key。

## 代码修改

- `ReMindRag/llms/openai_api.py`
  - 增加了每个 agent 的 API 用量统计：请求次数、prompt tokens、completion tokens、总 tokens。
- `eval/eval_Hotpot.py` 与 `eval/start_Hotpot.py`
  - 增加显式的 `--do_update` 记忆写入开关。
  - 增加 backbone/judge 的 API 配置索引，以及 judge 模型参数。
  - 按题型分别保存 `input_origin.json`、`input_similar.json`、`input_different.json`。
  - 增加构图阶段与查询/判分阶段的 token 统计。
- `eval/eval_LooGLE.py` 与 `eval/start_LooGLE.py`
  - 增加 `--no_update`、`--max_questions`、backbone/judge API 索引、judge 模型、按题型输出与用量统计。
- `eval/summarize_hotpot_runs.py`
  - 用于汇总 Hotpot 输出，并计算两个实验之间的 query+judge token 差异。

## 已准备的数据

- 作者提供的改写数据已解压到 `eval/dataset_cache/LooGLE-rewrite-data`。
- HotpotQA 改写数据：
  - `eval/dataset_cache/Hotpot/hotpot_dev_distractor_similar.json`
  - `eval/dataset_cache/Hotpot/hotpot_dev_distractor_different.json`
- HotpotQA 原始 distractor 验证集已从 Hugging Face 镜像转换为官方脚本需要的格式：
  - `eval/dataset_cache/Hotpot/hotpot_dev_distractor_v1.json`

## Hotpot 最小论文对齐实验

记忆写入种子运行：

```powershell
conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 1 --parallel 1 --test_name repro_hotpot_micro_paperjudge_20260528 --question_type origin --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --do_update --strong_connection_threshold 0.5
```

结果：

- 正确率：`1/1`
- 构图阶段：`16,014` tokens
- 查询+判分阶段：`10,377` tokens
- 日志确认发生记忆写入：`Enhance 3 Edges, Punish 1`

记忆重放与无记忆查询阶段对比：

| 问题类型 | 记忆版正确率 | 无记忆版正确率 | 记忆版 Query+Judge Tokens | 无记忆版 Query+Judge Tokens | 节省 Tokens | 节省比例 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| similar | 1/1 | 1/1 | 2,614 | 8,772 | 6,158 | 70.20% |
| different | 1/1 | 1/1 | 2,697 | 4,605 | 1,908 | 41.43% |

汇总命令：

```powershell
python .\summarize_hotpot_runs.py repro_hotpot_micro_paperjudge_20260528 repro_hotpot_micro_nomemory_paperjudge_20260528 --question_type similar
python .\summarize_hotpot_runs.py repro_hotpot_micro_paperjudge_20260528 repro_hotpot_micro_nomemory_paperjudge_20260528 --question_type different
```

## LooGLE Shortdep 烟测

运行命令：

```powershell
conda run -n ReMindRag python .\start_LooGLE.py --start_index 7 --test_count 1 --parallel 1 --test_name repro_loogle_short_micro_mini_20260528 --data_type shortdep_qa --question_type origin --model_name gpt-4o-mini --judge_model gpt-4o-mini --max_questions 1 --strong_connection_threshold 0.5
```

结果：

- 标题：`Foreign Cattle Market`
- 正确率：`1/1`
- 构图阶段：`97,328` tokens
- 查询+判分阶段：`3,043` tokens
- 该标题的第 1 个问题不需要图遍历，日志显示 `Jumps: 0`。因此这次实验验证了长文构图流程，但不适合作为记忆重放种子。

## Hotpot 小批量实验：index 1..10

本轮把最小实验扩展到 HotpotQA 的 index `1..10`。实验仍使用：

- Backbone：`gpt-4o-mini`
- Judge：`gpt-4o-2024-11-20`
- 记忆阈值：`strong_connection_threshold=0.5`
- 并发数：`parallel=1`

记忆版运行名：

```text
repro_hotpot_batch_paperjudge_20260528
```

无记忆基线运行名：

```text
repro_hotpot_batch_nomemory_paperjudge_20260528
```

运行命令：

```powershell
conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 10 --parallel 1 --test_name repro_hotpot_batch_paperjudge_20260528 --question_type origin --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --do_update --strong_connection_threshold 0.5

conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 10 --parallel 1 --test_name repro_hotpot_batch_paperjudge_20260528 --question_type similar --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --strong_connection_threshold 0.5

conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 10 --parallel 1 --test_name repro_hotpot_batch_paperjudge_20260528 --question_type different --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --strong_connection_threshold 0.5

conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 10 --parallel 1 --test_name repro_hotpot_batch_nomemory_paperjudge_20260528 --question_type similar --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --strong_connection_threshold 0.5

conda run -n ReMindRag python .\start_Hotpot.py --start_index 1 --test_count 10 --parallel 1 --test_name repro_hotpot_batch_nomemory_paperjudge_20260528 --question_type different --model_name gpt-4o-mini --judge_model gpt-4o-2024-11-20 --strong_connection_threshold 0.5
```

总体结果：

| 运行 | 问题类型 | 正确率 | Query+Judge Tokens | Total Tokens |
| --- | --- | ---: | ---: | ---: |
| 记忆版 | origin | 9/10 | 241,160 | 422,972 |
| 记忆版 | similar | 8/10 | 143,619 | 143,619 |
| 记忆版 | different | 7/10 | 51,533 | 51,533 |
| 无记忆版 | similar | 5/10 | 150,044 | 314,021 |
| 无记忆版 | different | 8/10 | 1,152,270 | 1,152,270 |

记忆版与无记忆版的查询阶段对比：

| 问题类型 | 记忆版正确率 | 无记忆版正确率 | 记忆版 Query+Judge Tokens | 无记忆版 Query+Judge Tokens | 节省 Tokens | 节省比例 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| similar | 8/10 | 5/10 | 143,619 | 150,044 | 6,425 | 4.28% |
| different | 7/10 | 8/10 | 51,533 | 1,152,270 | 1,100,737 | 95.53% |

需要注意：

- `different` 的无记忆基线中，index `2` 单条消耗了 `1,030,069` query+judge tokens，是这组节省比例极高的主要原因。这说明无记忆图遍历在个别样本上可能出现很长的搜索路径或反复判定。
- `similar` 小批量中，记忆版正确率高于无记忆版，但 token 节省幅度较小。
- 这个结果是 10 条样本的小批量复现，不应直接等同于论文完整 97 条 Hotpot 结果。

汇总命令：

```powershell
python .\summarize_hotpot_runs.py repro_hotpot_batch_paperjudge_20260528 repro_hotpot_batch_nomemory_paperjudge_20260528 --question_type similar
python .\summarize_hotpot_runs.py repro_hotpot_batch_paperjudge_20260528 repro_hotpot_batch_nomemory_paperjudge_20260528 --question_type different
```

## 后续实验建议

- Hotpot index `1..10` 已完成。若继续扩大，建议下一批跑 index `11..20`，确认成本和稳定性后再考虑完整 97 条设置。
- 对 LooGLE 先筛选会产生非零遍历步数的问题，再用 Similar 重放做成本对比。
- 若要复现 DeepSeek-v3 对照，需要先在 `api_key.json` 中增加第二条 DeepSeek-compatible API 配置，然后运行时使用 `--backbone_api_index 1 --judge_api_index 0`。

## Hotpot 扩展批量实验阶段记录：index 11..30

记录时间：`2026-05-31`

本阶段继续使用：

- Backbone：`gpt-4o-mini`
- Judge：`gpt-4o-2024-11-20`
- 记忆阈值：`strong_connection_threshold=0.5`
- 并发数：`parallel=1`
- 记忆版运行名：`repro_hotpot_batch_paperjudge_20260528`
- 无记忆基线运行名：`repro_hotpot_batch_nomemory_paperjudge_20260528`

截至当前，记忆版 `origin` 与 `similar` 已完成 index `11..30`，`different` 只完成部分样本。无记忆版 `similar/different` 的 index `11..30` 尚未开始。

阶段性结果：

| 运行 | 问题类型 | 完成进度 | 当前正确率 | 错误 index | Query+Judge Tokens | Total Tokens |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 记忆版 | origin | 20/20 | 14/20 | 13, 14, 21, 22, 23, 26 | 857,278 | 1,191,322 |
| 记忆版 | similar | 20/20 | 13/20 | 13, 14, 19, 21, 22, 23, 26 | 481,030 | 481,030 |
| 记忆版 | different | 8/20 | 7/8 | 25 | 164,064 | 164,064 |
| 无记忆版 | similar | 0/20 | - | - | 0 | 0 |
| 无记忆版 | different | 0/20 | - | - | 0 | 0 |

记忆版 `different` 已完成的 index：

```text
11, 12, 13, 14, 23, 24, 25, 26
```

记忆版 `different` 尚未完成的 index：

```text
15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 29, 30
```

需要注意：

- `different index 15` 曾多次出现长时间运行或中断，日志体积明显增大但未生成 `input_different.json`。为了避免它继续堵住整批任务，后续建议先补跑 `16..22` 与 `27..30`，最后单独跑 `15`。
- `start_Hotpot.py` 当前已经支持跳过已存在的 `input_{question_type}.json`，因此同一 `test_name` 下补跑不会覆盖已完成结果。
- 这一节是阶段性记录，不是 `11..30` 的最终完整对比；还需要补齐记忆版 `different` 和无记忆版基线后再写完整结论。
