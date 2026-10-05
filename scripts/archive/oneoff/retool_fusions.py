import shutil
import os

def main():
    target_path = r"engine\expansions\fusions.py"
    print(f"Reading target file: {target_path}")
    
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"Original content size: {len(content)}")
    
    # 1. Sparkle fusions overhaul
    orig_sparkle = '''def _spec_sparkle_v2(shape, mask, seed, sm, M_field, R_field, CC_val=20.0):
    """Common spec builder for sparkle fusions."""
    M = np.clip(M_field * sm + M_field * (1 - sm) * 0.3, 0, 255)
    R = np.clip(R_field, 15, 255)
    CC = np.full(shape, CC_val, dtype=np.float32)
    cc_var = _noise(shape, [8, 16], [0.5, 0.5], seed + 300)
    CC = np.clip(CC + cc_var * 10 * sm, 16, 255)
    return _spec_out(shape, mask, M, R, CC)'''

    new_sparkle = '''def _spec_sparkle_v2(shape, mask, seed, sm, M_field, R_field, CC_val=20.0):
    """Common spec builder for sparkle fusions."""
    smf = float(sm)
    m_min, m_max = float(M_field.min()), float(M_field.max())
    m_span = m_max - m_min
    m_norm = (M_field - m_min) / m_span if m_span > 1e-5 else np.zeros_like(M_field)
    
    r_min, r_max = float(R_field.min()), float(R_field.max())
    r_span = r_max - r_min
    r_norm = (R_field - r_min) / r_span if r_span > 1e-5 else np.zeros_like(R_field)
    
    cc_noise = _noise(shape, [1, 2, 4], [0.45, 0.35, 0.20], seed + 999)
    cc_norm = np.clip((cc_noise + 1.0) * 0.5, 0.0, 1.0)
    cc_norm = np.clip(cc_norm * 0.4 + m_norm * 0.6, 0.0, 1.0)
    
    M = 15.0 + 240.0 * np.clip(m_norm * smf + (1.0 - smf) * (M_field / 255.0), 0.0, 1.0)
    R = 15.0 + 240.0 * np.clip(r_norm * smf + (1.0 - smf) * (R_field / 255.0), 0.0, 1.0)
    CC = 16.0 + 239.0 * np.clip(cc_norm * smf + (1.0 - smf) * (CC_val / 255.0), 0.0, 1.0)
    return _spec_out(shape, mask, M, R, CC)'''

    if orig_sparkle in content:
        content = content.replace(orig_sparkle, new_sparkle)
        print("Successfully replaced sparkle spec function!")
    else:
        print("ERROR: orig_sparkle not found!")

    # 2. Halo fusions overhaul
    orig_halo = '''    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        ds, sh, sw = _work_shape((h, w))
        dist, core, rim, glow, hair, trace, micro, satin = _halo_fields_cached(pattern_type, sh, sw, int(seed))
        chrome = np.clip(rim * (0.85 + 0.15 * style["edge"]) + hair * 0.35 + trace * 0.18, 0, 1)
        valley = np.clip(1.0 - core * 0.70 - rim * 0.35, 0, 1)
        M = np.clip(
            28.0
            + float(center_m) * core * 0.42
            + float(halo_m) * chrome * 0.88
            + micro * 70.0 * style["grain"] * sm
            + glow * 42.0 * sm,
            0,
            255,
        )
        G = np.clip(
            38.0
            + valley * (86.0 + float(base_g) * 0.42)
            + satin * 46.0
            - chrome * 58.0 * style["edge"]
            - micro * 34.0 * sm,
            15,
            255,
        )
        B = np.clip(
            42.0
            + glow * 112.0 * style["cc"]
            + rim * 86.0
            + core * float(base_cc) * 0.55
            + trace * 34.0
            + micro * 44.0 * sm,
            16,
            255,
        )'''

    new_halo = '''    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        ds, sh, sw = _work_shape((h, w))
        dist, core, rim, glow, hair, trace, micro, satin = _halo_fields_cached(pattern_type, sh, sw, int(seed))
        chrome = np.clip(rim * (0.85 + 0.15 * style["edge"]) + hair * 0.35 + trace * 0.18, 0, 1)
        valley = np.clip(1.0 - core * 0.70 - rim * 0.35, 0, 1)
        smf = float(sm)
        M_var = np.clip(core * 0.35 + chrome * 0.45 + glow * 0.20, 0.0, 1.0)
        G_var = np.clip(valley * 0.45 + satin * 0.35 + micro * 0.20, 0.0, 1.0)
        B_var = np.clip(glow * 0.40 + rim * 0.30 + core * 0.15 + trace * 0.15, 0.0, 1.0)
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * (float(halo_m) / 255.0), 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * (float(base_g) / 255.0), 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(B_var * smf + (1.0 - smf) * (float(base_cc) / 255.0), 0.0, 1.0)'''

    if orig_halo in content:
        content = content.replace(orig_halo, new_halo)
        print("Successfully replaced halo spec function!")
    else:
        print("ERROR: orig_halo not found!")

    # 3. Light wave overhaul
    orig_wave = '''    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        field, crest, micro, glint, edge = _lw_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M = base_m + (crest * 96.0 + glint * 118.0 + micro * 24.0) * smf
        G = rough_base + ((1.0 - field) * 50.0 + micro * 26.0 - glint * 42.0 - crest * 22.0) * smf
        B = clearcoat_base + (crest * 92.0 + glint * 126.0 + edge * 72.0 + micro * 18.0) * smf
        return _spec_out(shape, mask2, M, G, B)'''

    new_wave = '''    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        field, crest, micro, glint, edge = _lw_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        field_scaled = 0.5 + 0.5 * np.sin(field * np.pi * 3.0)
        M_var = np.clip(field_scaled * 0.4 + crest * 0.4 + glint * 0.2, 0.0, 1.0)
        G_var = np.clip((1.0 - field_scaled) * 0.4 + (1.0 - micro) * 0.3 + (1.0 - glint) * 0.3, 0.0, 1.0)
        B_var = np.clip(crest * 0.3 + glint * 0.4 + edge * 0.3, 0.0, 1.0)
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * (base_m / 255.0), 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * (rough_base / 255.0), 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(B_var * smf + (1.0 - smf) * (clearcoat_base / 255.0), 0.0, 1.0)
        return _spec_out(shape, mask2, M, G, B)'''

    if orig_wave in content:
        content = content.replace(orig_wave, new_wave)
        print("Successfully replaced wave spec function!")
    else:
        print("ERROR: orig_wave not found!")

    # 4. Spectral reactive overhaul
    orig_sr = '''    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        hue, band, micro, glint, edge = _sr_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M = float(m_low) + (float(m_high) - float(m_low)) * np.clip(hue * 0.58 + band * 0.42, 0, 1)
        M = M + (glint * 112.0 + edge * 54.0 + micro * 22.0) * smf
        G = float(rough_high) - (float(rough_high) - float(rough_low)) * np.clip(band * 0.70 + glint * 0.30, 0, 1)
        G = G + micro * 24.0 * smf - glint * 38.0 * smf
        B = float(clearcoat) + band * 80.0 * smf + glint * 124.0 * smf + edge * 60.0
        return _spec_out(shape, mask2, M, G, B)'''

    new_sr = '''    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        hue, band, micro, glint, edge = _sr_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M_var = np.clip(hue * 0.4 + band * 0.4 + glint * 0.2, 0.0, 1.0)
        G_var = np.clip((1.0 - band) * 0.4 + (1.0 - glint) * 0.4 + micro * 0.2, 0.0, 1.0)
        CC_var = np.clip(band * 0.3 + glint * 0.5 + edge * 0.2, 0.0, 1.0)
        M_base = ((float(m_low) + float(m_high)) / 2.0) / 255.0
        G_base = ((float(rough_low) + float(rough_high)) / 2.0) / 255.0
        B_base = float(clearcoat) / 255.0
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * M_base, 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * G_base, 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(CC_var * smf + (1.0 - smf) * B_base, 0.0, 1.0)
        return _spec_out(shape, mask2, M, G, B)'''

    if orig_sr in content:
        content = content.replace(orig_sr, new_sr)
        print("Successfully replaced spectral reactive spec function!")
    else:
        print("ERROR: orig_sr not found!")

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully wrote updated engine\\expansions\\fusions.py!")

    # Now copy fusions.py to the other two locations!
    dest1 = r"electron-app\server\engine\expansions\fusions.py"
    dest2 = r"electron-app\server\pyserver\_internal\engine\expansions\fusions.py"
    
    print(f"Syncing to {dest1}...")
    shutil.copyfile(target_path, dest1)
    
    print(f"Syncing to {dest2}...")
    shutil.copyfile(target_path, dest2)
    
    print("Fusions synced successfully to all three paths!")

if __name__ == "__main__":
    main()
