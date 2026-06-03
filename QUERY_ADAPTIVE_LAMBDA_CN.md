# Query-adaptive Memory Replay Threshold 方法说明

## 背景

原始 ReMindRAG 在 memory replay 阶段使用 DFS 扩展知识图谱子图。扩展时会根据边权判断是否把相邻节点加入子图，判断阈值是固定的 `lambda`，论文默认值为 `0.55`。固定阈值的优点是实现简单、实验可控，但它对所有 query 使用同一检索强度，难以同时兼顾简单问题和复杂多跳问题。

本分支引入 Query-adaptive Memory Replay Threshold，核心目标是在不改变 ReMindRAG 主体流程的前提下，让每条 query 在 memory replay / DFS 子图扩展阶段使用自己的动态阈值 `lambda_q`。

## 改进点

固定阈值策略可以理解为：

```text
if edge_score > lambda:
    add neighbor to subgraph
```

本方法将其中的固定 `lambda` 替换为按 query 计算的 `lambda_q`：

```text
if edge_score > lambda_q:
    add neighbor to subgraph
```

动态阈值只影响 memory replay 阶段的 DFS 扩展条件，不改变数据加载、图构建、LLM 推理、答案生成和评估流程。默认情况下新功能关闭，baseline 仍然使用原始固定阈值逻辑。

## 动态阈值公式

本方法使用以下公式：

```text
lambda_q = lambda_0 + beta * sim(query, seed) - gamma * complexity(query)
```

然后进行范围裁剪：

```text
lambda_q = max(lambda_min, min(lambda_q, lambda_max))
```

默认参数如下：

```text
lambda_0    = 0.55
beta        = 0.10
gamma       = 0.08
lambda_min  = 0.35
lambda_max  = 0.75
```

其中：

- `lambda_0` 是原始固定阈值的基准值。
- `sim(query, seed)` 表示 query 与初始 seed entity 的相似度。
- `complexity(query)` 表示 query 的复杂度估计。
- `beta` 控制 query-seed 相似度对阈值的提升幅度。
- `gamma` 控制复杂 query 对阈值的降低幅度。

## 设计直觉

当 query 与 seed entity 相似度较高时，说明初始 seed 更可靠，可以适当提高阈值，让 DFS 扩展更保守，减少噪声子图。

当 query 更复杂、包含多跳推理需求时，固定高阈值可能过早截断有用路径。因此复杂度越高，`lambda_q` 会适当降低，使 memory replay 能探索更多潜在相关节点。

这个设计使检索行为更接近 query 的实际需求：

- 简单、明确的问题：阈值偏高，子图更紧凑。
- 复杂、多跳的问题：阈值偏低，子图覆盖更充分。

## Query Complexity 估计

当前实现不调用大模型，也不引入新的 embedding 模型，而是使用轻量规则估计复杂度，并把结果限制在 `[0, 1]`：

- query 越长，复杂度越高。
- 出现多跳关键词时复杂度提高。
- 出现多个实体样式的词组时复杂度提高。

多跳关键词包括：

```text
and, or, compare, between, same, difference, relationship,
first ... then, after, before, why, how, which ... more
```

这种规则化估计可解释、可复现，并且不会破坏原项目依赖。

## Query-seed 相似度

如果当前 memory replay 调用处可以拿到 query embedding 和 seed node embedding，则直接复用项目已有 embedding，并用 cosine similarity 计算 `sim(query, seed)`。

如果 embedding 获取失败，代码会退回默认值 `0.5`，保证实验流程仍然可运行。实现中没有额外引入新的 embedding 模型。

## 接入位置

动态阈值接入在 `ChromaDBManager.quick_query()` 中完成：

1. `PathFinder` 选出初始 seed entity。
2. `quick_query(query, seed_entity)` 为当前 query 和 seed 计算一次 `lambda_q`。
3. `strong_connection_dfs()` 在本轮 DFS 递归中复用同一个 `lambda_q`。
4. DFS 判断边是否扩展时，用 `lambda_q` 替代固定 `strong_connection_threshold`。

这样可以保证同一个 seed 出发的 memory replay 过程阈值一致，不会在递归过程中反复漂移。

## 实验日志

启用动态阈值后，每条 query/seed 的 replay 日志会记录：

```text
[AdaptiveLambda] query=... lambda=... complexity=... sim=... subgraph_size=...
```

字段含义：

- `query`：query 前 80 个字符。
- `lambda`：当前使用的动态阈值。
- `complexity`：规则估计得到的 query 复杂度。
- `sim`：query 与 seed entity 的相似度。
- `subgraph_size`：本次 DFS 得到的实体节点和 chunk 节点数量之和。

这些日志可用于比较 baseline 固定阈值和 adaptive lambda 的检索成本、子图大小和答案效果。

## 运行方式

baseline 不需要加新参数：

```shell
cd eval
python eval_LooGLE.py --title_index 0 --test_name baseline --data_type longdep_qa --question_type origin --model_name gpt-4o-mini
python eval_Hotpot.py --title_index 0 --test_name baseline --question_type origin --model_name gpt-4o-mini
```

adaptive lambda 实验需要显式开启：

```shell
cd eval
python eval_LooGLE.py --title_index 0 --test_name adaptive --data_type longdep_qa --question_type origin --model_name gpt-4o-mini --use_adaptive_lambda
python eval_Hotpot.py --title_index 0 --test_name adaptive --question_type origin --model_name gpt-4o-mini --use_adaptive_lambda
```

可选调参：

```shell
--lambda_0 0.55 --lambda_min 0.35 --lambda_max 0.75 --lambda_beta 0.10 --lambda_gamma 0.08
```

## 保持不变的部分

本方法只修改 memory replay / DFS 子图扩展阶段的阈值逻辑。以下流程保持不变：

- 数据加载。
- 知识图谱构建。
- seed entity 检索。
- LLM 推理和答案生成。
- memory update 奖惩逻辑。
- 原始固定阈值 baseline。

因此，只有在传入 `--use_adaptive_lambda` 或初始化 `ReMindRag(use_adaptive_lambda=True)` 时，动态阈值才会生效。
