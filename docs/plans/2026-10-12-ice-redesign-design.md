# Wemute "Ice" redesign — design

Status: approved by the owner on 2026-10-12. Visual reference:
`design/mockups/2026-10-12/index.html`, direction **C · 冰面 (Soft Glass)**,
including the dark-mode window. Open it in a browser before changing UI.

## Why

Two earlier redesigns added controls instead of removing them: a format menu
on every row, an "All →" menu per group, an options popover, a floating command
bar. A first-time user could not tell what to do. The owner wants a very simple
concept, effortless daily use, and visual quality on par with their ThunderTalk
app — without copying ThunderTalk's warm paper, orange, serif type or sidebar.

## The concept

**Drop files, then read one sentence that says what will happen.**

> 把 **12 张图片** 转成 **[JPG ▾]**
> 把 **2 个视频** 转成 **[MP4 ▾]**
> 保存到 **[原文件夹 ▾]**　　　　　**[ 开始转换 → ]**

The pill-shaped words are the only controls. One sentence line per media kind
present (image, video, audio). There are **no per-file format choices**; the
file area is for seeing and removing files only. To treat one file differently,
the user converts it in a separate batch.

## Three states

The window has exactly three states. Each has one main action.

### ① Empty
- The whole window is a drop target. Centered: a soft rounded "bubble" tile
  (tilted −6°) holding a download glyph in cobalt, the title
  "把文件拖到这里" / "Drop files here", and one muted line
  "图片 · 视频 · 音频，全部在本机完成".
- Clicking anywhere opens the file picker. ⌘O and ⌘V also add files.
- No toolbar buttons compete for attention; settings live behind ⌘, and a
  small quiet gear in the title bar.

### ② Ready (files added, nothing running)
- The glass panel shows the sentence at the top and the file cards below.
- Sentence lines appear in order image → video → audio, only for kinds present.
  Count wording: "12 张图片", "2 个视频", "3 段音频" / "12 images", "2 videos",
  "3 audio files".
- The last line is "保存到 [原文件夹 ▾]" with the primary button
  **开始转换 →** aligned right. ⏎ triggers it.
- The image line may carry an optional trailing phrase only when the user has
  changed image options away from defaults, e.g. "，缩小到 1080 像素". It is
  itself a pill that reopens the options.
- Dropping more files updates the counts in place.

### ③ Running → Done
- Running: the sentence stays (pills disabled), a thick rounded progress bar
  (10 px, cobalt gradient) appears under it with "正在转换 8 / 12"; the primary
  button becomes a quiet **停止**. Each card gets a cobalt check badge when its
  file finishes; the currently converting card shows a small circular progress.
- Done: the sentence area is replaced by
  "14 个文件都转好了" (bold) and "一共省下了 **144 MB**" (amount in teal; if the
  batch grew, say "共 186 MB" without a saving claim), with
  **[在访达中显示]** (primary) and **[再转一批]** (secondary). "再转一批" clears
  the list and returns to ①.
- Failures: done state headline becomes "12 个已完成，2 个失败"; failed cards
  show a red badge; a pill "重试失败的 2 个" appears next to the buttons. Hover
  a failed card for the reason.
- If the window is not focused when a batch finishes, bounce the Dock icon.

## Pills (the sentence's words)

- A pill is a rounded (14 px) button: white fill, 1 px tinted outline, soft
  tinted shadow, bold text in the kind's color, small chevron.
- Kind colors: image = cobalt, video = teal, audio = violet; the destination
  pill is neutral ink.
- Clicking opens a rounded popup menu anchored below the pill listing the
  formats for that kind (same lists as today, AI actions included when their
  model is installed). Current choice has a check.
- Image menu ends with "更多选项…" opening a small rounded sheet with:
  尺寸 (原始 / 50% / 长边 2048 / 长边 1080), 质量 (更小 / 平衡 / 最佳),
  圆角 (无 / 24 / 64), 目标大小 (KB). These apply to all images in the batch.
- Destination menu: 原文件夹 ✓ / 其他文件夹… / (recent custom folder).
- Choices are remembered per kind for next time (existing preference logic).

## File cards

- Card: 118 × 148 white rounded (20 px) card with 6 px padding, image area
  104 px tall with 15 px radius, file name below (11 px, rounded font, muted),
  soft shadow. Each card is rotated by a deterministic angle from
  [−4, 2, −2, 3, −3, 1, −2, 4] (by index) so the stack feels physical.
