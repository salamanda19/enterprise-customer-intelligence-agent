# 工作計畫：綜合度假村客戶智慧分析代理

本文件是規劃的第三層：**具體做什麼、依什麼順序、做到什麼算完**。

- 業務真相：[`ssot.md`](ssot.md)
- 實現策略：[`implementation_plan.md`](implementation_plan.md)

本層不得改寫範圍或架構。若實作發現衝突，先停、提案改上層文件，再改任務。

單人專案：下列 **Owner 皆為作者**。讀者是未來的自己與面試官，不是產品使用者。

---

## 1. 用法

- 狀態：`pending` → `in_progress` → `done`／`blocked`
- 優先級：`P0` 擋住 V1；`P1` 擋住 V2；`P2` 為 V3
- 完成定義（DoD）寫在任務上；里程碑 DoD 寫在迭代末
- 金標金額不手填：由 **golden runner** 對凍結庫產出
- **禁止**在 M3 完成前把「代理準確率」當進度
- 行為門檻（模式／原因碼／禁止主張）先對 SSOT 契約登記；生成性指標首測後才寫

已完成（M0）：SSOT、實作計畫、本工作計畫。  
**I1：** WP-101–107 完成。  
**I2：** WP-201–206 完成。  
**I3：** WP-301–305 完成。  
**I4／V1：** WP-401–407 完成（CLI 代理、pre-flight、SQL 護欄、確定性路由；預設不呼叫 LLM）。  
**I5：** WP-501–507 完成（Q2／Q11／Q12／Q15 指標；Q1–Q15＋RevPAR 全題金標；figures 驗證器；無金標拒跑代理評測）。  
**I6：** WP-601–606 完成（代理評測器、offline naive baseline、58 變體金標、延遲摘要、失敗分析與生成性目標回填）。  
**I7／V3：** WP-701–707 完成（FastAPI、Docker Compose、CI、meta 延遲欄位、架構圖、writeup、Q5／Q7 示範）。下一刀可選 **I8（WP-801+）**。  
**I8（本機 Explore UI）：** 可在 I4 後並行；**不擋** I6／I7。尚未開工。

---

## 2. 迭代對照

對齊實作計畫 V1／V2／V3 與 M1–M6。週數沿用提案時間盒，是上限不是承諾。

| 迭代 | 里程碑 | 約當 | 目標 |
|---|---|---|---|
| I1 | M1 | V1 前段 | 語意／政策 YAML + 題目契約（無金額）+ 覆蓋 catalog |
| I2 | M2 | V1 中段 | 可重建合成庫 + 資料不變量 |
| I3 | M3 | V1 中段 | golden runner + V1 題金標（**含 Q5 可觀察子集**） |
| I4 | M4 | V1 完成 | CLI 代理；真降級與拒絕；pre-flight |
| I5 | M5a | V2 前段 | 其餘指標、Q1–Q15 金標、驗證器 |
| I6 | M5b | V2 完成 | 代理評測 vs naive-LLM、失敗分析、題庫擴充 |
| I7 | M6 | V3 | API、Docker、CI、writeup、示範 |
| I8 | M4+／H | 可選；不擋 V2 | 本機 Streamlit：Ask／Explore／SQL；引擎端彙總 |

依賴鏈：**I1 → I2 → I3 → I4**。I5 可與 I4 尾部重疊（指標可先寫、代理後接），但 **I6 不得在 I5／Q1–Q15 全題金標齊備前開始正式評測**（僅有 I3 的 V1 子集金標不夠）。I7 不得在 I6 失敗分析前當「專案完成」。**I8 依賴 I4**（`handle`、`run_sql`、凍結庫），可與 I5–I7 並行，完成與否不影響 V2 行為門檻。

第一個有意義的程式產出是 I1–I3，**不是聊天迴圈**。

---

## 3. 工作分解

