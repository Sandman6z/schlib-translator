# Altium SchLib 中文翻译工具

批量将 Altium Designer `.SchLib` 文件中的中文字段翻译为英文。使用同长度原地写入，不改变文件结构。

## 依赖

- Python 3.7+
- [olefile](https://github.com/jborean93/olefile) >= 0.47

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

将需要翻译的 `.SchLib` 文件放到脚本所在目录，然后运行：

```bash
python translate_schlib.py
```

脚本会自动扫描当前目录下所有 `*.SchLib` 文件并逐一处理。

### 示例输出

```
Found 1 SchLib file(s) to process:
  ESLSChLib.SchLib

============================================================
Processing: ESLSChLib.SchLib
============================================================
  Creating backup: ESLSChLib.SchLib.bak
  Opening...
  Components modified: 10
  Field translations: 24
    [COMP_1] ComponentDescription: 贴片电阻 -> SMD Resistor
    [COMP_2] ComponentDescription: 2.2寸_ESL ESL板框,标准版 -> 2.2" ESL Board Outline, Standard

============================================================
Summary: 1/1 files modified, 24 total field translations
All done!
```

## 工作原理

1. 使用 `olefile` 以读写模式打开 SchLib（OLE 复合文档）
2. 遍历每个 Component 的 `Data` 流，查找含中文的 UTF-8 / GBK 字段
3. 用内置词典 `TRANSLATIONS` 和正则规则 `PATTERNS` 翻译为英文
4. 同长度原地写入 —— 若翻译后字节数不超出原文则直接替换
5. 若超出则自动尝试缩写（`Standard` → `Std`，`Connector` → `Conn.` 等）
6. 仍超出则截断，不破坏字段结构

## 翻译覆盖

| 类别 | 方式 | 示例 |
|------|------|------|
| 直接查词典 | `TRANSLATIONS` 字典 | `贴片电阻` → `SMD Resistor` |
| 正则模式 | `PATTERNS` 列表 | `2.2寸_ESL ESL板框,标准版` → `2.2" ESL Board Outline, Standard` |
| 制造商后缀 | 自动去除括号中文 | `Murata(村田)` → `Murata` |
| 标点替换 | 全角转半角 | `，` `、` → `, ` |

### 已支持的词典项

贴片电阻、贴片电容、贴片电感、贴片磁珠、贴片无源晶体、功率电感、层叠电感、
发光二极管、肖特基二极管、压敏电阻、天线、PCB定位点、测试点、RF电阻、
纽扣电池、TVS、FPC连接器、电池触点弹片 等 50+ 条。

### 已支持的复合模式

- `N寸_XXX ESL板框,标准版/标准款` → `N" ESL Board Outline (XXX), Standard`
- `NG PCB天线，倒F，...` → `N G PCB Inverted-F Antenna, ...`
- `NFC PCB天线，N匝，...` → `NFC PCB Antenna, N Turns, ...`
- `VGX寸标准款/超薄款专用` → `Standard/Ultra-Thin VGX"`
- `FPC连接器，下接，间距Xmm，max高Xmm` 等

## 自定义翻译

编辑 `TRANSLATIONS` 字典添加直译词条，或向 `PATTERNS` 列表追加正则规则。

```python
TRANSLATIONS = {
    '新词汇': 'New Translation',
}

PATTERNS = [
    (r'新模式(.*)', lambda m: f'New Pattern {m.group(1)}'),
]
```

## 输出

- 首次运行自动为每个 `.SchLib` 创建 `.bak` 备份
- 控制台打印每个文件的修改统计（修改的 Component 数、翻译字段数）
- 原始文件原地修改，不生成新文件

## 项目结构

```
Schlib_translate/
├── translate_schlib.py   # 主脚本
├── requirements.txt      # Python 依赖
├── README.md             # 本文件
└── *.SchLib              # 待处理的库文件（用户放置）
```
