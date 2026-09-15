# 失敗分析（I6 / WP-605）

首次全量對照：`deterministic_agent` vs `naive_baseline`（offline simulator，`naive-offline-v1`）。  
結果摘要：`eval/results/agent_vs_naive_latest.json`。量測日期以該檔 `generated_at` 為準。

## 行為門檻（預先登記，未放寬）

| 門檻 | Agent | Naive |
|---|---|---|
| 模式／原因碼 = 100%（Q1–Q15） | 通過 | 未通過（約 40%） |
| 禁止主張 = 0 | 通過 | 未通過（多題） |
| 數字 vs golden = 100% | 通過 | 未通過（約 20%） |
| Q8 `DEFINITION_CONFLICT` | 通過 | 未通過（選邊） |

## 按失敗類別

### 語意（semantic）

- **觀察到（naive）：** Q9 把高價值等同 VIP；Q8 衝突時選邊；Q14 把核銷當活躍；Q15 把租戶套裝成分計入支柱營收。
- **Agent：** 本輪 Q1–Q15 無語意門檻失敗（定義與聲明路徑對 golden）。

### SQL／指標（SQL / metrics）

- **觀察到（naive）：** 不呼叫命名指標，數字由雜湊發明 → Q1–Q5／Q10–Q12／Q14–Q15 figures 幾乎全錯。
- **Agent：** figures 與 golden runner 一致；未發現 SQL 白名單繞過（本輪評測路徑不走自由 SQL）。

### 政策（policy / preflight）

- **觀察到（naive）：** 跳過 preflight → Q6 估計、Q7 因果、Q13 PII、RevPAR 計算皆輸出「完整作答」。
- **Agent：** 拒絕／降級模式與原因碼對契約 100%；未出現 `ACCESS_RESTRICTED`。

### 生成（generation）

- **觀察到（naive）：** 流利中文＋假數字；Q5 寫成「商場 GMV」；Q7 肯定「造成營收增加」。
- **Agent：** 本輪確定性路由，不依賴 LLM 生成；故「幻覺數字」類失敗未在 agent 路徑出現。
- **聲明：** 若日後 deterministic_first=false 接上 LLM，生成類失敗須另開一輪評測，不得回推放寬本表行為門檻。

## 相對差距（實測，非預填）

- Agent `pass_all_behavioural` = true；naive = false。
- 延遲中位數（本機）：agent ≈ 139ms；naive offline ≈ 4ms。
- Token：offline naive = 0；live LLM naive 未跑（無強制 secrets）。

## 變體題庫（WP-603）

- `eval/questions/variants.yaml` + `eval/goldens/variant_goldens.json`
- 本輪變體數 **58**（≥50 目標）；含換等級、換期、對抗措辭。未擴到 100：時間盒內以全覆蓋＋有限變體為準（工作計畫允許退讓並寫明）。