### I1 — 語意與政策（M1）P0

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-101 | 建立 Python 套件骨架：`pyproject.toml`、`src/` 空模組、pytest、密鑰 gitignore | — | `pytest` 可跑（可先無測試）；`src/semantic`、`policy`、`tools`、`agent`、`validation` 目錄存在 |
| WP-102 | `config/app.yaml`：路徑、DuckDB、模型名、路由（確定性優先）；`config/secrets.example.yaml` | WP-101 | 行為只從 YAML 讀；範例無真金鑰 |
| WP-103 | 語意 YAML：實體同義詞（客戶→member；VIP→Tier 3）、預設解釋、指標名稱、常數 | WP-102 | 「客戶」「酒店營收」「F&B／Retail 營收」有預設；活躍＝90 天；等級＝Tier 1／2／3（**Tier 1 入門、Tier 3 最高＝VIP**）；產生器點數 1:1；**高價值門檻數字此階段可留 placeholder**，I2 凍結後鎖定（D38） |
| WP-104 | 政策 YAML：四種回答模式、原因碼（無 `ACCESS_RESTRICTED`）、定義衝突兩支規則、範圍外關鍵詞、禁止主張模式 | WP-103 | Q2／Q4／Q5／Q6／Q7／Q13／RevPAR 能對到模式＋原因碼；衝突路徑＝`DEFINITION_CONFLICT`+refuse（不得選邊） |
| WP-105 | 將 SSOT Q1–Q15 ＋ RevPAR 題寫入 `eval/questions/`（契約欄：類型、模式、原因碼、准用資料、禁止主張） | WP-104 | 無 `expected_amount`；與 SSOT §15 一致（含 Tier 2 題幹）；`question_type` 由契約寫死 |
| WP-106 | 不變量目錄 `tests/invariants/catalog.yaml`（I1–I21：檢查意圖、測法、最早階段、覆蓋狀態） | WP-103 | 對齊實作計畫 §4.3；I18 標 M2 資料覆蓋（D35） |
| WP-107 | 重寫過期 scaffold README：`data/`、`src/`（去 `booking_revenue`）、根 README（語意在 V1）、`tests/`、`eval/` | WP-103 | 不再出現提案 `bookings`／`booking_revenue` 主軸；與實作計畫一致 |

**I1 完成：** YAML 可載入；等級名與點數匯率已鎖；高價值門檻可暫緩；題目契約與 I 目錄齊；scaffold 與第二層一致。尚未有資料庫。

已鎖常數（SSOT D36–D37）：Tier 1／2／3（Tier 1＝入門；Tier 3＝VIP 同義＝最高）；產生器 1 現金單位＝1 點（非產品匯率）；貢獻分解用期末等級快照。高價值門檻見 WP-206。

---

### I2 — 合成世界（M2）P0

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-201 | DuckDB 實體 schema（表／鍵／收入桶），對齊邏輯模型 | I1 | 有 DDL 或建表腳本；**無**租戶 POS 表；能表達 §4.1 概念（資金來源、掛房帳、breakage、取消／退款、未識別錢包、租戶回報件數） |
| WP-202 | 產生器：會員（Tier 1／2／3）、outlet、住房、自營交易（含 IRD／breakage）、錢包現金（含未識別）、積分（1:1）、禮券（付費 standalone＝同一事件模型／comp／套裝）、租戶回報核銷件數、最小套裝、自營掛房帳、活動接觸 | WP-201 | 種子可重現；≥2 完整年；`member_id` 可空；訪客／住房客／會員可分開計；件數無金額（D35） |
| WP-203 | `scripts/` 一鍵重建庫檔 | WP-202 | 文件寫明一條命令 |
| WP-204 | 資料不變量測試 | WP-203 | 至少綠：leased outlet 不在自營事實；IRD 不在 `fb_self_op`；租戶禮券核銷不進 IR 營收事實；套裝樣本現金守恆；自營核銷≠第二次錢包；comp≠錢包／營收；掛房帳晚餐在 F&B；租戶回報件數存在且無 GMV 金額；無 GMV 事實表 |
| WP-205 | 核准文件：與語意一致的定義、一篇觀察性企劃、一篇提示注入、**一篇 VIP 衝突文（必產）** | WP-103 | 衝突文把 VIP 寫成≠Tier 3；可觸發 `DEFINITION_CONFLICT` |
| WP-206 | 凍結庫後鎖定高價值門檻：看 12 個月錢包現金分佈，選整數寫入語意 YAML，並回寫 SSOT 決策／§18 | WP-203 | 門檻可重現；Q9 定義仍成立；需要門檻的指標題方可跑數字金標 |

**I2 完成：** 凍結種子後庫可重建；WP-204 綠；catalog 中 M2 資料列（含 I18）標 covered；高價值門檻已鎖（WP-206）。此時仍無代理。

