# Shokker Paint Booth - Project Roadmap

**Mission:** Transform the current collection of tools (Python engine, Web UI, AI analysis) into a unified, sellable desktop application for iRacing painters.

## 🚧 Phase 1: Integration (The Bridge)
*Goal: Connect the Web UI to the Python "Brain" so users can apply finishes without manual script running.*

- [ ] **Architecture Decision:** Select integration method.
    - *Recommendation:* Local Flask/FastAPI server. This runs locally on the user's machine, listening for requests from the Web UI. It keeps the heavy image processing in Python (where it already works) without needing a rewrite.
- [ ] **API Layer:** Create `server.py` (new file) to wrap `shokker_engine_v2.py`.
    - Endpoint: `/apply-finish` (Accepts JSON zone data, returns processed image path).
    - Endpoint: `/preview` (Fast low-res preview).
- [ ] **UI Connection:** Update `PaintVault` (or `paint-booth-v2`) to send fetch requests to `http://localhost:5000` instead of downloading `.py` files.

## 🎨 Phase 2: The Unified Interface (UI/UX)
*Goal: Create a customer-ready experience, moving away from "dev tools" vibes.*

- [ ] **Merge Tools:** Consolidate `PaintVault` (AI Analysis) and `paint-booth-v2` (Zone Designer) into a single dashboard.
    - Tab 1: "Analyze" (Upload screenshots, get AI zone suggestions).
    - Tab 2: "Design" (Apply finishes to those zones).
    - Tab 3: "Export" (Generate TGA).
- [ ] **Live Preview:** Implement a basic visualizer in the Web UI so users see an approximation of the finish before the full Python render.

## 📦 Phase 3: Productization
*Goal: Package it for sale.*

- [ ] **Packaging:** Use PyInstaller or Electron-Builder to bundle the Python engine and Web UI into a single `.exe` installer.
- [ ] **Licensing:** Add a simple license key check on startup.
- [ ] **Docs:** User manual and installation guide.

## 🚀 Future Features (Post-Launch)
- [ ] Cloud syncing for saved projects.
- [ ] Community library for shared finish presets.
