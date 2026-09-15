# 實作計畫：綜合度假村客戶智慧分析代理

本文件是規劃的第二層：**如何實現** [`ssot.md`](ssot.md)。它把 SSOT 的目標對到架構、工作流、階段交付與驗證，不重寫業務定義，也不拆成工單。

職涯意圖見 [`proposal.md`](proposal.md)。任務順序見 [`work_plan.md`](work_plan.md)。

若本文件與 SSOT 衝突，以 SSOT 為準，並先改 SSOT 決策紀錄再改實作。

本版問答為**單輪**；用詞歧義走 SSOT 預設 + `declare`，不新增 clarify 模式。

---

## 1. 從 SSOT 到做法

| SSOT 要證明的事 | 本計畫的做法 |
|---|---|
| LLM 不是數字／定義的權威 | 語意層 + 確定性指標先於代理；代理只編排 |
| 三本帳不得合成「消費」 | 分析模型分帳：錢包現金、IR 營收、可觀察非營收事件 |
| 資料權利看 `operating_model` | 不產生租戶 POS；政策層攔截租戶 GMV／插補 |
| 四種回答模式 + 原因碼 | 政策與驗證產出結構化輸出，不只自由文本 |
| I1–I21 | 依 §4.3 覆蓋矩陣分層測；未覆蓋項須標明，不得默認全綠 |
| Q1–Q15 | 先有 **golden runner**，再評代理；另與 **naive-LLM baseline** 對照 |
| 套裝不雙計、不做總帳引擎 | 只建能支撐不變量與 Q15 的成分／負債／breakage |
| 單一代理 | 一個編排器、多個工具；無多代理，除非日後實驗證明有效 |
| 資料最小化、唯讀 SQL | 彙總優先；pre-flight 擋逐客進模型；禁止寫入 |

提案的 V1／V2／V3 時間盒保留，但順序改為：**語意與確定性路徑先於「會聊天的代理」**。否則無法分辨代理有沒有加值。

---

## 2. 假設（本層鎖定，非 SSOT 業務決策）

下列是實現選擇。行為不靠環境變數切換；見 `config/`（YAML／Python）。機密（API 金鑰）用 gitignore 的本地密鑰檔，不進版控。

| 項目 | 選擇 | 理由 |
|---|---|---|
| 語言 | Python | 分析、評測、資料產生同一語言 |
| 分析庫 | DuckDB 檔案庫，唯讀查詢 | 夠用、可重現、不是 EDW |
| 語意／政策 | 檢入的 YAML（定義、常數、原因碼、outlet 政策） | SSOT 的機器可讀投影 |
| 編排 | 單一 tool-calling 迴圈，薄封裝 | 避免框架變成產品 |
| 介面 | V1–V2 以 CLI 為準；V3 再加 HTTP。**本機薄 Explore UI**（Streamlit）可在 CLI 可跑後另開，不取代 CLI／API | 示範仍看系統行為；UI 是檢視與探索面，不是產品 |
| 檢索 | V1：核准文件分塊 + 關鍵詞／向量擇一簡單方案；V2 再評是否值得上向量 | 無衝突時定義以語意層為準；衝突則拒絕選邊 |
| LLM | OpenAI 相容 API，模型名寫在 config | 可換供應商；簡單題可走低成本路徑 |
| 測試 | pytest：資料不變量、指標金標、代理輸出契約 | 與原因碼對得上 |
| 等級時間語意 | 貢獻分解用**期末等級快照**（可重算核對） | 避免 as-of 複雜度；寫死以便 Q11 可測 |
| 來源市場／通路 | 本版**不做**為分析維度 | 變體軸以期間／等級／對抗措辭為主 |
| 等級命名 | Tier 1／2／3；**Tier 1＝入門、Tier 3＝最高＝VIP 同義** | SSOT D37 |
| 點數匯率（產生器） | 1 錢包現金單位＝1 點 | SSOT D36；非產品承諾 |
| Standalone 禮券 | 與套裝共用發行／核銷事件；不另開負債科目 | SSOT D34 |
| 租戶回報核銷件數 | 合成資料必產（僅件數） | SSOT D35；覆蓋 I18 |
| 高價值門檻數字 | 資料凍結後鎖定 | SSOT D38 |
| VIP 衝突文 | **必產**一篇，測 `DEFINITION_CONFLICT` | 覆蓋 Q8 衝突路徑，不留未測原因碼 |