套裝範圍：只產生能支撐 I11–I12 與 Q15 的頭＋成分（含至少一筆租戶早餐／購物禮券套裝、一筆自營早餐套裝、一筆自營掛房帳晚餐）。不建模負房費。

---

### I3 — golden runner（M3）P0

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-301 | 指標函式：三支柱 IR 營收、酒店支柱合計 vs 淨房收、活躍會員、會員數、禮券發行／核銷、**可觀察零售**（自營零售 POS ∪ 購物禮券核銷） | I2 | 純 Python／SQL；不呼叫 LLM |
| WP-302 | Q14 指標：90 天僅租戶核銷、無錢包現金 → 非活躍 | WP-301 | 測試案例為否 |
| WP-303 | Q8 定義答：無衝突時讀語意 YAML（VIP＝Tier 3；可附文件引用）；**來源互斥時 refuse + `DEFINITION_CONFLICT`，不得選邊** | I1、WP-205 | 無衝突：VIP＝Tier 3、高價值≠VIP；衝突文行為測通過 |
| WP-304 | golden runner：輸入 Q id 或契約 → 結構化輸出（實作計畫 §3.2，含 `figures[]`） | WP-301、WP-303、WP-105 | Q1、Q3、Q4、**Q5（可觀察子集）**、Q8、Q10、Q14 可跑 |
| WP-305 | 對凍結庫產出 `eval/goldens/` 並設 pytest 比對 | WP-304 | 金標由命令生成；重跑 runner 位元組級一致（數字欄）；含 Q5 |

**I3 完成：** 上列 V1 題有金標（含 Q5）；無 LLM 也能「答對」。**此後才允許談代理正確性。**

---

### I4 — V1 代理 CLI（M4）P0

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-401 | 唯讀 SQL 工具：表／欄白名單；拒絕 DROP/DELETE/UPDATE/INSERT/ALTER；預設彙總；逐客欄不進預設白名單；row cap | I2 | 寫入嘗試失敗；查詢結果可進 evidence；無故不回傳逐客列 |
| WP-402 | **Pre-flight** 政策閘：範圍外、因果、PII、租戶 GMV／估計、插補（查庫前攔截） | WP-104 | Q6→`DATA_UNAVAILABLE` 拒絕；Q7→`CAUSAL_UNSUPPORTED`；Q13→`PII_MINIMIZATION`（不把逐客送進模型）；RevPAR→`OUT_OF_SCOPE`；**不**發 `ACCESS_RESTRICTED` |
| WP-403 | 指標工具給代理呼叫（包 WP-301；實稱數字預設走命名指標） | WP-304 | 數字題路徑以命名指標為主 |
| WP-404 | 簡易 RAG：分塊＋關鍵詞（或同等簡單方案） | WP-205 | 檢索當資料；注入句不進入系統指令；衝突則 refuse |
| WP-405 | 單一 agent 迴圈 + CLI | WP-401–404 | 輸出符合結構化契約（含 `figures[]`） |
| WP-406 | V1 行為測：Q5 **真降級**（可觀察數字 + `COVERAGE_GAP`＋`DATA_UNAVAILABLE`）；Q7 拒絕；確定性題模式／數字對金標 | WP-305、WP-405 | pytest 覆蓋；Q5 非空拒絕；Q6／Q7 答案無插補、無「造成營收」 |
| WP-407 | V1 冒煙腳本：重建資料 → runner → 抽 3 題 CLI | WP-406 | README 有重現步驟 |

**I4／V1 完成：** 與實作計畫 6.1 一致。不做 50–100 題、Docker、API。

---

