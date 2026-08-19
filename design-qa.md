# Wemute 0.3 design QA

**Evidence**

- Source visual truth: `/Users/songallen/Desktop/wemute/design/reference/wemute-queue-target.png`
- Packaged implementation: `/Users/songallen/Desktop/wemute/artifacts/implementation-bundle-v02.png`
- Full-view comparison: `/Users/songallen/Desktop/wemute/artifacts/design-comparison-v02-final.png`
- Batch-image state: `/Users/songallen/Desktop/wemute/artifacts/batch-images-bundle-v02.png`
- Image-options state: `/Users/songallen/Desktop/wemute/artifacts/image-options-bundle-v02.png`
- Reference: 1487 × 1058, normalized to 1440 × 1024.
- Implementation screenshots: 1440 × 1024 at device scale 1.
- Main state: five mixed files; two completed, one running at 48%, two queued, one selected row, a three-video batch selector, and Image Options available in the footer.

The offscreen capture omits native macOS window chrome. The packaged `.app` uses the native title bar; the comparison normalizes this known capture difference.

**Findings**

No remaining P0, P1 or P2 issue was found.

- Fonts and typography: system sans-serif, weights, metadata scale and single-line hierarchy remain consistent with the source. `All → MP4 (H.265)` and per-row format names render without truncation.
- Spacing and layout: the source → target → status grid, page margins, adaptive rows and fixed footer preserve the approved composition. The group selector occupies previously empty header space and does not increase row density.
- Colors and tokens: graphite surfaces, low-contrast separators, selected-row tint and one blue action/status accent remain unchanged.
- Image quality: real image thumbnails, extracted video frames and waveform media are sharp, correctly cropped and free of placeholder art.
- Copy and content: the batch label states its scope directly; the three Image Options use outcome-based terms and remain closed by default.
- Icons: existing bundled icon-library assets remain optically aligned. The batch selector intentionally omits an extra media icon to keep the header quiet and preserve its full label.
- Behavior and accessibility: group changes update every non-running item; row selectors still override one file; keyboard/drop interactions remain available. The batch and image-option controls use Qt controls with focus and accessible names.
- Responsiveness: at 1440 × 1024 every persistent action stays visible. Adaptive row heights continue to support the shorter native macOS content viewport without overlap.

**Focused region evidence**

The five-image batch capture verifies the new group control in its intended high-frequency case, and the options capture verifies the closed-by-default popover's typography, field alignment and three settings. There is no corresponding batch or popover state in the original source visual, so these extensions were evaluated against the source's control height, radius, spacing and color tokens rather than a false pixel-for-pixel counterpart.

**Intentional deviations**

- Circular running progress remains replaced by the requested thin horizontal bar.
- A compact `All → format` selector appears only for groups containing at least two files.
- `Image Options` is a quiet footer action; its resize, quality and corner controls live in a temporary popover rather than permanent side chrome.

**Comparison history**

1. QA1 found excessive density and undersized rows; adaptive section and row sizing fixed it.
2. QA2 found missing output/status icon fidelity; a consistent bundled icon set fixed it.
3. QA3 found per-row format truncation; ComboBox internal padding was corrected.
4. QA4 found the initial batch label truncated as `All → MP4 …`; its redundant icon was removed and the control widened. The final packaged capture shows the complete label.

**Implementation checklist**

- [x] Preserve the approved queue hierarchy and linear progress.
- [x] Keep bulk format changes group-scoped and reversible per row.
- [x] Keep image settings closed by default.
- [x] Verify resize, quality and alpha-corner output in the isolated worker.
- [x] Validate the packaged Apple Silicon app and focused states.

**Follow-up polish**

- P3: once native UI automation is added, capture keyboard focus rings and every open ComboBox state in CI.

Final result: passed

## Web W1 addendum

The browser workspace was compared beside the same approved queue reference at
1487 × 1058, then exercised with real local images through ready, converting,
completed and ZIP-download states. A second pass covered 390 × 844 with loaded
rows and the fixed action bar.

No remaining P0, P1 or P2 visual issue was found. The web build retains the
graphite hierarchy, restrained separators, one blue primary action, group output
control, row-level override and requested linear progress. The browser-only
image scope intentionally produces one Images section instead of empty audio or
video chrome. The compact mobile layout moves source details and output controls
into a two-column row without horizontal overflow.

Interaction checks passed for multi-file selection, drag/drop, group format,
single-file override, option changes, conversion, repeated download and clear.
The browser console was clean during the completed-state capture.
