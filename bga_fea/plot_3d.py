import numpy as np
import pyvista as pv

# 1. Read 3D node coordinates from mesh_only.inp
node_ids = []
coords = []
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

# 2. Read 3D tetrahedral elements from mesh_only.inp
cells = []
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
            # C3D4 tetrahedron has 4 corner nodes
            tet = [id_to_idx[n] for n in parts[1:5]]
            cells.append([4] + tet)

cells_flat = np.hstack(cells)
cell_types = np.full(len(cells), pv.CellType.TETRA, dtype=np.uint8)
grid = pv.UnstructuredGrid(cells_flat, cell_types, points)

# 3. Read solved displacements (Ux, Uy, Uz) from sim.dat
displacements = np.zeros_like(points)
with open("sim.dat", "r") as f:
    reading = False
    for line in f:
        if "displacements" in line:
            reading = True
            continue
        if reading and line.strip():
            parts = line.split()
            if len(parts) == 4 and parts[0].isdigit():
                idx = id_to_idx[int(parts[0])]
                displacements[idx] = [
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                ]

grid.point_data["U"] = displacements
grid.point_data["Warpage_Z_microns"] = displacements[:, 2] * 1000.0

# 4. Magnify bending by 30x so you can clearly see the "potato chip" curl
warped = grid.warp_by_vector("U", factor=30.0)

# Save a PNG image automatically AND open an interactive 3D window
plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(
    warped,
    scalars="Warpage_Z_microns",
    cmap="turbo",
    show_edges=True,
    scalar_bar_args={"title": "Z Warpage (microns)"},
)
plotter.add_axes()
plotter.add_text("3D Silicon/FR4 Warpage (30x Magnified)", font_size=12)
plotter.screenshot("warpage_3d.png")
print("Success! Open warpage_3d.png in your VS Code sidebar to view the 3D plot.")
