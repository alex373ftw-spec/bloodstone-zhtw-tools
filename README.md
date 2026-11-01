# 007 Blood Stone 繁體化工具（James Bond 007: Blood Stone ZH-TW Tools）

把《007 血石》**簡體中文漢化版**的文本與字庫轉換為**繁體中文**的一組離線工具腳本。

本倉庫只包含**處理腳本**，不包含任何遊戲資源、漢化補丁或字庫文件——你需要自備一份已安裝簡體漢化的遊戲（詳見下方「前提條件」）。

> **來源說明**：本工具用於在 [Kanadeforever/BloodStone_CN](https://github.com/Kanadeforever/BloodStone_CN) 簡體漢化補丁的基礎上進行繁體化。簡體譯文、漢化技術實現與字庫格式研究均歸該項目及其作者所有，本倉庫僅提供簡→繁的轉換腳本。使用前請先安裝原版簡體漢化補丁，並遵守原項目的「免費分享、禁止商用、轉載保留來源」聲明。

## 背景

簡體漢化組的中文版由兩部分組成：

| 部分 | 位置 | 說明 |
|---|---|---|
| 文本 | `scripts/BSCNContents/loc/*.loc` | 86 個 OLTX 二進制容器，中文以 UTF-16LE 存放 |
| 字庫 | `scripts/BSCNContents/fonts/ui_font_cnx.dat` + `.bpr` | `.dat` 是 UV 索引表，`.bpr` 是 DXT1 位圖字庫 |

繁體化需要同時處理兩者：只改文本不改字庫會出現大量豆腐塊；只改字庫不改文本則沒有意義。

## 工具一覽

| 腳本 | 作用 |
|---|---|
| `tools/s2t_loc.py` | 把所有 `.loc` 內的簡體文本**就地**（字節長度不變）轉為繁體 |
| `tools/build_map2.py` | 從 `.loc` 語料統計「簡→繁」字級映射（語境多數投票），輸出 `s2t_map.pkl` |
| `tools/patch_glyphs.py` | 在 `.bpr` 字庫中**批量重繪**所有需要變形的漢字字形（717 字 × 3 字體塊） |
| `tools/blank_page2.py` | **清除 `.bpr` 隱藏第二頁**——疊影字的根源（見下） |
| `tools/dxt.py` | DXT5 解碼/編碼小工具（被其他腳本引用） |

## 關鍵格式發現（逆向筆記）

### `.loc`（OLTX 容器）
- 中文串為 UTF-16LE、以 `0x0000` 結尾，與二進制索引數據交錯。
- 腳本用「常用字命中率」區分真實譯文與二進制誤判，僅在繁體編碼後**字節數完全一致**時回寫，文件大小與全部偏移保持不變。

### `.bpr` 字庫
- 數據從 `0x9D` 開始，共 **3 個字體塊**，每塊 `2,752,512` 字節 = 一張 **2048×2688 DXT1** 紋理。
- `.dat` 中每條記錄 28 字節：`<I f f f f H H H H`（char_id, u1, v1, u2, v2, ox, w, h, oy）。
- 漢字格為 **36×32 像素 = 9×8 個 DXT1 塊**，格原點 `x0 = round(u1*2048)`、`y0 = round(v1*2048) + 8`，始終 4 對齊。
- 字形墨跡集中在格子的行 0–28、列 2–33（無上邊距、約 3px 下邊距）。

### ⚠️ 隱藏第二頁（疊影字真兇）
每個字體塊的後 655,360 字節其實是**第二張 2048×640 DXT1 隱藏頁**：一份完整的小號簡體字庫，**不被 `.dat` 引用**（UV 表硬編碼在加密 exe 裡）。

遊戲部分 UI（對話框、檔案菜單、字幕、名單）會**同時渲染主頁與第二頁**。原版兩頁都是簡體、完全重疊看不出來；一旦把主頁重繪成繁體，簡體第二頁就會以「淡色疊影字」的形式顯形。

**修復方法**：把三塊的第二頁全部清黑（`blank_page2.py`）。實測清黑後疊影完全消失、UI 無缺字——第二頁路徑只產生疊影層，不承載正常顯示。

## 使用步驟

> 以下路徑均以遊戲根目錄（含 `scripts/`）為準。**操作前務必備份原文件。**

```bash
pip install opencc-python-reimplemented numpy pillow

# 0. 備份字庫（腳本不替你備份）
cp scripts/BSCNContents/fonts/ui_font_cnx.bpr ui_font_cnx.bpr.orig

# 1. .loc 文本簡→繁（原地生成到新目錄後手動覆蓋回 loc/）
python tools/s2t_loc.py scripts/BSCNContents/loc out_loc

# 2. 從語料構建 簡→繁 字級映射
python tools/build_map2.py \
    --loc scripts/BSCNContents/loc \
    --dat scripts/BSCNContents/fonts/ui_font_cnx.dat \
    --out .

# 3. 批量重繪字庫字形（需 Windows + 微軟雅黑字體，可改 --font）
python tools/patch_glyphs.py \
    --pristine ui_font_cnx.bpr.orig \
    --dat scripts/BSCNContents/fonts/ui_font_cnx.dat \
    --bpr scripts/BSCNContents/fonts/ui_font_cnx.bpr \
    --font C:/Windows/Fonts/msyhbd.ttc

# 4. 清除隱藏第二頁，根除疊影字
python tools/blank_page2.py scripts/BSCNContents/fonts/ui_font_cnx.bpr
```

啟動遊戲驗證：登錄畫面「點擊登入」、主菜單、對話框、字幕均應為乾淨繁體、無疊影。

## 已知限制

- `patch_glyphs.py` 使用點陣量化（4 級灰度）重繪字形，風格與原字庫一致但非逐像素復刻。
- 繁體轉換採用 OpenCC `s2twp`（台灣正體＋常用詞彙），語境投票修正了部分一字多繁（如「发→發/髮」）的取捨。
- 隱藏第二頁的簡體 UV 表在加密 exe 內、無法建立映射，因此採取「整頁清黑」方案而非重繪繁體。
- 未修改、也不依賴漢化組的 ASI 插件（`BloodstoneCN.asi` / `NPCSubtitles.asi`），它們需保留在遊戲目錄中。

## 免責聲明

- 本倉庫**不含**任何遊戲資源、漢化補丁、字庫或版權素材，僅提供針對用戶自有遊戲文件的格式轉換腳本。
- 請自備正版遊戲與簡體漢化補丁；對漢化組作品的版權歸原作者所有。
- 修改遊戲文件存在風險，使用腳本前請自行備份，後果自負。

## 致謝

- [Kanadeforever/BloodStone_CN](https://github.com/Kanadeforever/BloodStone_CN)：簡體漢化補丁（文本譯文、ASI 插件、字庫格式基礎），本項目的上游。
- [Ultimate-ASI-Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader)、[DXVK](https://github.com/doitsujin/DXVK)：原補丁依賴的運行時組件。
- [OpenCC](https://github.com/BYVoid/OpenCC)：簡轉繁轉換引擎。

## 授權

腳本部分以 [MIT License](LICENSE) 釋出。
