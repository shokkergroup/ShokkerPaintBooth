# Shokker Paint Booth

**The ultimate finish applicator and paint manager for iRacing.**

## Project Structure

### 🧠 The Brain: `shokker_engine_v2.py`
The core logic engine.
- **Capabilities:** Color-based zone detection, multi-zone masking, 20+ specialized finishes (Holographic, Carbon, Chrome, Anodized).
- **Input:** TGA textures, JSON zone definitions.
- **Output:** Processed TGA spec maps and textures ready for iRacing.

### 👁️ The Eyes: `PaintVault` (Web)
The analysis and organization frontend.
- **Capabilities:** Uses AI vision (Claude/GPT-4V) to analyze car screenshots and identify paint schemes.
- **Current State:** Standalone web app. Needs integration with the Engine.

### 🎨 The Brush: `paint-booth-v2.html` (Web)
The designer interface.
- **Capabilities:** Visual zone selection and finish assignment.
- **Current State:** Generates Python scripts for manual execution.

## The Goal
Unify these three components into a single, seamless desktop application. The user should be able to:
1.  Drop in a car paint file.
2.  Use AI to auto-detect zones (Hood, Side, Numbers).
3.  Apply specialized finishes (e.g., "Make the numbers Holographic") via UI.
4.  Export the final TGA directly to iRacing.

## Development Rules
*   **NEVER DELETE:** Do not delete existing files. Create `_v2`, `_new`, or distinct filenames for iterations.
*   **Focus:** Integration and Productization.
