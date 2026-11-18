# damru 远程控制台（Design artifact）

来源：Claude Design 类型 artifact「damru 远程控制台」

- slug：`37bd3444-4bf4-4eb4-973c-14fdac230952`
- 版本：`1794998212-875e`

## 提交的内容

`project/` 下是用户自己的设计内容：

| 文件 | 页面 | 大小 |
|---|---|---|
| `Main.dc.html` | 总览 | 15132 B |
| `Tasks.dc.html` | 任务 | 20484 B |
| `Worker.dc.html` | Worker 详情 | 15430 B |
| `Proxy.dc.html` | 网络代理 | 14208 B |
| `Audit.dc.html` | 审计与令牌 | 12862 B |
| `Confirm.dc.html` | 危险操作确认 | 3344 B |
| `canvas.json` | 画布布局（6 个画板） | 1351 B |

每个文件的字节数和 sha256 都与 artifact 的文件列表（list_files）记录一致。

## 未提交的内容

- `index.html`、`SKILL.md`、`artifact-type/`：Design 类型自带的文件（`of_type`），由类型发布方提供，不是用户内容，因此不放入仓库。
- 各页面都引用了 `./support.js`。该文件不在 artifact 的文件列表里，也没有提交，需要时请从 artifact 运行环境获取。
