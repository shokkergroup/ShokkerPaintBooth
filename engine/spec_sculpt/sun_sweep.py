# -*- coding: utf-8 -*-
"""Sun Sweep — flat-plane angle-flash simulator (2026-06-19).

Relights an SPB finish (paint albedo + M/R/Cc spec map) under a virtual sun swept across azimuths,
on a FLAT material chip — NO 3D car, NO mesh, NO imported geometry. It makes SPB's invisible
superpower (the angle-reactive flash that only shows in iRacing) VISIBLE inside the app and exportable
as a looping hero GIF per finish.

Correctness note: a literally-flat plane with a single constant normal (N=+Z) shows NO motion as the
sun's azimuth changes (the half-vector's z is azimuth-invariant). The flash in reality comes from
MICRO-SURFACE normal variation — metallic flake, clearcoat texture, paint structure — so this derives
a per-pixel micro-normal field from the finish itself, then runs a real per-pixel Cook-Torrance GGX
lobe. Metallic specular is tinted by the albedo (metals reflect their own colour), so a region with a
hidden colour + high metallic IGNITES in that colour as the travelling highlight crosses it.

Self-contained: numpy + cv2 (already engine deps). Channel mapping (verified against base_registry):
  spec[...,0] = Metallic (R)         metal = M/255
  spec[...,1] = Roughness (G)        rough = G/255   (high G = rough)
  spec[...,2] = Clearcoat (B)        16 = max clear ... 255 = dull, 0 = none  -> cc = (255-B)/239
"""
from __future__ import annotations
import numpy as np

try:
    import cv2
    _HAVE_CV2 = True
except Exception:
    _HAVE_CV2 = False


def _as_f01(a):
    a = np.asarray(a, np.float32)
    if a.size and a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def _blur(a, sigma):
    if sigma <= 0:
        return a
    if _HAVE_CV2:
        return cv2.GaussianBlur(a, (0, 0), float(sigma))
    return a


def _sobel(a, axis):
    if _HAVE_CV2:
        return cv2.Sobel(a, cv2.CV_32F, 1 if axis == 0 else 0, 0 if axis == 0 else 1, ksize=3)
    g = np.gradient(a)
    return g[1] if axis == 0 else g[0]


def clearcoat_strength(spec_u8):
    """B near 16 = max clearcoat, 255 = dull, 0 = none (per iron rules / base_registry)."""
    B = np.asarray(spec_u8, np.float32)[..., 2]
    cc = np.clip((255.0 - B) / (255.0 - 16.0), 0.0, 1.0)
    return np.where(B < 1.0, 0.0, cc).astype(np.float32)


def derive_micro_normal(tex, spec_u8, bump=3.0, flake_tilt=0.85, seed=7):
    """Per-pixel micro-normal that makes the sweep actually MOVE. Two parts:
      (1) macro relief (paint structure + clearcoat) so the travelling highlight catches edges, and
      (2) metallic FLAKE micro-mirrors: each metallic pixel gets a strongly-tilted random normal, so a
          flake mirrors the sun only when the azimuth aligns with its tilt -> individual flakes glint
          and TWINKLE across the sweep (this is what produces the real flash; near-+Z normals alone are
          azimuth-invariant and show no motion)."""
    H, W = tex.shape[:2]
    lum = 0.299 * tex[..., 0] + 0.587 * tex[..., 1] + 0.114 * tex[..., 2]
    M = np.asarray(spec_u8, np.float32)[..., 0] / 255.0
    cc = clearcoat_strength(spec_u8)
    height = _blur(0.6 * lum + 0.4 * cc, 1.0)
    gx = _sobel(height, 0) * bump
    gy = _sobel(height, 1) * bump
    # strong random flake tilts (tiny mirrors), magnitude biased small-with-a-bright-tail, gated by metal
    rng = np.random.default_rng(int(seed))
    ang = rng.uniform(0.0, 2.0 * np.pi, (H, W)).astype(np.float32)
    mag = (rng.random((H, W)).astype(np.float32) ** 2.2) * float(flake_tilt) * M
    nx = -gx + np.cos(ang) * mag
    ny = -gy + np.sin(ang) * mag
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-9)
    return np.stack([nx * inv, ny * inv, nz * inv], axis=-1).astype(np.float32)


def _fresnel(cos_t, F0):
    return F0 + (1.0 - F0) * np.power(np.clip(1.0 - cos_t, 0.0, 1.0), 5.0)


