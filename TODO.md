# Shokker Paint Booth - Active Tasks

## 🛑 Critical Path (Integration)
- [ ] **Create `server.py`:** A lightweight Flask server to expose `shokker_engine_v2` functions as API endpoints.
- [ ] **Update Web UI:** Modify the JavaScript in PaintVault/PaintBooth to call the local server API instead of generating download files.
- [ ] **Test Loop:** Verify that a change in the Web UI triggers a render in the Python backend and updates the view.

## 🧠 Engine Improvements (Python)
- [ ] **Refine Color Masking:** Tune the HSV thresholds in `shokker_engine_v2.py` for better accuracy on dark/muddy textures.
- [ ] **Performance:** Optimize image loading/saving to speed up the "Preview" generation.

## 🖥️ UI/UX Polish
- [ ] **Unified Dashboard:** Sketch out a wireframe combining the AI Analysis and Zone Designer views.
- [ ] **Zone visualizer:** Add a way to "paint" or tweak zones manually if the AI gets it wrong.

## 📝 Documentation
- [x] Create ROADMAP.md
- [x] Create TODO.md
- [ ] Create README.md (General overview)