不選：K8s、微服務、生產 IAM、多代理、精緻產品前端、租戶 POS 模擬。本機 Streamlit（Ask／Explore／SQL）不算精緻產品 UI。

---

## 3. 目標架構

代理不是權威。語意層與政策決定什麼為真、什麼可問；工具只在允許範圍內計算；驗證通過才輸出。

兩道閘：

1. **Pre-flight（查庫前）：** 範圍外、因果、PII／逐客、租戶 GMV／插補 → 不查庫、不把逐客資料送進模型。
2. **輸出驗證：** 模式、原因碼、禁止主張、數字↔evidence、不變量。

```text
                         ┌──────────────────┐
                         │  Semantic layer  │
                         │  (SSOT projection)│
                         └────────┬─────────┘
                                  │
User question → Pre-flight policy ┼── (scope, PII, causal,
                                  │    GMV/impute, operating_model)
                                  │
                    ┌─────────────┴─────────────┐
                    │   Planner / agent         │
                    └─────────────┬─────────────┘
                 ┌────────────────┼────────────────┐
                 ↓                ↓                ↓
            SQL (RO)         Python metrics        RAG
                 │                │                │
                 └────────────────┼────────────────┘
                                  ↓
                           Evidence pack
                                  ↓
                         Validation / invariants
                                  ↓
                    Answer | Declare | Downgrade | Refuse
                    + reason code + evidence
```

### 3.1 模組邊界

對應現有 `src/` 方向，名稱以 SSOT 為準（不要沿用提案的 `booking_revenue` 當主指標）。現有 `src/security/` 骨架併入 `policy/`（pre-flight）與 `validation/`（輸出護欄），不另做第三套真相。

| 模組 | 職責 | 不職責 |
|---|---|---|
| `semantic/` | 規範名詞、預設解釋、指標公式、同義詞對到實體 | 不存第二套業務真相；衝突時不「選邊贏」 |
| `policy/` | 回答模式、原因碼、資料邊界、PII、因果、範圍外；**pre-flight** | 不是 IAM |
| `data` 模型 + `scripts/` 產生器 | 前後一致的合成 IR；覆蓋 §4.3 已列的不變量 | 不是 PMS／POS／總帳；不默認 I1–I21 全綠 |
| `tools/sql/` | 唯讀、表／欄白名單、禁止 DDL/DML；預設彙總優先；逐客可識別欄不進預設白名單；結果 row cap | 不讓模型直接連原始檔；不作為實稱數字的首選來源 |
| `tools/analytics/` | 已命名指標與分解（活躍、支柱營收、禮券、可觀察零售／用餐、貢獻） | 不做因果估計、不插補 GMV |
| `tools/rag/` | 檢索核准文件當**資料** | 文件不能當系統指令；不得用文件覆寫語意層答案；來源互斥時 refuse（不得選邊） |
| `agent/` | 選工具、組答案草稿 | 不算數、不定義、不選邊衝突定義 |
| `validation/` | SQL 護欄、數字重算、主張對證據、不變量、模式／原因碼 | 不「用另一個 LLM 感覺對不對」當唯一關卡 |
| `eval/` | Q1–Q15 契約 → golden runner → 代理 vs naive-LLM baseline | 不預先寫死金額；行為門檻見 §10 |
| `api/` | V3 才出現 | V1 不需要 |
| `explore/`（或同等薄層） | 本機探索：`preview`／`summarize`／`aggregate` 參數化 SQL；Kaggle Data Explorer 式欄位摘要 | 不是 BI 產品；不算數權威；不把全表載入記憶體當預設路徑 |
| 本機 UI（Streamlit） | 三 Tab：Ask（`handle`）、Explore（上述 API）、SQL（`run_sql`） | 不另開 DuckDB-WASM；不開頁 rebuild；不預設全庫 profiling |

**數字路徑：** 實稱數字主張**預設**走命名指標；自由 SQL 可作探索／交叉核對。獨立重算不得等於「重跑模型剛寫的同一條 SQL」。

Planner 與 agent 可為同一迴圈裡的路由步驟（簡單確定性題走低成本／既有指標；不必每題大模型）。不是兩個自主代理。

### 3.2 輸出契約（實現 SSOT §12）

每次呼叫回傳同一結構。模式／原因碼／數字欄對契約**自動比對**；散文風格不評。

