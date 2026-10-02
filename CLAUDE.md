# Flappy Dawn — 3D Flappy Bird（Web）

单文件 Three.js 网页游戏：玩家用空格 / 点击 / 触屏让小鸟扇翅，穿过迎面而来的管子。
低多边形「黎明山谷」风格：渐变天空、太阳、云、三层视差山丘、树和灌木、滚动草地、实时阴影和雾。

- 已发布为 Claude Artifact：https://claude.ai/code/artifact/b7eb9848-a786-4e1c-b715-2243a6835099
  （本会话直接重新发布同一文件即可更新；其他会话发布时要把该 URL 作为 `url` 传入，否则会新建 artifact）
- 游戏内 UI 文案是英文；和用户交流用中文。

## 文件

| 文件 | 作用 |
| --- | --- |
| `flappy-dawn.html` | **唯一的源码文件**，也是 artifact 的发布源。故意不含 doctype/html/head/body（Artifact 宿主会自动包裹）。所有修改都在这里。 |
| `build.py` | 由源码生成 `index.html` 和 `dev.html`，并用 node 做语法检查。改完源码后运行 `python build.py`。 |
| `index.html` | 生成物。加了标准 HTML 外壳，可直接双击在浏览器里玩。 |
| `dev.html` | 生成物。同 index，另外暴露 `window.__dbg`（游戏内部句柄）和 `window.__events`（标记触发日志），用于脚本化测试。 |
| `.claude/launch.json` | Browser 预览用的本地静态服务器（`python -m http.server 8765`）。 |

生成物不要手改，改源码后重新 build。

## 运行与测试

- 本地试玩：双击 `index.html`，或 `python -m http.server 8765` 后打开 http://localhost:8765/index.html。
- 需要联网：Three.js r128 来自 cdnjs，字体（Titan One、Nunito）来自 Google Fonts。
- **内置 Browser pane 不跑 requestAnimationFrame**（只在截图时绘制一帧），不能在里面实时试玩，第一次点击还常被吞掉。实时手感请用 artifact 链接或本机浏览器。
- 逻辑验证用 `dev.html` 的 `window.__dbg`（在 Browser pane 里用 javascript_tool 调用）：
  - `start()` / `flap()` / `die()` / `reset()`
  - `step(1/60)` 推进一帧物理并渲染；`render()` 只渲染
  - `state()` 返回 `{ state, score, birdY, vy, speed, columnsMade, cols:[{x, gaps:[[y,size,marker]], segs}] }`
  - `setBird(y, vy)` 直接摆放小鸟；`placeColumn(pipes[i], x, gaps)` 摆放指定管子
  - `advance(seconds)` 推进游戏时钟 `t`（死亡后 0.7 s 内的重开冷却依赖它）
  - `window.__events` 记录每次标记触发 `[marker, score, birdY]`
- 语法检查：`python build.py` 末尾会调用 node 执行 `new Function(script)`。

## 代码结构（`flappy-dawn.html` 的 `<script>`，按出现顺序）

1. DOM 引用、工具函数（`clamp / rand / lerp / pick / col`）。`col(hex)` = `Color.convertSRGBToLinear()`，材质颜色一律经它转换。
2. persistence：localStorage 键 `flappy-dawn-best`、`flappy-dawn-muted`，读写都包在 try/catch 里。
3. tuning 常量：`GROUND_Y=-3.5 CEIL_Y=7.4 GRAVITY=-30 FLAP_V=9.6 MAX_FALL=-17 BIRD_R=0.42`，`PIPE_R=0.9 RIM_R=1.08 RIM_H=0.7 PIPE_COUNT=8 START_X=15`，动态间距常量 `DANGER_W≈2.92 S_FLOOR=5 S_CEIL=12 CLIMB_RATE=4 FALL_RATE=10`，相机 `CAM_X / CAM_LOOK_X`，地面 `GROUND_W / GROUND_D / TILE`。
4. `Sfx`：WebAudio 合成音效（flap / score / hit / reward / punish / swoosh），无音频文件；AudioContext 在首次输入时创建。
5. renderer / camera / scene：`outputEncoding = sRGB`，**无 tone mapping**；`resize()` 按宽高比切换 fov（竖屏 62、横屏 46）并拉远相机。
6. 灯光、天空穹顶（ShaderMaterial 渐变，跟随相机；用原始 sRGB 值）、太阳圆盘 + 光晕、地面（Canvas 生成的无缝草地贴图，`groundTex.offset.x` 滚动）。
7. 世界道具：`layers.near`（树、灌木，速度 1.0）、`mid`（绿色山丘 0.35）、`far`（青灰远山 0.12）、`clouds`（0.2 + 自漂移）。`moveLayer` 负责回收重生，`scrollWorld(dx, dt)` 一次推进全部。
8. **pipe columns**：`makeColumn()` 预建 `MAX_GAPS+1=6` 段管身 + `MAX_GAPS*2=10` 个管口 + `MAX_GAPS=5` 个标记槽；`placeColumn(c, x, gaps)` 由 `gaps` 推导管段 `segs`（不用的部件自动隐藏）；`pickGapCount()` 按分数加权随机选口数（1-5），受 `maxAllowedGaps()` 上限；`makeGaps(prevGaps)` 生成口并验证可达性（最多重试 4 次，失败则回退安全单口）；辅助函数 `minTraverseGap()` / `spacingBounds()` / `computeSpacing(prev, next)`；`parkPipes()` 停到 x=200；`animateMarkers(dt)` 让标记旋转浮动。
9. **`GAP_EFFECTS` + `triggerGap`**：奖惩标记的效果接入点（见下）。
10. bird：由球体 / 圆锥拼成的组，`wingL / wingR` 是翅膀 pivot，整体 `scale 1.12`。
11. particles：对象池，`dot`（60）与 `feather`（18）两种；`emit(kind, n, x, y, z, mats, spd, life, grav, up)`。
12. game state：`start / flap / addScore(n) / die / reset / action`；输入（pointerdown、Space/↑/W、M 静音）；`updatePlaying(dt)`（物理 2 子步 → 滚动 → 碰撞 → 计分/触发 → 回收）；`frame()` 主循环（翅膀、标记、粒子、相机跟随 + 震屏）。

