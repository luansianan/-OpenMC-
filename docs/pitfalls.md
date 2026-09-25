# 踩坑记录（以及怎么绕过去）

本项目的目标是“用 OpenMC 算一个铅基堆简化模型”。真正花时间的不是物理，而是环境与数据。以下按遇到顺序记录，供后来者少走弯路。

## 1. Windows 上没有 OpenMC

- conda-forge 的 `openmc` 只有 **linux-64 / osx-64**，**没有 win-64**：`micromamba create -c conda-forge openmc` 在 Windows 上直接报 `PackagesNotFoundInChannels`。
- PyPI 上也没有官方 wheel（`pip index versions openmc` → 无匹配）。
- 官方文档建议 Windows 用户使用 WSL。
- Docker Desktop 已安装，但 **Docker 引擎需要管理员权限**（`com.docker.service` 无法启动），且 `registry-1.docker.io` 在本机 DNS 解析失败。

**解决**：用 WSL。而且不用管理员：

```powershell
curl.exe -L -o ubuntu.rootfs.tar.gz `
  https://cloud-images.ubuntu.com/wsl/jammy/current/ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz
wsl --import openmc-lfr C:\wsl\openmc-lfr ubuntu.rootfs.tar.gz --version 1
```

## 2. WSL2 起不来

`wsl --import ... --version 2` 后启动发行版报：

```
Wsl/Service/CreateInstance/HCS_E_CONNECTION_TIMEOUT
```

原因是 WSL2 需要 `VirtualMachinePlatform` / Hyper-V，而这需要管理员开启、并可能要求重启。

**解决**：`wsl --set-version <distro> 1` 降到 **WSL1**（syscall 翻译层，不需要 Hyper-V）。WSL1 上 OpenMC/NJOY 都能正常跑。

## 3. micromamba 解压失败（镜像缺 bzip2）

Ubuntu 最小 WSL 镜像里没有 `bzip2`，`tar -xjf` 报 `bzip2: Cannot exec: Permission denied`。

**解决**：用 Python 的 `tarfile` 模块解压（`tarfile.open(..., 'r:bz2')`），见 `environment/setup_wsl.sh`。

## 4. 核数据一个都下不了

| 来源 | 结果 |
|---|---|
| openmc.org 官方 HDF5 库（ANL Box 共享链接） | 301 跳到 `anl.app.box.com`，需要浏览器/JS，脚本下载不到 |
| TENDL（PSI） | DNS/连接不可达 |
| NNDC ENDF/B-VIII.0 | 只有 ENDF-6 评价文件，没有现成 ACE |
| LANL nucleardata | 404 / 站点结构变化 |
| Zenodo | 不可达 |

**解决**：从 **IAEA NDS**（`www-nds.iaea.org/public/download-endf/ENDF-B-VIII.0/n/`）下载 ENDF-6 评价文件（每核素一个 ZIP，命名如 `n_9228_92-U-235.zip`），再用 **NJOY2016.78** 自行加工成 ACE/HDF5 —— 顺便，这条路径本身就是最标准、最可复现的做法。

- 注意 IAEA 对密集请求会返回 **HTTP 403**，脚本里加了 UA 头与 3 秒间隔。
- 只下载需要的 24 个核素（连 Fe/Cr/Mo 的天然同位素一起下），总计约 130 MB，远小于整库。

## 5. NJOY 加工铀同位素把 WSL1 实例打崩

`IncidentNeutron.from_njoy()` 默认重建容差 `error=0.001`（0.1 %）。处理 U-235 / U-238 时 **整个 WSL 发行版崩溃**两次：

```
Error: 0xd00002fe
Wsl/Service/0xd00002fe
```

（内存看门狗显示 NJOY 的 RSS 只有几 MB，说明不是简单的 OOM；U-238 的 **PURR** 不可分辨共振自屏计算本身耗时约 **25 分钟**。）

**解决**：
1. 对 U-235 / U-238 放宽 RECONR 容差到 **2 %**（`LOOSE = {"U235": 0.02, "U238": 0.02}`），其余核素仍用默认 0.1 %；
2. 用一个**独立基准（Godiva）**验证该容差没有引入系统偏差：`k = 1.00071 ± 0.00073`（+71 pcm）。

## 6. 栅元漏填 → lost particles

第一次冒烟测试直接报：

```
WARNING: After particle 802 crossed surface 4 it could not be located in any cell
ERROR: Maximum number of lost particles has been reached.
```

原因：燃料棒 universe 只定义了“中心孔 / 芯块 / 气隙 / 包壳”，**没有定义包壳外的冷却剂**；粒子穿出包壳后就找不到栅元了。几何截面图里“棒间显示为白色（void）”正是这个问题的直观信号。

**解决**：在棒 universe 中补一个无界区域的冷却剂栅元 `Cell(fill=lbe, region=+clad_outer)`（栅格元素边界由 lattice 自身负责裁剪）。

## 7. 统计效率误判（照搬文献批次会跑 3 小时）

该模型燃料体积份额只有 6–14 %、且全反射无泄漏 → 中子几乎不泄漏、随机游走步数极长。实测吞吐仅 **约 900 粒子/秒**（12 线程），文献的 500 批 × 20 000 粒子（10 M）需要约 **3 小时/算例**。

**解决**：本模型的单批方差很小（σ_batch ≈ 0.003 @ 20 000 粒子），要达到 σ<0.001 **只需约 10 个活性批**。因此生产算例取 45 / 30 批 × 20 000 粒子（σ ≈ 8×10⁻⁴），既满足判据又不浪费时间。批次数在 `scripts/run_case.sh` 里可调。

## 8. OpenMC 0.16 的 API 变更

| 变更 | 影响 |
|---|---|
| `openmc.Plane` 改为系数形式 `Plane(a, b, c, d)` | 六角盒的 6 个面要用 `a·x + b·y + c·z − d = 0` 的系数构造 |
| `openmc.PointSource` 被移除 | 改用 `openmc.IndependentSource()` + `.space` / `.energy` |
| 计数数组形状 / 滤波器 `bins` 形式 | 网格计数要 `mean.reshape(nx, ny, -1)[:, :, 0]`；`EnergyFilter.bins` 可能是 `(n, 2)` 边界对 |
| 多滤波器计数的 bin 顺序易混 | 改为**每个区域一个能谱计数**，bin 含义唯一，避免顺序歧义 |

## 9. WSL1 的 drvfs 文件元数据损坏

一个位于 `/mnt/c/...` 的 shell 脚本突然在 WSL 里变成 `-?????????`（不可读、不可执行），Windows 侧却完全正常。

**解决**：把代码**同步进 Linux 文件系统**再执行（`scripts/sync_and_run.sh`），结果写回 `/mnt/c` 的仓库目录。

## 10. 几何参数歧义

表 2 的 “Fuel rod inner/outer diameter 1.651/2.210 mm” 未说明是否为环形芯块。用图 1(a) 的棒数（程序化统计 = 91，5 环）与盒体尺寸联立反解，才能确定棒外径必须 ≈3.35 mm（教程见 `docs/model_notes.md`、脚本 `scripts/measure_fig1.py`）。最终模型提供 `--pellet solid|annular` 两种解读，结论对两者都成立。