### I5 — V2 指標與驗證（M5a）P1

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-501 | Q2 聲明後作答（預設酒店支柱合計） | WP-301 | 模式 `declare`＋`SEMANTIC_AMBIGUITY` |
| WP-502 | Q11 貢獻分解（期末等級）、Q12 可觀察用餐（不含 IRD） | WP-301 | 分解列可加總核對；用餐集合＝自營 F&B ∪ F&B 禮券 |
| WP-503 | Q15 套裝／房帳規則指標或查詢 | I2、WP-301 | 租戶早餐／購物禮券不進該支柱營收；掛房帳晚餐在 F&B |
| WP-504 | Q1–Q15 全數金標（補齊 V1 未覆蓋題；Q9 定義等） | WP-501–503、WP-305 | 全部由 runner／語意產生；Q5 已在 I3，此處確認不回歸 |
| WP-505 | 數字與證據驗證器：`figures[]` 須能在 evidence 重算；禁止解釋引入新數 | WP-504 | Q11／Q12 有負向測 |
| WP-506 | 輸出不變量：禁止主張字串、PII 清單、注入遵從 | WP-402、WP-205 | Q13 無逐客進模型亦無輸出；注入文件不能讓系統改行為 |
| WP-507 | 評測入口：無金標則拒絕跑「代理評測」 | WP-504 | 缺檔失敗訊息明確 |

---

### I6 — V2 評測與失敗分析（M5b）P1

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-601 | 代理評測器：對契約**自動比對**模式、原因碼、數字、禁止主張 | I4、I5 | Q1–Q15 出表；行為門檻＝100%／0／100%（見實作計畫 §6.2）；不靠人工判讀散文 |
| WP-602 | naive-LLM baseline：少工具 RAG／LLM，同一題庫 | WP-601 | 兩套結果並列；不得預填優勝；紀錄 model＋prompt 版本 |
| WP-603 | 由 Q1–Q15 **模板化**變體擴題（換期、換等級、對抗措辭）；金標 runner 自動產 | WP-105 | 不新增支柱／博彩／租戶 POS；目標約 50–100，不足則退讓並寫明 |
| WP-604 | 延遲與 token 粗量測（寫入結果摘要） | WP-601 | 有中位數即可；含 flaky 處理說明（seed／N 次） |
| WP-605 | `docs/evaluation/` 失敗分析：語意／SQL／政策／生成 | WP-601、WP-602 | 每類至少一例或聲明未觀察到 |
| WP-606 | 依首次全量結果回填**生成性**評測目標（有依據、解釋品質、相對 naive-LLM、延遲／成本） | WP-605 | **不得**回填或放寬已登記的行為門檻（模式／原因碼／禁止主張） |

**I6／V2 完成：** 實作計畫 6.2。若單代理編排被證明是準確度瓶頸，**先寫失敗分析再考慮**多代理；預設不做。`DEFINITION_CONFLICT` 必須已被 WP-205／WP-303 覆蓋。

---

### I7 — V3 包裝（M6）P2

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-701 | HTTP API，同一輸出契約 | I6 | 健康檢查＋一題 ask |
| WP-702 | Docker：資料＋服務 | WP-701 | README 一條 compose／run |
| WP-703 | CI：不變量＋金標；LLM 題抽樣或標記 manual | WP-506、WP-601 | PR 不燒全量 LLM |
| WP-704 | 成本／延遲日誌欄位穩定 | WP-604 | 示範可引用；含 model＋prompt 版本 |
| WP-705 | 架構圖（實作計畫 §3 落成 `docs/architecture/`） | — | 含 pre-flight、政策與證據，不只「使用者→LLM」 |
| WP-706 | 1,500–2,000 字 writeup | I6、WP-705 | 問題、語意、驗證、拒絕、取捨、失敗 |
| WP-707 | 2–5 分鐘示範腳本：必演 Q5 或 Q7 | WP-701 或 CLI | 真輸出，不旁白造數字 |

**I7／V3 完成：** 實作計畫 6.3。仍無 K8s、IAM、精緻產品 UI（本機薄 Explore 見 I8）。

---

### I8 — 本機 Explore UI（M4+／工作流 H）P2

對齊實作計畫 §3.3。不新增業務範圍；不取代 CLI／HTTP。

