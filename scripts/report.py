#!/usr/bin/env python3
"""Generate the one-page PDF summary report (Chinese, A4, single page)."""
import argparse
import json
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
F = "STSong-Light"

TITLE = ParagraphStyle("title", fontName=F, fontSize=14.5, leading=17,
                       alignment=1, spaceAfter=1.5)
SUB = ParagraphStyle("sub", fontName=F, fontSize=8.2, leading=10, alignment=1,
                     textColor=colors.HexColor("#555555"))
H = ParagraphStyle("h", fontName=F, fontSize=9.6, leading=11.6, spaceBefore=3.4,
                   spaceAfter=1.4, textColor=colors.HexColor("#0b3d6b"))
BODY = ParagraphStyle("body", fontName=F, fontSize=7.9, leading=10.0,
                      alignment=TA_JUSTIFY)
SMALL = ParagraphStyle("small", fontName=F, fontSize=7.3, leading=9.2)
CONC = ParagraphStyle("conc", fontName=F, fontSize=8.8, leading=11.4,
                      textColor=colors.HexColor("#7a1f00"))


def tbl(data, widths, header=True, fontsize=7.4):
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), F),
        ("FONTSIZE", (0, 0), (-1, -1), fontsize),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9aa5b1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
                  ("ALIGN", (1, 0), (-1, 0), "CENTER")]
    t.setStyle(TableStyle(style))
    return t


def main():
    ap = argparse.ArgumentParser()
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--summary", default=os.path.join(_repo, "results", "tables",
                                                      "results_summary.json"))
    ap.add_argument("--out", default=os.path.join(_repo, "results", "figures",
                                                  "report_1page.pdf"))
    args = ap.parse_args()

    S = json.load(open(args.summary, encoding="utf-8"))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    story = []
    story.append(Paragraph("铅基（LBE）快堆燃料组件简化模型 OpenMC 临界计算与文献基准对比", TITLE))
    story.append(Paragraph(
        "复现对象：J. Xiao et al., <i>Research on Equivalent One-Dimensional Cylindrical Modeling Method "
        "for Lead–Bismuth Fast Reactor Fuel Assemblies</i>, Energies 18 (2025) 3564, doi:10.3390/en18133564 "
        "（全燃料棒布置组件，2-D 非均匀模型 “Before Equivalence” 结果）", SUB))

    story.append(Paragraph("1. 目标", H))
    story.append(Paragraph(
        "用开源蒙特卡洛程序 OpenMC 建立该文献铅铋冷却快堆燃料组件的简化模型，计算 k<sub>eff</sub> 与中子通量分布，"
        "并与文献给出的参考值比较，验证建模与核数据加工链的正确性（判据：偏差 &lt; 1 %，统计误差 &lt; 0.001）。", BODY))

    story.append(Paragraph("2. 方法", H))
    story.append(Paragraph(
        "<b>程序/数据</b>：OpenMC 0.16.0（conda-forge, Linux, 12 线程 OpenMP）；连续能量中子截面由 ENDF/B-VIII.0 "
        "评价文件经 NJOY2016.78 加工为 ACE 后转 OpenMC HDF5 库（24 个核素，293.6 K）。"
        "<b>几何</b>：六角形组件、91 根燃料棒（5 环六角栅格，栅距 0.57432 cm，P/D = 1.7144）、"
        "环形 UO<sub>2</sub> 芯块（内径 1.651 mm / 外径 2.210 mm）、氦气隙 0.254 mm、HT-9 包壳 0.316 mm，"
        "棒外径 3.350 mm；HT-9 六角组件盒对边 56.134 mm、壁厚 1.016 mm；盒内为 Pb-Bi 共晶冷却剂；"
        "组件盒外表面为全反射边界（单组件 k<sub>∞</sub> 模型，与文献 2-D 组件模型一致）。"
        "<b>计数</b>：500 批 × 20 000 粒子，前 100 批丢弃（与文献设置相同）；二维网格通量计数 + 分区能谱计数。", BODY))

    story.append(Paragraph("3. 计算条件与简化", H))
    rows = [["项目", "本工作", "文献 (Energies 18, 3564)"]]
    rows += [r for r in S.get("assumptions", [])]
    story.append(tbl(rows, [34 * mm, 68 * mm, 60 * mm], fontsize=7.0))

    story.append(Paragraph("4. 结果与文献对比", H))
    res = [["量", "本工作 (OpenMC, ENDF/B-VIII.0)", "文献 (OpenMC)", "偏差"]]
    res += S["comparison_rows"]
    story.append(tbl(res, [40 * mm, 50 * mm, 40 * mm, 32 * mm], fontsize=7.2))

    imgs = []
    for path, w in S.get("figures", []):
        if os.path.exists(path):
            imgs.append(Image(path, width=w * mm, height=w * mm * S.get("fig_aspect", 0.62)))
    if imgs:
        story.append(Spacer(1, 1.6 * mm))
        it = Table([imgs], hAlign="CENTER")
        it.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 1),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
        story.append(it)
        story.append(Paragraph(S.get("figure_caption", ""), SMALL))

    story.append(Paragraph("5. 偏差分析", H))
    for p in S.get("analysis", []):
        story.append(Paragraph("• " + p, SMALL))

    story.append(Paragraph("6. 遇到的坑与解决", H))
    for p in S.get("pitfalls", []):
        story.append(Paragraph("• " + p, SMALL))

    story.append(Paragraph("7. 一句话结论", H))
    story.append(Paragraph(S["conclusion"], CONC))

    doc = SimpleDocTemplate(args.out, pagesize=A4, topMargin=11 * mm,
                            bottomMargin=9 * mm, leftMargin=13 * mm, rightMargin=13 * mm,
                            title="OpenMC LBE benchmark - one page report")
    doc.build(story)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
