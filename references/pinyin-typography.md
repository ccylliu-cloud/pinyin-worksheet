# V2 拼音排印

输入先 Unicode NFC 归一化；ɑ 及其组合声调可作为输入，归一化回 a 系列后校验。
输出 a/ā/á/ǎ/à 映射为 U+0251（单层ɑ）及相应组合声调。

DejaVuSans.ttf 随包分发并嵌入 PDF。ReportLab 普通 Canvas 不依赖浏览器字形定位，
本实现不直接把 ɑ+组合符号交给自动 shaping：ɑ 用字体字形绘制，四个声调用显式矢量线条，
定位在ɑ字宽中心上方。其余元音使用预组合字形，保留ü两点。
字符宽使用实际字体度量，不再使用 Arial 估宽表。

check_glyph.py 一次检查所需字符覆盖、a与ɑ的 glyph ID 不同和字体 SHA256。
这些结构检查不能单独证明单层外观；版式或字体变动后做一次代表性整页视觉验收。
不循环切换系统字体、不反复截图。字体许可证见 assets/fonts/。

中文标题用静态400字重 Noto Sans SC，来自 Google Fonts OFL 字体的固定实例；
标题字形覆盖及最大120mm宽度在写PDF前校验。生成不需要系统中文字体。

官方 API 依据：https://docs.reportlab.com/reportlab/userguide/ch3_fonts/
