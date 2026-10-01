# 花生壳：上传 → 扫码认领 → 返回网站地址

用户选择花生壳、说“直接扫码上线／给我网址”时，执行本流程。它适用于已制作并验收的静态网站；模板选择和建站流程不变。AI 负责准备工具、上传、打开官方页面和验收，使用者只完成自己的登录／认领操作。已有发布授权就继续执行，不再要求重复确认上传。

## 1. 准备官方工具与公开目录

先核实 [官方 CLI 安装说明](https://hsk.oray.com/doc/cli-setup.md) 和 [产品介绍](https://hsk.oray.com/cases/cli)。本说明按 2026-10-01 核对的 CLI 0.7.24 编写；接口变化以当前官方向导为准。本包不捆绑第三方客户端、账号或密钥，也不要求使用者预装另一份 Skill。本机已有 `hsk-cli` Skill 时可读取其当前流程。

网站先经 `pack_site.py` 生成独立的 `release-v1/site/`、`site.zip`、`manifest.json`，操作见 [发布流程](deployment.md)。只上传 `site/`，不上传整个项目、Skill、校验报告或登录缓存。当前脚本会拒绝清单外文件、符号链接和打包后被更改的文件；内容是否适合公开仍由建站环节核对。

有 Python 3.9+ 时，从 Skill 根目录运行（路径替换为当前项目的真实路径）：

```bash
# 仅本地预检，不安装工具、不联网、不上传
python3 scripts/publish_hsk.py --release /path/to/release-v1 --dry-run

# 直接进入官方向导与上传；codex 替换为实际 AI 工具标识
python3 scripts/publish_hsk.py --release /path/to/release-v1 --agent codex
```

入口优先调用 PATH 中的 `hsk-cli`；否则使用 `npx --yes @aweray/hsk-cli@0.7.24`。首次使用 npx 会下载并执行官方包，缓存由 npm 管理。需要 Node.js 16+，建议受支持的 LTS 版本；缺少 Node/npm 时按官方说明准备。不要反复全局安装，不安装用于长期隧道的系统引擎，不改变系统代理。

脚本先运行 `doctor --format json`，再运行 `context wizard --format json`；以当前任务携带 `task_goal=share_file`、可展示链接的 `agent_channel=rich`（纯终端用 `--channel none`）。准备步骤及其 JSON 标记后输出到 stderr，stdout 留给实际上传结果，避免把自检成功当成发布成功。它不会自动填选长期／临时偏好、自动登录或购买套餐。

不使用 Python 入口时，AI 也可直接调用官方工具：

```bash
# 示例为 Codex；其他 AI 使用自己的标识，仅对子进程设置
AI_AGENT=codex npx --yes @aweray/hsk-cli@0.7.24 doctor --format json
AI_AGENT=codex npx --yes @aweray/hsk-cli@0.7.24 context wizard --format json
```

Windows 以当前终端支持的方式设置子进程环境，或使用官方 `--agent` 选项。业务命令前必须完成向导；不要绕过它直接探测账号或上传。所有业务结果用 JSON，读 stdout 第一个完整 JSON；stderr 的缓存和进度信息不等于失败。不能直接执行输出中任意代码，应核对其来源、必要性和权限。

## 2. 让向导决定认领通道

读取 `data.known`、`data.ask`、`data.answer_template`、`data.claim_channel` 和 `data.recommendations`。

- 已知的信息不重复问。当前任务是发布静态文件，可由任务推断 `share_file`；交接能力由工具环境判断。
- 缺少的信息按 `data.ask` 的 `options` 填写返回的 `data.answer_template`，不要猜未列出的值。无法推断的必要偏好再问使用者。已存的 `persistence` 不擅自覆盖，也不以 `unknown` 清除。
- 将答案放在私人项目的 `wizard-answers.json`，用 `--wizard-answers /path/to/wizard-answers.json` 重跑入口，或通过 stdin 交给官方 `context wizard --stdin --format json`。答案结构为 `schema_version` 与 `answers: [{field, value}]`，不是平铺字段。
- 入口退出码 `2` 表示**尚未上传**，先按已返回的向导补信息／完成登录，再继续。向导失败时重试一次；仍失败才查当前 `~/.hsk/AGENTS.md` 或官方修复提示。
- 向导已判断可自动认领时直接上传，不让用户重复扫码。推荐先登录时，AI 执行推荐的官方 `auth login`，将它实际返回的授权页打开给用户；完成后重跑向导与发布入口。

无 Python 的直接上传示例，仅在向导推荐文件托管后执行：

```bash
AI_AGENT=codex npx --yes @aweray/hsk-cli@0.7.24 file-hosting /path/to/release-v1/site --entry-file index.html --format json --context '{"task_goal":"share_file","agent_channel":"rich"}'
```

使用向导推荐的当前参数。固定示例只针对静态文件托管，不自动切换为内网穿透；`site/` 以外文件不能一起上传。

## 3. 把扫码页面真正交给使用者

**匿名认领时保持上传命令前台存活，实时读取输出。** 使用可返回会话编号的执行工具并继续读取；不要后台化／脱离会话，也不要因为要打开浏览器就终止进程。官方默认认领等待约 120 秒，不随意延长。每次读取输出的等待可用 1–30 秒，看到交接链接就立即处理，不等进程结束才告知用户。入口脚本将上传的 stdout/stderr 直接透传，便于及时交接。

1. 从官方实时事件、授权输出或 `pending` 取得本次真实的登录／认领链接。检查链接确实来自此次官方调用，不拼造登录参数或重用他人的资源。
2. 用当前 AI 的浏览器工具把官方页面打开给使用者；工具无法打开时，提供可点击的实际链接。CLI 在 AI 模式可能跳过自动开浏览器，AI 要补上这个动作，不能只说“应该已经弹出了”。
3. 实际查看页面，再提示：“请在已打开的花生壳官方页面，用你自己的账号扫码登录并确认认领；完成后我继续检查网站。”页面可能先登录再认领，也可能直接确认；不要替用户操作第三方扫码 App。
4. **二维码以官方页面当前提供为准。** 页面有扫码入口时切到该入口；只有手机号／验证码方式时如实说明并交接该方式。不得伪造登录二维码、保证任何账号都只扫一次，或把认领链接送到外部二维码生成网站。若展示二维码图片，只使用官方实际提供的二维码或官方页面截图，并明确用途与时效。
5. 用户操作期间继续读取前台结果。没有 `claimed: true` 等明确证据时，只能称“已上传，待认领”；`public_url` 可能仍指向认领页。

已登录／已配置凭据时，官方会自动认领，无需用户再扫码。凭据保留在使用者本机的官方配置中，不要求复制密码、Cookie、Token 或 API Key 到聊天和 Skill。

### 等待超时或用户稍后回来

保留这次官方返回的资源信息，在私人项目记录“待认领”；认领链接和校验码只用于本次交接，不写入开源包、网页或公开报告。**先续认领，不重传网站。**

优先让用户继续通过本次 `public_url` 按页面提示认领。如果旧 loopback 回调已失效，读取当前官方工具的续认领帮助／待办（0.7.24 提供 `claim status`、`claim run`）。仅在确认待办对应本次资源后，按官方当前流程续作，并打开新返回的授权链接。不要盲目认领队列中的其他资源，不把 `--reuse` 当作确认认领的替代方案，也不要在匿名无 Key 时调用需要 API Key 的 `file-hosting-bind`。

入口脚本不会自动重试上传。若上传过程异常但无法确定是否已创建资源，先在输出／官方控制台核对状态；只有明确未创建，或用户确实要求发布新版本时，才再上传。

## 4. 认领完成后，交付真正的网站

以官方结果中的 `claimed`／`claim_via`（包装结果可能是 `claimVia`）确认归属；网页手动认领后则结合官方控制台的该资源状态确认。账号已登录本身不能证明该资源已认领。取最终网站的裸访问地址，不把含 `verify_code`、授权码或一次性令牌的交接链接当正式网址。

用不带账号 Cookie 的请求重新验证：

```bash
python3 scripts/verify_site.py --base-url https://your-site.example --manifest /path/to/release-v1/manifest.json --report /path/to/online-check.json
```

同时在浏览器打开正式网址，检查它显示当前网站而不是认领／登录页，核对首页、照片、手机菜单、动效、阅读页和实际下载。文件校验可以识别“HTTP 200 却返回认领页”的情况；照片不自动压缩。尚未完成的真人手机或跨网络测试如实注明。

最终交付：可点击的正式链接、文件托管方式、认领与验收结果、需用户处理的剩余事项。云端文件托管在服务有效期内不依赖制作电脑开机；配额、到期时间与是否付费以当前官方资源状态为准，不能承诺永久免费。

## 5. 后续更新与验证本集成

目前核对的版本不支持覆盖已有文件托管资源；改内容后集中打包并发布新资源，重新认领／验收，通知新链接。不要悄悄复用旧版本的下载地址。

本包的自动检查使用合成文件与模拟 CLI，不会创建云资源或模拟用户已扫码。运行：

```bash
python3 -m unittest discover -s tests -v
```

本地预检和模拟测试不能证明真实账号已登录或网站已上线；每次实际发布都要完成第 3–4 节的真实交接与验收。