## 关键机制

- 坐标：小鸟固定在 x=0，世界向 -x 滚动；管子 group 在 z=0。计分点是管子中心过 x=0。
- 通过口生成（`makeGaps(prevGaps)`）：前 `WARMUP_COLUMNS=2` 根固定单口；之后由 `pickGapCount()` 按分数加权随机选口数。
  - 口数概率：5 档加权随机，高档随分数解锁并递增权重（2 口≥3 分、3 口≥10 分、4 口≥20 分、5 口≥35 分），受 `maxAllowedGaps()` 封顶（基于 `minTraverseGap()` 物理公式确保每口可穿越）。
  - 单口：高度在上一根基础上随机走（上根≥3 口 → ±1.5，2 口 → ±2.2，1 口 → ±3），限制在 `[lo+gap/2, min(hi-gap/2, 4.4)]`。
  - 多口：`perGap` = 可用空间均分（2 口额外限 3.1），最小 `BIRD_R*3`；`midSize` 相邻口间管壁 ≥ `MIN_MID=0.6`；有剩余空间时随机偏移。
  - gap 尺寸 `currentGap() = max(2.7, 3.5 - score*0.03)`；速度 `6 + min(score,40)*0.06`。
  - 可达性验证：生成后调用 `computeSpacing(prevGaps, gaps)` 检查所需间距 ≤ `sMax`，不满足则缩小 walk 重试（最多 4 次），全部失败回退为上一列附近的安全单口。
- 动态管道间距：移除了固定 `PIPE_SPACING=7.2`，改为逐列计算。
  - `DANGER_W ≈ 2.92`：管体碰撞区水平宽度，间距的不可压缩部分。
  - `computeSpacing(prev, next)`：取最佳口对（上升用 `CLIMB_RATE=4`，下降用 `FALL_RATE=10`），返回 `DANGER_W + speed × tFree + 0.05`（含浮点安全余量）。
  - 间距范围 `spacingBounds()`：`[max(S_FLOOR, DANGER_W+speed×0.25), min(S_CEIL, DANGER_W+speed×1.0)]`，实际间距 clamp 到此区间。
- 标记（只在多口管子上）：每口 `rollMarker()`：45% `reward`（金色星星）/ 35% `punish`（紫色刺球）/ 20% 无；全无则强制一个。
- 触发：过中心线时按 `birdY` 判定所处的口，任何口都 +1；该口有标记 → `triggerGap(c, i)`：隐藏标记、粒子、音效、toast（"★ Reward" / "✖ Trap"），再调用 `GAP_EFFECTS[kind].apply(ctx)`。
- `ctx = { column, opening, index, score, addPoints(n), die }`。**`apply()` 目前是空的，等待用户定义奖惩效果**（这是下一步待办）。
- 碰撞：`hitRect` 圆 vs 矩形，对每段 `segs` 和每个口的上下管口（略宽 `RIM_R-0.04`）检测；小鸟命中半径 0.42 比视觉小，故意宽松。
- 管口与管身共轴，管口高度多出 0.02 覆盖管身端面，避免 z-fighting。

## 约定

- 保持单文件架构，不引入打包器 / 框架。
- Artifact CSP：外部脚本只能来自 cdnjs（当前 `three.js/r128/three.min.js`，是最后带 UMD 版本的几个发行之一，不要随意升级到 r160+），样式字体只能来自 Google Fonts，其余资源内联。
- 材质颜色用 `col()`；天空 shader 和 fog 颜色的关系已对齐（fog 用线性值，天空用原始值），改颜色时保持这一规则。
- 标准改动流程：改 `flappy-dawn.html` → `python build.py` → 用 `dev.html` 的 `__dbg` 做脚本化验证 → 重新发布 artifact（同一 URL）。
- 视觉基调：ink `#1f2b3d`、paper `#fff6e4`、accent `#ff6b35`、gold `#ffb347`、sky `#7ec3f2`、trap purple `#8b5cf6`；字体 Titan One（展示）+ Nunito（正文）；贴纸风 HUD（粗描边、硬阴影）。
