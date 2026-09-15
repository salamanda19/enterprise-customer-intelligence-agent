# 生成性評測目標（I6 / WP-606）

**不得**回填或放寬已登記行為門檻（模式／原因碼 100%、禁止主張 0、數字對 golden 100%）。  
本檔只記錄首次全量跑完後的**生成性／對照**目標，依 `eval/results/agent_vs_naive_latest.json` 與 [`failure_analysis.md`](failure_analysis.md)。

## 已登記行為門檻（鎖定）

維持實作計畫 §6.2；本輪 agent 已達成，naive 未達成。後續迭代不得為了「追齊 naive 流暢度」而放寬。

## 首次量測後校準（本輪填入）

| 指標 | 本輪觀察 | 暫定目標（供後續） |
|---|---|---|
| 有依據程度 | Agent 答案含 `figures[]`／evidence／語意引用；naive 多為無依據發明 | Agent 維持 figures↔evidence 可重算 100%；若接 LLM，抽樣人工標註「有依據」≥ 設門檻前先累積 2 輪 |
| 解釋品質 | 未做人工 rubric（確定性路由為主） | 接 LLM 後再設 1–5 分量表；在有 N≥2 輪前不寫死及格線 |
| 相對 naive-LLM | Offline naive：模式／數字大幅落後 agent；行為門檻全過 vs 全不過 | 繼續並列報告；**不**預填「必須贏多少個百分點」 |
| 延遲 | Agent 中位約 100–200ms（本機、無 LLM）；naive offline ≪ 10ms | Agent P95 < 2s（本地 DuckDB 路徑）；LLM 路徑另記 |
| 成本 | Agent token = 0（本輪）；naive offline = 0 | 若開 LLM：評測摘要必須記 model + prompt_version + usage |

## Flaky 處理（WP-604）

- 確定性 agent：temperature 不適用；同一凍結庫應位元組級穩定（數字欄）。
- Optional naive LLM：`config/app.yaml` → `eval.llm_repeat_n`／`seed`；預設 N=1、temperature=0。CI 預設不跑 `--naive-llm`。

## 明確不做

- 不為抬高生成性分數而放寬拒絕／降級契約。
- 不把 Streamlit／Explore（I8）完成度算進本檔。