- Video cards show a teal duration badge bottom-right; audio cards show a
  violet waveform/music glyph on a tinted tile; images show their thumbnail.
- Cards wrap into rows inside the panel; the card area scrolls vertically when
  needed (the sentence stays pinned).
- Hover: the card straightens to 0°, lifts 4 px, and a small × appears
  top-right to remove it. Double-click opens Quick Look. Delete removes the
  selected card; arrow keys move selection.

## Visual system

Font: SF Pro Rounded everywhere (`ui-rounded` on the web; in Qt use
`".AppleSystemUIFont"` with the rounded design if available, otherwise
"SF Pro Rounded"). Sentence 30 px bold; counts in the sentence use the strong
text color, connective words ("把", "转成", "保存到") use the muted color.
Figures use tabular numerals.

| Token | Light | Dark |
| --- | --- | --- |
| Base background | `#F2F5FB` | `#0D1220` |
| Glow 1 (top-left) | `#DFE7FF` | `rgba(61,92,255,.28)` |
| Glow 2 (top-right) | `#D9F3EF` | `rgba(20,170,150,.18)` |
| Glow 3 (bottom) | `#E9E4FF` | `rgba(120,90,255,.18)` |
| Glass panel | `rgba(255,255,255,.72)` + 1 px inner white line | `rgba(24,30,48,.66)` + 1 px `rgba(255,255,255,.07)` |
| Strong text | `#182033` | `#F1F4FB` |
| Muted text | `#8A93A8` | `#7D879F` |
| Secondary text | `#5B6478` | `#A4ADC2` |
| Cobalt (image, primary) | `#2C4BF0`, gradient `#3D5CFF → #2440E8` | text `#9FB2FF`, same button gradient |
| Teal (video, savings) | `#0F8F7E` | `#5FE0CB` |
| Violet (audio) | `#6B4FE0` | `#B3A2FF` |
| Error | `#D14343` | `#FF8A80` |
| Card | `#FFFFFF` | `#1C2336` |

Shapes: panel radius 26, pills 14, primary button 20 (56 px tall), cards 20,
menus 14. Shadows are soft and tinted (cobalt or navy), never grey slabs.
Motion only where it informs: pill press, card hover lift, check badges
appearing in sequence, panel edge glowing cobalt while dragging files over the
window. Follow the system appearance (light/dark).

## Settings (⌘,)

A small rounded sheet over the window, three rows only:
保存位置 (原文件夹 / 指定文件夹), 默认格式 (image / video / audio), 语言
(跟随系统 / 中文 / English), plus "添加后自动开始" toggle. AI model management
and About move into this sheet's secondary tabs; they are no longer main-window
buttons.

## What is removed from the main window

Per-row format menus, per-row "Adjust" buttons, the "All →" group menus, the
floating command bar, the separate AI Tools and Image Options buttons, the
notice toast for routine success (the Done state replaces it). Notices remain
only for skipped/unreadable files, shown as a quiet line under the sentence.

## Web edition

Same visual system and sentence model. The home page converter starts in ①.
Tool pages (e.g. HEIC to JPG) pre-fill the sentence ("把 HEIC 照片转成 JPG")
and convert immediately on drop for image/audio tools; video tools wait for the
user to press 开始转换 because they expose GIF/compress options as pills.
Results: per-card download on hover, and the Done state's primary button is
"全部下载" (single file → direct download, many → ZIP). Ads, SEO content and
routes are unchanged.

## Engineering notes

- Keep the existing conversion engines, parallel scheduler, preferences,
  output-name reservation and tests. This redesign changes presentation and
  interaction, plus small controller APIs:
  - Mac: expose `phase` ("empty" | "ready" | "running" | "done"), a `groups`
    list for the sentence (kind, count, target, options), batch summary values
    (done/failed counts, total before/after bytes), and `clearAll` for
    "再转一批". Per-job overrides are no longer set from the UI (the model
    keeps the field for compatibility).
  - Web: same phases in the React converter; remove per-row selects.
- Tests: existing suites must stay green; add controller tests for `phase`
  transitions and group counts.

## Acceptance

1. A first-time user can convert a batch with: drop → ⏎ → "在访达中显示".
2. No per-file format controls exist anywhere.
3. Light and dark modes both match the mockup's direction C windows.
4. All three states render correctly with 1, 14 and 200 files.
5. `uv run pytest`, the QML smoke test, and the web `check`, `test`,
   `test:sites` and `build` all pass.
