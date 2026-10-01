# 内容与事实来源

## 私有记录与公开数据分开

`project-brief.md` 记录来源、确认状态、修订和设计选择；`profile.js` 或项目的数据文件只放可公开文字与资源路径。不要把附件全文、证件或未获同意公开的联系方式塞进前端。

用户最新明确更正优先于旧资料。区分团队成果、参与项目规模和个人职责，不顺手扩大归属。

## 底稿字段

`assets/profile.example.json` 与 `assets/starter/profile.js` 使用同样的对象；后者外包 `window.RESUME_DATA = …;`，以便本地直接打开、不依赖网络请求。

| 字段 | 用法 |
| --- | --- |
| `draft` | 是否展示示例／待核对提示 |
| `name`、`role`、`location` | 姓名、当前定位、可公开地点 |
| `headline` | 两行首页标题，不虚构职务 |
| `intro`、`about` | 一句话定位、介绍段落数组 |
| `photo`、`photoAlt` | 本地相对图片路径和替代文字 |
| `layout` | `overlay`、`split` 或 `type` |
| `theme.accent`、`theme.background` | 十六进制强调色与背景色；改后检查对比度 |
| `directions` | `title`、`detail` |
| `metrics` | `value`、`label`、`context`；写清时间、单位和口径 |
| `experience` | `period`、`organization`、`role`、`location`、`points` 数组 |
| `projects` | `title`、`category`、`description`、可选 `url` |
| `skills` | `name`、`detail`，不用虚构百分比 |
| `education` | `school`、`detail` |
| `contact` | `label`、`url`；无公开联系方式时留空 |
| `resume` | `file` 为真实 PDF／DOCX 相对路径，`filename` 为下载名称 |

数组可为空，不为填满布局编造内容。交付时补齐、合并或隐藏无内容栏目。`--final` 检查不了事实真伪，仍需要人工核对。

## 修改一个事实的顺序

1. 记录旧值、新值及范围，例如“某段经历的岗位标题”，而非全局替换一个数字。
2. 改公开内容源。底稿的主页与阅读页自动共享该源。
3. 如另有 PDF／DOCX，修改对应内容并检查最终渲染。底稿不会自动修改外部简历文件。
4. 检查下载实际文件、链接和缓存版本。
5. 更新正式交付包；历史稿同步事实或明确标为历史，不当作当前资料。

“已同步”必须有文件或渲染证据。改了按钮文字不代表下载简历也已改变。