def relight_frame(tex, spec_u8, normal, light_dir, view_dir=(0.0, 0.0, 1.0),
                  light_color=(1.0, 1.0, 1.0), ambient=0.10, gain=3.2):
    """One Cook-Torrance GGX frame on the flat chip with a per-pixel micro-normal."""
    tex = _as_f01(tex)
    spec_u8 = np.asarray(spec_u8, np.float32)
    M = spec_u8[..., 0] / 255.0
    R = np.clip(spec_u8[..., 1] / 255.0, 0.045, 1.0)
    cc = clearcoat_strength(spec_u8)
    N = normal
    L = np.asarray(light_dir, np.float32); L /= (np.linalg.norm(L) + 1e-9)
    V = np.asarray(view_dir, np.float32); V /= (np.linalg.norm(V) + 1e-9)
    Hh = L + V; Hh /= (np.linalg.norm(Hh) + 1e-9)
    NdotL = np.clip(N[..., 0] * L[0] + N[..., 1] * L[1] + N[..., 2] * L[2], 0.0, 1.0)
    NdotV = np.clip(N[..., 0] * V[0] + N[..., 1] * V[1] + N[..., 2] * V[2], 0.0, 1.0)
    NdotH = np.clip(N[..., 0] * Hh[0] + N[..., 1] * Hh[1] + N[..., 2] * Hh[2], 0.0, 1.0)
    VdotH = float(np.clip(V @ Hh, 0.0, 1.0))
    a = R * R
    a2 = a * a
    d = NdotH * NdotH * (a2 - 1.0) + 1.0
    D = a2 / (np.pi * d * d + 1e-7)
    k = (R + 1.0) * (R + 1.0) / 8.0
    G = (NdotV / (NdotV * (1.0 - k) + k + 1e-6)) * (NdotL / (NdotL * (1.0 - k) + k + 1e-6))
    # F0: dielectric 0.04, metals reflect their own albedo (this is what makes hidden colours IGNITE)
    F0 = (1.0 - M)[..., None] * 0.04 + M[..., None] * tex
    F = F0 + (1.0 - F0) * np.power(1.0 - VdotH, 5.0)
    spec = (D * G)[..., None] * F / (4.0 * NdotV * NdotL + 1e-3)[..., None] * NdotL[..., None]
    # clearcoat: a sharp secondary lobe gated by cc strength
    acc = 0.06 * 0.06
    dcc = NdotH * NdotH * (acc * acc - 1.0) + 1.0
    Dcc = (acc * acc) / (np.pi * dcc * dcc + 1e-7)
    spec_cc = (Dcc * _fresnel(VdotH, 0.04) * NdotL * cc)[..., None]
    diff = tex * (1.0 - M)[..., None] * NdotL[..., None]
    lc = np.asarray(light_color, np.float32)[None, None, :]
    lit = ambient * tex + (diff + (spec + spec_cc) * gain) * lc
    # soft filmic tone-map so flake glints POP (bright sparkle) without the whole chip clipping flat
    out = 1.0 - np.exp(-lit * 1.5)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def sun_sweep(tex, spec_u8, n_frames=24, elevation_deg=34.0, bump=3.0, flake_tilt=0.85, seed=7,
              light_color=(1.0, 0.97, 0.92)):
    """Return a list of HxWx3 float01 frames, sun azimuth swept 0..360 at fixed elevation."""
    tex = _as_f01(tex)
    normal = derive_micro_normal(tex, spec_u8, bump=bump, flake_tilt=flake_tilt, seed=seed)
    el = np.radians(float(elevation_deg))
    frames = []
    for i in range(int(n_frames)):
        az = 2.0 * np.pi * i / float(n_frames)
        L = (np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el))
        frames.append(relight_frame(tex, spec_u8, normal, L, light_color=light_color))
    return frames


def frames_to_gif(frames, out, fps=18, max_size=360):
    """Assemble float01 frames into a looping GIF via PIL. `out` may be a path (str) or a file-like
    (e.g. io.BytesIO) — format='GIF' is passed explicitly so a buffer works for the server route."""
    from PIL import Image
    imgs = []
    for f in frames:
        a = (np.clip(f, 0, 1) * 255).astype(np.uint8)
        im = Image.fromarray(a, 'RGB')
        if max_size and max(im.size) > max_size:
            s = max_size / max(im.size)
            im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
        imgs.append(im)
    dur = int(1000.0 / max(1, fps))
    imgs[0].save(out, format='GIF', save_all=True, append_images=imgs[1:], duration=dur, loop=0, optimize=True)
    return out
