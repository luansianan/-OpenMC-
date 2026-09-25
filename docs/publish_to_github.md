# 发布到 GitHub（网页版创建 + 本地推送）

本仓库本地已经初始化并提交完毕（分支 `main`，53 个文件），只差在 GitHub 上建一个空仓库再推上去。

---

## 方式 A：网页创建 + 本地推送（推荐）

### 第 1 步：在网页上创建空仓库

1. 浏览器打开 <https://github.com/new>（需先登录）。
2. 填写：

   | 字段 | 建议值 |
   |---|---|
   | **Repository name** | `openmc-lbe-assembly-benchmark` |
   | **Description** | `OpenMC 0.16 reproduction of an LBE fuel-assembly criticality benchmark (Energies 18 (2025) 3564), with a packing upper bound and enrichment study showing the published k_eff is inconsistent with the paper's own tables` |
   | **Public / Private** | 按需（公开便于引用） |

3. **⚠️ 关键**：`Initialize this repository with:` 下的 **README / .gitignore / license 三个勾选框全部不要勾**。
   本地仓库里已经有这些文件，勾了会在推送时冲突（`rejected - fetch first`）。
4. 点 **Create repository**。

创建后会看到一个空仓库页面，里面就有仓库地址，形如：

```
https://github.com/<你的用户名>/openmc-lbe-assembly-benchmark.git
```

### 第 2 步：本地推送

打开 **PowerShell**，复制粘贴（把 `<用户名>` 和 `<仓库名>` 换成你自己的）：

```powershell
cd C:\deepseek\openmc-lfr-benchmark
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

会弹出认证窗口：

- **推荐**：让 Git Credential Manager 弹浏览器登录 GitHub（点 `Sign in with your browser`）。
- 或者手动输入：用户名 + **Personal Access Token**（**不是**账号密码！开了两步验证的账号必须用 token）。
  生成入口：GitHub → 右上头像 → Settings → Developer settings → Personal access tokens →
  **Fine-grained tokens**（或 Tokens (classic)），权限勾 **Contents: Read and write**（classic 勾 `repo`）。

推送成功的输出形如：

```
To https://github.com/<用户名>/<仓库名>.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

之后刷新网页，就能看到 README 与全部内容。

### 第 3 步（可选）：改提交作者

首提交用的是占位作者。改成你自己的：

```powershell
cd C:\deepseek\openmc-lfr-benchmark
git config user.name "你的名字"
git config user.email "你的邮箱"
git commit --amend --reset-author --no-edit
git push -f origin main
```

---

## 方式 B：完全没有 git / 推送不通时，用网页上传

适用于「浏览器能上 GitHub，但命令行连不上（本文机器实测 `curl https://github.com` 返回 000）」。

1. 解压 `C:\deepseek\openmc-lfr-benchmark.zip`（例如解压到 `D:\upload\openmc-lfr-benchmark`）。
   该压缩包由 `git archive` 生成，已包含 `.gitignore`、`.gitattributes` 等点文件。
2. 在 GitHub 按方式 A 的第 1 步建一个**空仓库**（同样不要勾初始化选项）。
3. 进入空仓库页面，点 **uploading an existing file**（或 `Add file → Upload files`）。
4. 打开解压后的文件夹，**在资源管理器里先开启「显示隐藏项目」**（查看 → 显示 → 隐藏的项目），
   然后 **Ctrl+A 全选 → 拖到上传区**。
   - 拖**文件夹**会保留子目录结构（`results/`、`scripts/`、`docs/`、`environment/`、`refs/`）。
   - 注意：网页上传单文件上限 25 MB、单次 100 个文件；本仓库共 53 个文件、最大约 450 kB，完全够用。
5. 下方 Commit changes 填一句说明（如 `Initial commit`），点 **Commit changes**。

---

## 推送失败怎么办

| 现象 | 原因 / 解决 |
|---|---|
| `curl https://github.com` 返回 `000`、`git push` 卡住或超时 | 本机到 GitHub 的网络不通（DNS 污染/被墙）。用代理/VPN；若代理在本机端口（如 7890），给 git 也配上：<br>`git config --global http.proxy http://127.0.0.1:7890`<br>`git config --global https.proxy http://127.0.0.1:7890`<br>取消：`git config --global --unset http.proxy`（https 同理） |
| `remote: Support for password authentication was removed` | 必须用 Personal Access Token 当密码，见方式 A 第 2 步 |
| `error: remote origin already exists` | 先删掉再加重设：`git remote remove origin` |
| `rejected - fetch first` / `updates were rejected` | 建仓库时勾了 README 等初始化文件。解决：`git pull --rebase origin main` 后再 `git push`，或删掉远程仓库重建（不勾初始化） |
| 分支名不是 `main` | `git branch -M main` |

---

## 建好后建议补充的仓库设置

- **About**（右上齿轮）：把上面的 Description 填进去；**Topics** 建议
  `openmc`、`monte-carlo`、`neutronics`、`lead-cooled-fast-reactor`、`benchmark`、`endf`、`njoy`、`criticality`
- **License**：仓库已含 MIT 的 `LICENSE`，GitHub 会自动识别并在页面显示
- 若想让它可被引用：仓库已含 `CITATION.cff`，GitHub 侧边栏会出现 “Cite this repository”
- 发布 Release（可选）：Tag 填 `v1.0.0`，标题 `Initial release`，一键附带源代码压缩包
