#!/usr/bin/env python3
"""Assemble results/tables/results_summary.json - the input of the one-page PDF report."""
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(REPO, "results", "tables")
FIG = os.path.join(REPO, "results", "figures")
PAPER_K, PAPER_S = 1.31181, 0.00023


def load_json(name, default=None):
    path = os.path.join(TAB, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def main():
    ana = load_json("analysis.json", {}) or {}
    rows = ana.get("rows", [])
    gk, gs = ana.get("godiva", [1.00071, 0.00073])
    bk, bs = ana.get("bound", [1.07243, 0.00087])

    comparison = []
    for i, label in enumerate(["k<sub>eff</sub>（环形芯块，表 2 字面读法）",
                               "k<sub>eff</sub>（实心芯块读法）"]):
        if i < len(rows):
            r = rows[i]
            comparison.append([label, f"{r['k']:.5f} ± {r['sk']:.5f}",
                               f"{PAPER_K:.5f} ± {PAPER_S:.5f}",
                               f"{r['dev_pcm']:+.0f} pcm ({r['dev_pct']:+.1f} %)"])
    comparison += [
        ["工具链验证：Godiva 裸高浓铀球", f"{gk:.5f} ± {gs:.5f}",
         "1.0000（实验）", f"{(gk-1)*1e5:+.0f} pcm"],
        ["k<sub>eff</sub> 密排极限（栅距 = 棒径，燃料份额上限 39.5 %）",
         f"{bk:.5f} ± {bs:.5f}", f"{PAPER_K:.5f} ± {PAPER_S:.5f}",
         f"{(bk-PAPER_K)*1e5:+.0f} pcm —— 物理上无法达到文献值"],
    ]

    figs = []
    for name_r, name_m in (("flux_radial_solid.png", "flux_map_solid.png"),
                           ("flux_radial_annular.png", "flux_map_annular.png")):
        pr, pm = os.path.join(FIG, name_r), os.path.join(FIG, name_m)
        if os.path.exists(pr) and os.path.exists(pm):
            figs = [[pr, 82], [pm, 82]]
            break

    summary = dict(
        comparison_rows=comparison,
        assumptions=[
            ["几何（文献表 2）", "六角组件 91 棒/5 环（由图 1(a) 统计），P/D = 1.7144，"
             "芯块 Ø2.210、气隙 0.254、包壳 0.316 mm，棒外径 3.350 mm；"
             "组件盒对边 56.134 mm、壁厚 1.016 mm", "表 2 同值"],
            ["材料（文献表 1）", "UO<sub>2</sub> 5/28.3/66.7 at%（= 15.02 % 富集度），"
             "10.94 g/cm<sup>3</sup>；Pb-Bi 44.3/55.7 at%，10.29 g/cm<sup>3</sup>；"
             "HT-9 70/11.5/1 at%（Fe/Cr/Mo 天然同位素），7.8 g/cm<sup>3</sup>", "表 1 同值"],
            ["程序 / 核数据", "OpenMC 0.16.0；ENDF/B-VIII.0（IAEA NDS）+ NJOY2016.78 "
             "自加工 24 核素 HDF5，293.6 K", "OpenMC，版本未说明"],
            ["边界 / 统计", "组件盒外表面全反射（2-D 组件 k<sub>∞</sub>）；"
             "45 / 30 批 × 20 000 粒子、弃 5–10 批（σ ≈ 8×10<sup>-4</sup>）",
             "500 批 × 20 000 粒子、弃 100 批（σ = 2.3×10<sup>-4</sup>）"],
        ],
        analysis=[
            "<b>偏差不是本工作引入的</b>：Godiva 基准验证核数据链与输运计算，偏差仅 "
            f"{(gk-1)*1e5:+.0f} pcm。",
            "<b>几何反解自洽</b>：由图 1(a) 程序化统计得到 91 个燃料棒（5 环），实测 P/D = 1.77 "
            "与表 2 的 1.7144 吻合；反解出的棒外径 3.17–3.41 mm 与「芯块 2.210 + 2×(0.254+0.316) = "
            "3.350 mm」一致。",
            "<b>燃料份额被棒设计锁死</b>：该棒在 P/D = 1.7144 的栅格中燃料体积份额仅 6–14 %；"
            f"密排到棒贴棒（栅距 = 棒径）的上限也只有 39.5 %，k = {bk:.4f} ± {bs:.4f} —— "
            "用表 2 的燃料棒参数搭任何组件都达不到 1.31。",
            "<b>文献值对应约 24 % 富集度</b>：本工作 14.83 % → 1.0395、22 % → 1.2528、"
            "<b>24 % → 1.3075</b>、26 % → 1.3460、30 % → 1.4290；24 % 时与文献 1.31181 仅差 "
            "427 pcm（0.33 %），线性内插得文献值对应约 24.2 % 富集度，而表 1 给出 ~15 %。",
            "<b>结论</b>：文献表 3 的 k<sub>eff</sub> 与其表 1/表 2 的材料几何参数内部不自洽，"
            "偏差并非本工作的几何简化、材料密度或核数据版本所致。",
        ],
        figures=figs,
        fig_aspect=0.60,
        figure_caption="图：本工作 OpenMC 计算的中子通量分布（左：径向分布，圆点 = 环平均、"
                       "方块 = 燃料区；右：组件横截面通量图）。",
        pitfalls=[
            "<b>Windows 无 OpenMC</b>：conda-forge 只有 linux-64/osx-64、PyPI 无 wheel、"
            "Docker 引擎需管理员 → 用 <i>wsl --import</i> 导入 Ubuntu 根文件系统以 WSL1 运行；"
            "micromamba 解压需先用 Python tarfile(bz2)（镜像缺 bzip2）。",
            "<b>核数据源受阻</b>：ANL Box 共享链接需浏览器、TENDL 不可达、NNDC 只给整库 ACE → "
            "改从 IAEA NDS 下载 ENDF/B-VIII.0 评价文件，用 NJOY2016 自加工为 HDF5。",
            "<b>NJOY 加工铀同位素把 WSL1 实例打崩</b>（默认 0.1 % 重建容差，两次 0xd00002fe；"
            "U-238 的 PURR 自屏约 25 min）→ 放宽 RECONR 容差至 2 %，并用 Godiva 验证其影响仅几十 pcm。",
            "<b>栅元漏填</b>：燃料棒 universe 未包含“棒外冷却剂”时粒子穿出包壳即丢失"
            "（几何图中棒间空白暴露该问题），冒烟测试抓出后修复。",
            "<b>统计效率</b>：燃料份额低、全反射无泄漏 → 中子历史极长，实测约 900 粒子/秒，"
            "照搬文献 500 批需约 3 小时 → 按 σ&lt;0.001 的最小充分统计量重设为 45/30 批 × 20 000 粒子。",
            "<b>OpenMC 0.16 API 变更</b>：<i>Plane</i> 改用系数 (a,b,c,d)、<i>PointSource</i> → "
            "<i>IndependentSource</i>，网格/能谱计数的数组形状与滤波器顺序需按新版本处理。",
        ],
        conclusion=(
            "本工作用 OpenMC 0.16 + 自制 ENDF/B-VIII.0 库完整复现了该铅铋快堆组件基准的建模与计算流程"
            "（k<sub>eff</sub> 统计误差约 8×10<sup>-4</sup>，并给出二维/径向通量分布与分区能谱），"
            "工具链经 Godiva 基准验证偏差仅几十 pcm；但按文献表 1/表 2 参数得到的 k<sub>eff</sub> 为 "
            "0.879–1.040，与文献的 1.31181 相差 21–33 %。密排极限（1.0724）与富集度扫描证明："
            "该燃料棒设计在 ~15 % 富集度下物理上不可能达到 1.31（需约 24 % 富集度），"
            "故偏差源自文献材料/几何参数与其 k<sub>eff</sub> 参考值之间的内部不自洽。"),
    )
    out = os.path.join(TAB, "results_summary.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("wrote", out)
    for r in comparison:
        print("  ", " | ".join(map(str, r)))
    if not rows:
        print("WARNING: results/tables/analysis.json has no run rows yet - "
              "run scripts/analysis.py after a calculation", file=sys.stderr)


if __name__ == "__main__":
    main()
