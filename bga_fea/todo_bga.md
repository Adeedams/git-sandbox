# BGA Thermomechanical FEA Roadmap

## Completed
- [x] Validate 2-layer Silicon/FR4 warpage against Timoshenko theory (run_warpage.py)
- [x] Model 3-layer stack with 0.1 mm underfill cushion (run_3layer.py)
- [x] Build 9-bump SAC305 Flip-Chip BGA with underfill toggle (run_solder_bga.py)
- [x] Plot centerline cross-section showing Distance to Neutral Point (plot_cross_section.py)
- [x] Run automated DOE sweep over gap heights (run_doe_sweep.py)
- [x] Document workflow in README.md and push to GitHub

## Up Next
- [ ] Upgrade mesh to 2nd-order quadratic tetrahedrons (C3D10) for smoother stress contours
- [ ] Build a 2D BGA solder ball array using quarter-symmetry (X=0 and Y=0 planes)
- [ ] Add temperature-dependent FR4 properties above Glass Transition Temperature (Tg)
- [ ] Export a multi-parameter DOE sweep to CSV
- [ ] Train a PyTorch AI surrogate model on the CSV dataset for instant warpage prediction