- `answer_text`
- `question_type`：`deterministic` / `analytical` / `knowledge` / `should_refuse`（對齊 SSOT §15；**由政策／題目契約判定**，不由模型語感）
- `response_mode`：`full` / `declare` / `downgrade` / `refuse`（頂層單一；Q5／Q7 的「附帶觀察／子集」寫在本文與下列欄位）
- `reason_codes[]`（非 `full` 必填；可多碼，如 Q5 的 `COVERAGE_GAP` + `DATA_UNAVAILABLE`）
- `definitions_used[]`
- `figures[]`：`{metric_id, period, dimensions, value, evidence_ref}`（實稱數字可重算；無數字題可空）
- `evidence[]`（查詢摘要、指標結果、文件引用）
- `coverage_gap`（降級或含 `COVERAGE_GAP` 時）
- `missing_for_full`（拒絕／降級時）

定義處理：

- **無衝突：** 語意層為準，核准文件可附引用。
- **核准來源互斥：** 不得選邊；`DEFINITION_CONFLICT` + `refuse`，直到 SSOT 更新。

### 3.3 本機 Explore UI（實現選擇，非 SSOT 產品介面）

目的：本機用瀏覽器問代理、看庫、做**資料彙總**（mean／count／sum 等），並跑簡單唯讀 SQL。對齊 Kaggle **Data Explorer** 的體驗（預覽 + **欄位級 metrics**），不是縮寫 glossary。

**原則：** 統計與彙總在 DuckDB **push-down**；UI 只收小結果。資料變大時，記憶體應隨**結果大小**成長，不隨全表線性成長。

```text
Streamlit（Ask | Explore | SQL）
        │
        ├─ Ask  → agent.handle（既有契約）
        ├─ SQL  → tools/sql.run_sql（明細 row cap）
        └─ Explore → explore service
                      preview | summarize | aggregate
                      ↓
                   DuckDB 唯讀（白名單）
```

| API | 用途 | Cap 語意 |
|---|---|---|
| `preview` | 明細／分頁／可選 sample | `preview_row_cap`（例如 100）；禁止預設全表下載 |
| `summarize` | 表／欄位摘要（型別、null%、unique、min／max／mean／std、分位數；類別 top-K） | 結果小；優先引擎 `SUMMARIZE` 或等效聚合；**不得**先 `LIMIT` 原始列再算 mean |
| `aggregate` | 1–2 維度 + count／sum／avg／min／max | 可全表掃描；回傳 `aggregate_result_cap`（top-N） |

與 `run_sql` 共用：唯讀連線、表／欄白名單、禁寫入。分開：自由 SQL 的明細 cap **不可**套在彙總掃描上。行為常數寫入 `config/app.yaml`（`explore.preview_rows`、`aggregate_result_cap`、`value_counts_top_k`、`default_sample_rows`、`allow_full_scan`）。小表可自動 full scan；大表預設 sample，full scan 須明示。

刻意不做：開頁整表 `.df()`、預設 ydata-profiling／PyGWalker（若日後加，只吃樣本或已聚合小結果）、第二條 WASM 查詢路徑、寫入 SQL、精緻 BI。

此面不擋 V2 評測、不取代 V3 HTTP；CLI 仍是行為準據。

---

## 4. 分析資料邊界（邏輯模型，不是 DDL）

Schema 從 SSOT 長出，**禁止**從提案第 6 節的 `bookings` 草稿複製。實作前更新過期 scaffold（見 §9）。

### 4.1 要有的東西

