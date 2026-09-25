# 参考文献

本仓库复现的基准题来自下面这篇开放获取（CC-BY 4.0）论文。**论文原文不随本仓库分发**，请通过 DOI 或出版社链接获取。

## 被复现的文献

> J. Xiao, Y. Zhang, S. Li, L. Chen, J. Li, C. Zhang,
> **Research on Equivalent One-Dimensional Cylindrical Modeling Method for Lead–Bismuth Fast Reactor Fuel Assemblies**,
> *Energies* **18** (2025) 3564.
> doi: [10.3390/en18133564](https://doi.org/10.3390/en18133564) · CC-BY 4.0

本仓库用到的数据：

| 位置 | 内容 |
|---|---|
| 表 1 | 材料成分：UO₂ 5 %/28.3 %/66.7 %(at)，HT-9 70 %/11.5 %/1 %(at)，Pb-Bi 44.3 %/55.7 %(at) |
| 表 2 | 几何：燃料棒内/外径 1.651/2.210 mm，气隙 0.254 mm，包壳 0.316 mm，P/D = 1.7144，盒壁厚 1.016 mm，盒边长 56.134 mm |
| 表 3 / 表 4 | 参考 k_eff（“Before Equivalence”，2-D OpenMC）：14.83 % 富集度 → **1.31181 ± 0.00023** |
| 图 1 | 组件布置图（用于反解棒数与 P/D，见 `scripts/measure_fig1.py`） |

## 相关工具与数据

- **OpenMC**：P. K. Romano, N. E. Horelik, B. R. Herman, A. G. Nelson, B. Forget, K. Smith,
  *OpenMC: A State-of-the-Art Monte Carlo Code for Research and Development*,
  Ann. Nucl. Energy **82** (2015) 90–97. doi:[10.1016/j.anucene.2014.07.048](https://doi.org/10.1016/j.anucene.2014.07.048)
- **NJOY2016**：A. C. Kahler et al., *The NJOY Nuclear Data Processing System, Version 2016*, LA-UR-17-20093.
- **ENDF/B-VIII.0**：D. A. Brown et al., *ENDF/B-VIII.0: The 8th Major Release of the Nuclear Reaction Data Library*,
  Nucl. Data Sheets **148** (2018) 1–142. 数据取自 IAEA Nuclear Data Services。
- **Godiva 基准**：R. E. Peterson / LANL critical assembly 数据（LEU-MET-FAST-001，ICSBEP Handbook）。

## 引用本仓库

见 [`CITATION.cff`](../CITATION.cff)。