| ID | 任務 | 依賴 | DoD |
|---|---|---|---|
| WP-801 | `config/app.yaml` 增加 `explore`：preview_rows、aggregate_result_cap、value_counts_top_k、default_sample_rows、allow_full_scan | WP-102、I4 | 行為只從 YAML 讀；無環境變數開關 |
| WP-802 | Explore service：`preview`／`summarize`／`aggregate`；表／欄白名單；唯讀 DuckDB；彙總**不得**先截斷明細再算 mean | WP-401、WP-801 | 三 API 可單測；白名單外表／寫入失敗 |
| WP-803 | 欄位摘要：優先引擎 `SUMMARIZE`（或等效）；類別 top-K 用 `GROUP BY … LIMIT K` | WP-802 | 結果列數小；小表可 full scan、大表可 sample |
| WP-804 | Streamlit：Ask Tab 呼叫既有 `handle()` | WP-405、WP-801 | 能跑題號／自由文字；顯示 mode、原因碼、`figures` |
| WP-805 | Explore Tab：選表、COUNT(*)、preview、column metrics、1–2 維 group-by builder | WP-802、WP-803 | 預設不 `.df()` 全表；不開頁 rebuild／profiling |
| WP-806 | SQL Tab：接 `run_sql()` | WP-401 | 寫入被拒；明細仍受 row cap |
| WP-807 | README 啟動步驟；可選輕量測（白名單、cap、summarize ≠ limited-mean） | WP-804–806 | `streamlit run …` 有文件；測試不拉 UI e2e |

**I8 完成：** 三 Tab 可本機使用；Explore 走 push-down；與實作計畫 §3.3 刻意不做清單一致。不做 PyGWalker／ydata-profiling 預設、不做 WASM 第二路徑。

---

## 4. 優先級與建議週序

在 V1 時間盒內 strictly：I1 → I2 → I3 → I4。抽時間只准往前趕指標（WP-501 類），不准先做 API 或多代理。I8 不進 V1 關鍵路徑；I4 完成後可穿插，但不得擠掉 I6。

```text
週序（示意，可壓縮）
W1     I1  YAML／契約／骨架／scaffold
W1–W2  I2  schema／產生器／不變量
W2     I3  runner／金標（含 Q5）
W2–W3  I4  政策／SQL／CLI／V1 測
W4–W5  I5–I6  全題、naive-LLM、失敗分析
W6     I7  包裝與示範
       I8  可與 W4–W6 並行（不擋 I6）
```

並行限制：產生器未綠燈前不寫「自由 SQL 探索用」寬表。金標未產出前不擴大 LLM 評測。

---

## 5. 執行風險與阻擋

| 風險 | 擋哪 | 處理 |
|---|---|---|
| 一開始就做 chat | 全 V1 | 勾選 WP-101–305 未 done 則不開 WP-405 |
| 套裝做太大 | I2 | Q15 兩種套裝＋守恆測試即停 |
| 手填金標 | I3／I6 | 金標檔頭註明生成命令；手改 PR 拒收 |
| 租戶 POS 混進產生器 | I2 | WP-204 為合併門檻 |
| 語意與 SSOT 漂移 | I1 之後 | 改 YAML 前先改 SSOT 決策 |
| 定義衝突選邊 | I1／I4 | WP-104／WP-303 禁止「語意層必贏」；衝突＝refuse |
| Q5 做成空拒絕 | I3／I4 | WP-304／WP-406 必須有可觀察數字 |
| 評測燒錢 | I6／CI | 確定性題走 runner；CI 抽樣 |
| 放寬行為門檻 | I6 | WP-606 只回填生成性指標 |
| `ACCESS_RESTRICTED` 被加回來 | I4 | WP-402 測試禁止該碼 |
| 過期 scaffold 誤導 | I1 | WP-107 與 schema 同一迭代 |
| Explore 全表進記憶體／先 LIMIT 再平均 | I8 | WP-802／WP-803／WP-805 禁止該路徑 |
| 把 I8 當 V2 完成條件 | I6 | I8 完成與否不改行為門檻 |

阻擋協議：WP-204 或 WP-305 紅燈時，不把代理當進度；只修資料或指標。

---

## 6. 本層不包含

- 新的業務定義、新支柱、租戶 GMV 估計
- 完整欄位型別清單（屬 WP-201 產出，不在計畫正文展開）
- 每日 checklist、小時估算
- 選定 LLM 具體版號（WP-102 開工時寫進 `app.yaml` 即可）
- 再討論 D34–D37（已定案）；D38 規則已定（凍結後鎖），門檻數值見 WP-206
- 把本機 UI 升成 SSOT 正式產品介面（若要升，先改 SSOT）

---

## 7. 現在下一步

開始可選 **WP-801**（本機 Explore UI），或停在此處整理 PR。  
I7 重現：`python -m api.server`、`python scripts/demo.py`、`docker compose -f deploy/docker-compose.yml up --build`。