| 邏輯實體／概念 | 用途 |
|---|---|
| 會員 | `member_id` 主軸；等級＝Tier 1／2／3（Tier 1 入門、Tier 3 最高）；由錢包現金規則可重算；貢獻用期末快照 |
| 訪客／住房客人可區分 | 不必獨立主檔，但客戶數／訪客數／住房客數須可分開計（I9、Q4 負向） |
| Outlet 維度 | `pillar` + `operating_model`；租戶店為禮券核銷地點，不是 POS |
| 住房事實 | 間夜、淨房收（含套裝客房分攤連結）；取消／退款後淨額；`member_id` 可空 |
| 自營交易 | 僅 `self_op`；收入桶：`fb_self_op` / `retail_self_op` / `hotel_other`（含 IRD、breakage） |
| 錢包現金事件 | 付給 IR 的現金；**未識別亦可有**（不限住房）；忠誠與活躍只認這本帳 |
| 積分流水 | 累點／兌換（產生器 1:1）；兌換不進營收、不進錢包 |
| 禮券發行／核銷 | 核銷帶 outlet；**資金來源**：付費／comp／套裝成分；standalone 與套裝同一事件模型（D34）；租戶核銷≠營收≠活躍 |
| 租戶回報核銷件數 | 僅件數、無金額；聯名／租戶檔可觀測下界（D35、I18） |
| 套裝頭＋成分 | SSP／面額、負債 vs 自營認列、到期／breakage；只為 I11–I12 與 Q15 |
| 自營掛房帳／退房結清 | 代收路徑；營收歸 F&B；錢包現金結帳計一次（I21）；租戶仍不掛 |
| 活動＋接觸 | 觀察性；無隨機分派欄位可冒充實驗 |
| 核准文件 | 定義、企劃、一篇可測提示注入、**一篇 VIP≠Tier 3 衝突文**（必測 `DEFINITION_CONFLICT`） |

時間範圍至少兩個完整年。單一物業、單一貨幣。F&B 自營為主、零售租戶為主，兩邊都留少數另一種經營模式。

### 4.2 明確不要有的東西

- 租戶 POS／租戶 GMV 事實表
- 租戶掛房帳
- ADR／RevPAR 指標實作
- 外部忠誠帳本
- 博彩
- 用「消費」寬表把三本帳揉在一起給模型
- 來源市場／通路維度（本版）

會員身份預留未來外部會籍鍵，本版不填、不 join。

### 4.3 不變量覆蓋（概念層，非測試程式碼）

| 測法 | 典型 I | 最早階段 |
|---|---|---|
| 政策／輸出 | I1、I7、I16、I17、I19、I20 | M1（契約對表）→ M4+（行為測） |
| 資料產生器 | I2、I5、I11、I12、I13、I14、I15、I18、I21 | M2 |
| 指標／golden | I3、I4、I6、I8、I9、I10 | M3–M5 |

完整逐條對照表在工作計畫 I1（catalog）維護；本層只鎖定「不得默認全綠」。

---

## 5. 工作流

工作流是架構切片，不是 sprint backlog。

```text
SSOT
  → 語意契約 + 政策碼
  → 邏輯 schema + 產生器
  → 資料不變量測試
  → 確定性指標／golden runner（Q 金標）
  → 單一代理 + 工具
  → 驗證 + 證據包
  → 代理評測 vs naive-LLM baseline
  → V3 包裝、文件、示範
```

本機 Explore UI（工作流 H）可在 CLI 可跑（M4）後並行，不插入上述評測關鍵路徑。

| 工作流 | 內容 | 主要 SSOT 對應 |
|---|---|---|
| A. 語意與政策 | YAML：實體、預設解釋、指標、原因碼、覆蓋 catalog | §7–11、D27–D30 |
| B. 合成世界 | 產生器 + DuckDB；無租戶 POS | §3–4、§8 |
| C. 確定性指標 | 支柱營收、活躍、禮券、**可觀察零售／用餐／購物**、貢獻分解 | Q1–Q5、Q10–Q12、Q14–Q15 |
| D. 代理與工具 | SQL／指標／RAG；路由；pre-flight | §6、§10 |
| E. 驗證 | 護欄、數字核對、模式／原因碼、PII | §10–13 |
| F. 評測 | Q1–Q15 → 變體擴題；golden + naive-LLM 對照 | §15–16、提案 §11–13 |
| G. 包裝 | API、Docker、CI、成本／延遲、writeup、示範 | 提案 V3 |
| H. 本機探索面 | Streamlit + explore service（preview／summarize／aggregate）；Ask 接既有代理 | 非 SSOT；見 §3.3 |

C 必須在 D 的正式評測之前可跑。D 的 V1 只為證明端到端，不是評測終點。H 可在 M4 之後開始，**不得**擋 M5 評測。

---

## 6. 階段與交付

對齊提案週期：V1 約 2–3 週，V2 約 2–3 週，V3 約 1–2 週。週數是盒子，不是承諾工時。

### 6.1 V1 — 可運作、且路徑正確

**目標：** 沒有 LLM 也能算對一批題；有 LLM 能走完「問題 → 工具 → 證據 → 結構化輸出」。

必須交付：

