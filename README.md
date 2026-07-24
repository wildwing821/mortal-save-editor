# Mortal Save Editor (活俠傳存檔修改工具)

專為遊戲《活俠傳》（Mortal Sound / Legend of Mortal）設計的輕量級、高可靠性存檔修改工具。

與一般的解包重組工具不同，本工具採用純二進位直寫（Binary Direct-Patching）機制，繞過全文解碼與序列化開銷，直接對 C# `BinaryWriter` 序列化產生的小端序（Little-Endian）數據區塊進行精準尋址與記憶體覆寫，大幅降低存檔損壞風險。

---

## 核心技術特色

* **零架構污染（Binary-Safe I/O）**：全過程維持 `bytes` 狀態，拒絕將二進位流轉為字串處理，徹底避免 Encoding/Decoding 導致的數據失真。
* **三層架構分離（Clean Architecture）**：
* **Entry (CLI)**：處理使用者互動、路徑尋址與 Guard Clause 邊界防禦。
* **Business Logic**：基於正則匹配（`re.DOTALL`）與長度前綴解析，執行二進位偏移量覆寫。
* **Infra**：封裝原子化檔案寫入（Temp-and-Replace Pattern），防止突發性中斷導致存檔損毀。


* **動態 Schema 映射**：採用 Pydantic V2 定義數據模型，自動調用反射機制建構提示選單。

---

## 架構設計與底層原理

C# 在寫入變數名稱與數值時，會在字串前方附加 **1-Byte 長度前綴**，後續緊跟 **4-Byte signed 32-bit integer (Little-Endian)**：

$$\text{[Length: 1B]} + \text{[Key String: UTF-8]} + \text{[Value: 4B Int32]}$$

本修改器透過精準定位匹配模式，將欲寫入之數值利用 `struct.pack('<i', value)` 打包後直接置換：

```
[原數據流]  ... | 0x05 | m o n e y | 0x10 0x27 0x00 0x00 | ...
                                 └─ Int32 (10000) ──┘
                                        ↓ [Binary Patch]
[新數據流]  ... | 0x05 | m o n e y | 0x3F 0x42 0x0F 0x00 | ...
                                 └─ Int32 (999999) ─┘

```

---

## 環境需求

* **Python** $\ge 3.9$
* **Pydantic** $\ge 2.0$

安裝依賴：

```bash
pip install pydantic

```

---

## 使用方式

1. 確保遊戲已關閉或處於主選單。
2. 執行腳本：

```bash
python mortal_editor.py

```

3. **步驟一**：輸入存檔編號（例如 `1` 或 `001`，對應 `Save_001.dat`）。
4. **步驟二**：系統將逐一詢問欲修改的屬性，輸入目標數值；若該項目不需修改，直接按 `Enter` 跳過即可。

---

## 預設存檔路徑

本工具會自動解析當前 Windows 使用者的家目錄：

```text
%USERPROFILE%\AppData\LocalLow\Obb Studio\Mortal\<SteamID>\Save_XXX.dat

```

> **注意**：若 Steam ID 與預設不符，可於 `get_target_save_path()` 函式中進行配置修正。

---

## 支援修改屬性列表

| 分類 | 欄位名稱 (Alias) | 說明 |
| --- | --- | --- |
| **基礎貨幣** | `money`, `mental`, `martial-point`, `contribution`, `fate` | 銀兩、心相、武學點、門派貢獻、天命點 |
| **生產點數** | `weapon`, `poison` | 打鐵點數、煉毒點數 |
| **門派經營** | `assets`, `fame`, `people`, `team` | 門派資產、門派名聲、門派人口、門派向心力 |
| **趙活核心** | `life`, `dexterity`, `stamina`, `m-fist`, `m-sword`, `m-projectile` | 體力、輕功、內力、拳掌、刀劍、暗器 |
| **戰鬥爆發** | `combat-attack-dice`, `combat-weapon-dice`, `combat-defence` | 爆發、暗器爆發、防禦 |
| **特質抗性** | `literacy`, `talking`, `poison-resistance`, `paralysis-resistance` | 學問、嘴力、抗毒、抗麻 |
| **心性涵養** | `behaviour`, `karma`, `disposition`, `training`, `internal` | 處世、道德、性情、修養、陰陽 |
| **三教素養** | `confucianism`, `taoism`, `buddhism` | 儒學、道學、佛學 |

---

## 免責聲明 (Disclaimer)

修飾存檔數據存在不可預測之風險。儘管本工具採用了原子寫入防禦機制，仍**強烈建議在執行修飾前手動備份原始 `.dat` 存檔檔案**。
