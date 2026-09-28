// Manga action style (JS plugin): screentone glued to the moving surface, and speed lines drawn from measured motion.
//
// Screentone dots are laid out in the advected texture coordinates, so they ride on each limb. Speed lines trail
// behind parts that actually moved between frames, with length and direction taken from the plate's optical flow;
// nothing is drawn where nothing moved. Needs guides extracted with --flow for both effects.
// Speed lines add strokes outside the subject: declare intent.silhouette_min (about 0.8) when running qc_redraw.py.
//
// params: tone, line_color (#RRGGBB), dot (px pitch), halftone [light_luminance, dark_luminance],
//         speed (px/frame to start a line), length (trail frames), width (px), cell (px between line seeds).

function render(ctx, api) {
  const P = Object.assign({tone: '#221E2E', line_color: '#221E2E', dot: 5, halftone: [0.3, 0.78],
                           speed: 1.5, length: 4, width: 2.4, cell: 18}, ctx.params);
  const W = ctx.width, H = ctx.height, hw = ctx.uvWidth, hh = ctx.uvHeight;
  const hex = s => [1, 3, 5].map(i => parseInt(s.slice(i, i + 2), 16));
  const out = new OffscreenCanvas(W, H), g = out.getContext('2d');

  // 1. Speed lines beneath the figure: one seed per cell, at the fastest trusted-flow pixel inside the subject.
  if (ctx.flow) {
    const cell = Math.max(2, Math.round(P.cell / 2)), [lr, lg, lb] = hex(P.line_color);
    for (let cy = 0; cy < hh; cy += cell) for (let cx = 0; cx < hw; cx += cell) {
      let best = -1, bx = 0, by = 0;
      for (let y = cy; y < Math.min(hh, cy + cell); y++) for (let x = cx; x < Math.min(hw, cx + cell); x++) {
        const i = y * hw + x;
        if (!ctx.flowValid[i] || !ctx.mask[(2 * y) * W + 2 * x]) continue;
        const s = Math.hypot(ctx.flow[2 * i], ctx.flow[2 * i + 1]);
        if (s > best) { best = s; bx = x; by = y; }
      }
      const speed = best * 2;  // half-resolution units to full pixels
      if (speed < P.speed) continue;
      const i = by * hw + bx, fx = ctx.flow[2 * i] * 2, fy = ctx.flow[2 * i + 1] * 2;
      const x0 = bx * 2 + 1, y0 = by * 2 + 1, x1 = x0 + fx * P.length, y1 = y0 + fy * P.length;
      const nx = -fy / speed, ny = fx / speed, w = P.width * Math.min(1.6, 0.6 + speed / 8);
      const grad = g.createLinearGradient(x0, y0, x1, y1);
      grad.addColorStop(0, `rgba(${lr},${lg},${lb},0.9)`); grad.addColorStop(1, `rgba(${lr},${lg},${lb},0)`);
      g.fillStyle = grad; g.beginPath();
      g.moveTo(x0 + nx * w, y0 + ny * w); g.lineTo(x1, y1); g.lineTo(x0 - nx * w, y0 - ny * w); g.closePath(); g.fill();
    }
  }

  // 2. The figure with screentone in texture space (bilinear half-resolution UV, doubled to full pixels).
  const img = new ImageData(new Uint8ClampedArray(ctx.base.data), W, H), d = img.data;
  const [tr, tg, tb] = hex(P.tone), [light, dark] = P.halftone, pitch = P.dot, root2 = Math.SQRT1_2;
  const uvAt = (x, y, k) => {
    const sx = Math.min(hw - 1.001, Math.max(0, x / 2 - 0.25)), sy = Math.min(hh - 1.001, Math.max(0, y / 2 - 0.25));
    const x0 = Math.floor(sx), y0 = Math.floor(sy), ax = sx - x0, ay = sy - y0, at = (xx, yy) => ctx.uv[2 * (yy * hw + xx) + k];
    return 2 * ((at(x0, y0) * (1 - ax) + at(x0 + 1, y0) * ax) * (1 - ay) + (at(x0, y0 + 1) * (1 - ax) + at(x0 + 1, y0 + 1) * ax) * ay);
  };
  if (ctx.uv) for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const p = 4 * (y * W + x);
    if (d[p + 3] === 0) continue;
    const lum = (0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2]) / 255;
    const t = Math.min(1, Math.max(0, (dark - lum) / (dark - light)));
    if (t <= 0) continue;
    const u = uvAt(x, y, 0), v = uvAt(x, y, 1);
    const a = (u + v) * root2 / pitch, b = (u - v) * root2 / pitch;
    const da = a - Math.round(a), db = b - Math.round(b);
    const dist = Math.hypot(da, db) * pitch, radius = pitch * 0.5 * Math.sqrt(t) * 1.05;
    const ink = Math.min(1, Math.max(0, radius - dist + 0.5));
    d[p] += (tr - d[p]) * ink; d[p + 1] += (tg - d[p + 1]) * ink; d[p + 2] += (tb - d[p + 2]) * ink;
  }
  const figure = new OffscreenCanvas(W, H);
  figure.getContext('2d').putImageData(img, 0, 0);
  g.drawImage(figure, 0, 0);
  return out;
}