- 語意／政策 YAML 初版（含預設：「客戶」＝會員、「酒店營收」＝支柱合計、F&B／Retail 營收＝自營；定義衝突兩支規則）
- 合成庫可載入；資料層不變量抽樣（至少：無租戶 POS、IRD 不在 F&B 事實、禮券租戶核銷不進營收事實）
- 確定性 **golden runner**：至少 Q1、Q3、Q4、Q5（可觀察零售子集）、Q8（語意／文件）、Q10、Q14
- 單一代理 CLI：能跑上述確定性題 + **Q5 降級（含可觀察子集數字與缺口聲明）** + 一題拒絕（Q7 或 Q6）
- 唯讀 SQL 護欄（禁寫入）；pre-flight 擋 PII／因果／GMV 插補

刻意不做：50–100 題、完整數字驗證器、Docker、API、多代理、向量庫打磨、本機 Explore UI（可於 M4 後另開，見 §3.3／工作流 H）。

**完成定義：** 同一指令可重建資料並跑通 V1 題；輸出含 `response_mode`、原因碼與（有數字時）`figures[]`；Q5 為真降級而非空拒絕；Q6／Q7 不出現因果或插補數字。

### 6.2 V2 — 可靠到可被認真看待

**目標：** Q1–Q15 契約可測；代理對上 golden runner；失敗可寫清楚。

必須交付：

- 指標金標（由 golden runner 從凍結資料算出，再寫入 `eval/`）
- Q1–Q15 全覆蓋；另收 RevPAR 為 `OUT_OF_SCOPE`
- VIP 衝突文：**必產**；Q8 路徑必須測到 `DEFINITION_CONFLICT`
- 分析題 Q11／Q12：解釋不引入新數字
- 驗證：數字重算、證據、PII、提示注入文件
- 不變量測試對資料與輸出（對齊 §4.3）
- **naive-LLM baseline**：少工具的 RAG／LLM vs 本系統；量測不得預填
- 失敗分析：錯在語意、SQL、政策還是生成

**完成定義（行為門檻先登記，與資料無關）：**

- Q1–Q15 的 `response_mode`／原因碼對契約 = **100%**
- 禁止主張字串出現 = **0**
- 數字題與 golden runner 一致 = **100%**
- Q6／Q7 無插補、無因果數字

**首次量測後才校準（寫進評測文件，禁止事先填表）：** 有依據程度、解釋品質、相對 naive-LLM 的差距、延遲／成本。

擴題：變體由模板化產生（換期間、換等級、對抗措辭），金標一律由 runner 自動產出。目標約 50–100；時間不足時可接受退讓為 Q1–Q15 全覆蓋 + 有限變體，並在失敗分析中寫明。

### 6.3 V3 — 偏生產打磨

**目標：** 別人能重現，面試能在數分鐘內看懂行為。

必須交付：

- HTTP API 包同一輸出契約
- Docker 一鍵起資料＋服務
- CI：不變量 + 金標 + 抽樣代理測（成本可控）
- 延遲／token 成本紀錄（含 model 名與 prompt 版本）
- 架構圖、評測摘要、1,500–2,000 字 writeup、2–5 分鐘示範（Q5 降級或 Q7 拒絕為必演）
- **可選：** 本機 Streamlit Explore（§3.3）；不列入 V3 完成必要條件

仍不做：K8s、IAM、精緻產品 UI（本機薄 Explore 除外，見 §2）。

---

## 7. 里程碑

| 里程碑 | 代表狀態 |
|---|---|
| M0 | SSOT 已鎖（已完成） |
| M1 | 語意／政策 YAML 能對上**政策可表達**的不變量與 Q 的模式／原因碼；覆蓋 catalog 齊 |
| M2 | 合成庫可重建；§4.3 資料列不變量綠燈；無租戶 GMV 事實 |
| M3 | golden runner 產出 V1 題金標（含 Q5 可觀察子集） |
| M4 | CLI 代理端到端含真降級與拒絕；pre-flight 生效 |
| M5 | Q1–Q15 + naive-LLM 對照 + 失敗分析 |
| M6 | API／Docker／CI／writeup／示範 |
| M4+／H | 本機 Explore UI（可選；不擋 M5） |

M3 未完成不做正式「代理準確率」結論。

---

## 8. 角色

作品集單人專案：作者兼領域、資料、代理、評測。

外部「讀者」是招聘主管與技術面試官，不是產品使用者。示範與 writeup 用他們聽得懂的話解釋：為什麼降級、為什麼不談因果、為什麼零售營收很小。

