import numpy as np
import pyvista as pv

# 1. Read nodes from mesh_only.inp
node_ids, coords = [], []
with open("mesh_only.inp", "r") as f:
    in_nodes = False
    for line in f:
        if line.startswith("*NODE"):
            in_nodes = True
            continue
        if line.startswith("*"):
            in_nodes = False
        if in_nodes and line.strip():
            parts = [p.strip() for p in line.split(",")]
            node_ids.append(int(parts[0]))
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])

id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}
points = np.array(coords)

# 2. Read 3D tetrahedral elements and map element IDs
elem_ids, cells = [], []
with open("mesh_only.inp", "r") as f:
    in_elems = False
    for line in f:
        if line.startswith("*ELEMENT"):
            in_elems = True
            continue
        if line.startswith("*"):
            in_elems = False
        if in_elems and line.strip():
            parts = [int(p.strip()) for p in line.split(",")]
            elem_ids.append(parts[0])
            tet = [id_to_idx[n] for n in parts[1:5]]
            cells.append([4] + tet)

elem_to_idx = {eid: idx for idx, eid in enumerate(elem_ids)}
grid = pv.UnstructuredGrid(
    np.hstack(cells), np.full(len(cells), pv.CellType.TETRA, dtype=np.uint8), points
)

# 3. Read displacements (U) and elemental stresses (Sxx, Syy, Szz, Sxy, Sxz, Syz) from sim.dat
displacements = np.zeros_like(points)
elem_stresses = {eid: [] for eid in elem_ids}

with open("sim.dat", "r") as f:
    mode = None
    for line in f:
        if "displacements" in line:
            mode = "U"
            continue
        elif "stresses" in line:
            mode = "S"
            continue
        if line.strip():
            parts = line.split()
            if mode == "U" and len(parts) == 4 and parts[0].isdigit():
                idx = id_to_idx[int(parts[0])]
                displacements[idx] = [float(parts[1]), float(parts[2]), float(parts[3])]
            elif mode == "S" and len(parts) == 8 and parts[0].isdigit():
                eid = int(parts[0])
                if eid in elem_to_idx:
                    # Components: sxx, syy, szz, sxy, sxz, syz (columns 2 to 7)
                    s = [float(x) for x in parts[2:8]]
                    # Calculate von Mises stress formula
                    vm = np.sqrt(
                        0.5 * ((s[0] - s[1])**2 + (s[1] - s[2])**2 + (s[2] - s[0])**2)
                        + 3.0 * (s[3]**2 + s[4]**2 + s[5]**2)
                    )
                    elem_stresses[eid].append(vm)

# Average integration-point stress for each pyramid element
vm_array = np.zeros(len(elem_ids))
for eid, vals in elem_stresses.items():
    if vals:
        vm_array[elem_to_idx[eid]] = np.mean(vals)

grid.point_data["U"] = displacements
grid.cell_data["von_Mises_MPa"] = vm_array

# 4. Calculate warpage and plot
grid.point_data['Warpage_um'] = (displacements[:, 2] - np.min(displacements[:, 2])) * 1000.0
warped = grid.warp_by_vector("U", factor=15.0)
surface = warped.extract_surface()

plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(
    surface,
    scalars="Warpage_um",
    cmap="jet",
    clim=[0.0, 200.0],
    show_edges=True,
    edge_opacity=0.15,
    scalar_bar_args={"title": "Z-Warpage (microns)"},
)
plotter.add_axes()
plotter.add_text("Full 10mm x 10mm 64-Bump BGA 3D Warpage", font_size=12)
plotter.reset_camera()
plotter.screenshot("full_stack_warpage_3d.png")

print(f"Max von Mises Stress in Package: {np.max(vm_array):.1f} MPa")
print("Saved 3D warpage plot to full_stack_warpage_3d.png!")