---

## 9. 風險、依賴、緩解

| 風險 | 依賴 | 緩解 |
|---|---|---|
| 套裝會計膨脹成總帳 | D32 | 只支援 Q15 與 I11–I12；不建模負房費等病態折扣 |
| 語意層與模型 SQL 各說各話 | 指標模組 | 實稱數字預設走命名指標；自由 SQL 不作獨立重算來源 |
| 合成資料意外含租戶 POS | 產生器 | 測試：leased outlet 不得出現在自營事實 |
| RAG 定義蓋過／與語意層互斥 | 政策 | 無衝突：語意層為準、文件可引用；互斥：`DEFINITION_CONFLICT` + refuse，不得選邊 |
| 先評代理、沒有 golden | M3 | V2 評測入口檢查金標存在 |
| 評測燒 token | config 路由 | 確定性題走 runner；CI 只抽樣需 LLM 的題 |
| LLM 輸出 flaky | 評測設定 | temperature／seed 或 N 次多數；結果紀錄寫明 |
| prompt 未版本化 | 釋出產物 | 評測摘要含 model 名 + prompt 版本 |
| 50–100 題時間盒過滿 | 變體模板 | 模板化 + runner 金標；可退讓並寫明 |
| 把租戶 GMV 做成權限問題 | D29 | 政策只發 `DATA_UNAVAILABLE`／`COVERAGE_GAP` |
| 過期 scaffold 誤導實作 | 本文件 §4 | 實作前更新：`data/README.md`、`src/README.md`（去 `booking_revenue`）、根 `README.md`（語意在 V1）、`tests/README.md`、`eval/README.md` |
| Explore 用 pandas 全表載入或「先 LIMIT 再 mean」 | §3.3 | 彙總走引擎端；明細 cap 與彙總 result cap 分開 |
| 把本機 UI 當成正式產品面／擋評測 | 工作流 H | 不擋 M5；CLI／契約仍是準據 |

---

## 10. 驗證、釋出、治理

### 驗證

三層，對應 SSOT「能算的算、不能算的拒絕」：

1. **資料：** 不變量（無租戶 POS、現金守恆抽樣、IRD 分桶、核銷≠活躍、掛房帳路徑等 §4.3 資料列）
2. **指標：** 與凍結庫位元組級可重算的 golden
3. **系統：** 模式、原因碼、禁止主張、`figures[]`↔evidence、有依據、naive-LLM 對照

**先登記的行為門檻（與合成金額無關）：** 見 §6.2（模式／原因碼 100%、禁止主張 0、數字對 golden 100%）。

**首次完整 V2 跑完後才寫進評測文件：** 有依據程度、解釋品質、相對 naive-LLM 差距、延遲／成本。禁止事先填表。

模式／原因碼／數字欄必須能對 `eval/questions/` 契約**自動比對**，不得只靠人工判讀散文。

### 釋出

沒有對真實 IR 上線。釋出＝可重現產物：鎖定資料種子、config、**prompt 版本**、評測摘要、容器。示範走真實 CLI／API（可另開本機 Streamlit），不配旁白造假數字。

### 治理

- 改定義、範圍、原因碼：先改 SSOT 決策紀錄，再改 YAML。
- 改表、工具、模型、本機 Explore UI：只改本層與工作計畫，不准倒寫 SSOT。
- 發現 7–8 節與 I1–I21 不一致：改不變量表去對齊 7–8 節，或先改 SSOT 再改表。
- 本層已定案對齊 SSOT D34–D38；其餘開放題僅剩 §18 高價值門檻數字與金標。定案時先改 SSOT，再改 YAML／產生器。

---

## 11. 明確不在本計畫內

- 工作計畫層的工單、日曆、逐檔修改清單
- 完整 DDL、欄位型別、產生器偽代碼
- 選定確切 LLM 型號或 embedding 套件版本（V1 開工時在 config 寫死即可）
- 多代理實驗（僅當 V2 失敗分析證明單代理編排是瓶頸）
- 多主張圖（`claims[]`）；本版頂層單一 `response_mode` 即可
- 澄清對話模式；本版單輪 + 預設聲明
- 精緻產品前端、瀏覽器內 OLAP、開頁全表 profiling

---

## 12. 下一層

工作計畫見 [`work_plan.md`](work_plan.md)。評測關鍵路徑仍是 I6；本機 Explore 任務為 **I8**。
