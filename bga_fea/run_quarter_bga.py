import subprocess
import gmsh
import numpy as np

# ==========================================
# PARAMETERS (Quarter of a 10mm x 10mm Square Chip)
# ==========================================
use_underfill = True   # Compare True vs False later!
L_quarter = 5.0        # Half-length of 10 mm chip (mm)
W_quarter = 5.0        # Half-width of 10 mm chip (mm)
h_fr4 = 0.8            # FR4 substrate thickness (mm)
h_gap = 0.1            # Solder & underfill gap thickness (mm)
h_si = 0.2             # Silicon die thickness (mm)

solder_radius = 0.15   # Radius of each SAC305 solder joint (mm)
grid_coords = [1.0, 2.0, 3.0, 4.0]  # 4x4 = 16 joints in this quarter (64 total on full chip!)
mesh_size = 0.25       # Balanced mesh size so 16 solder joints solve in ~5 seconds

# ==========================================
# STAGE 0: OPEN THE LAB
# ==========================================
gmsh.initialize()
gmsh.model.add("quarter_symmetry_bga")

# ==========================================
# STAGE 1: GLUE (2D Grid of 16 Solder Columns + Underfill + FR4 + Silicon)
# ==========================================
fr4 = gmsh.model.occ.addBox(0, 0, 0.0, L_quarter, W_quarter, h_fr4)
si = gmsh.model.occ.addBox(0, 0, h_fr4 + h_gap, L_quarter, W_quarter, h_si)

# Nested loop creates a 2D 4x4 checkerboard grid of 16 solder joints!
solder_cylinders = []
for x_pos in grid_coords:
    for y_pos in grid_coords:
        cyl = gmsh.model.occ.addCylinder(x_pos, y_pos, h_fr4, 0, 0, h_gap, solder_radius)
        solder_cylinders.append((3, cyl))

if use_underfill:
    uf_block = gmsh.model.occ.addBox(0, 0, h_fr4, L_quarter, W_quarter, h_gap)
    uf_cut, _ = gmsh.model.occ.cut([(3, uf_block)], solder_cylinders, removeTool=False)
    all_vols = [(3, fr4), (3, si)] + solder_cylinders + uf_cut
else:
    all_vols = [(3, fr4), (3, si)] + solder_cylinders

out, _ = gmsh.model.occ.fragment(all_vols[:1], all_vols[1:])
gmsh.model.occ.synchronize()

# Tag volumes by Z-height and X-span
fr4_tags, si_tags, solder_tags, uf_tags = [], [], [], []
for dim, tag in out:
    xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(dim, tag)
    z_mid = 0.5 * (zmin + zmax)
    if z_mid < h_fr4:
        fr4_tags.append(tag)
    elif z_mid > h_fr4 + h_gap:
        si_tags.append(tag)
    else:
        if (xmax - xmin) > 2.5:
            uf_tags.append(tag)
        else:
            solder_tags.append(tag)

gmsh.model.addPhysicalGroup(3, fr4_tags, name="FR4_SUBSTRATE")
gmsh.model.addPhysicalGroup(3, si_tags, name="SILICON_DIE")
gmsh.model.addPhysicalGroup(3, solder_tags, name="SAC305_SOLDER")
if use_underfill and uf_tags:
    gmsh.model.addPhysicalGroup(3, uf_tags, name="UNDERFILL_LAYER")

# ==========================================
# STAGE 2: MESH (Slice Into 3D Pyramids)
# ==========================================
gmsh.option.setNumber("Mesh.SaveAll", 0)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
gmsh.model.mesh.generate(3)
gmsh.write("mesh_only.inp")
gmsh.finalize()
# ==========================================
# STAGE 3: PIN (Quarter-Symmetry Mirror Walls)
# ==========================================
nodes = {}
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
            nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))

all_node_ids = sorted(nodes.keys())

# Find all nodes on the X=0 mirror wall and Y=0 mirror wall
sym_x_nodes = [nid for nid, (x, y, z) in nodes.items() if abs(x) < 1e-5]
sym_y_nodes = [nid for nid, (x, y, z) in nodes.items() if abs(y) < 1e-5]
n_center = min(all_node_ids, key=lambda i: (nodes[i][0]**2 + nodes[i][1]**2 + nodes[i][2]**2))

with open("nall.nam", "w") as f:
    f.write("*NSET, NSET=NALL\n")
    for i in range(0, len(all_node_ids), 10):
        f.write(", ".join(map(str, all_node_ids[i:i + 10])) + "\n")

    f.write("*NSET, NSET=SYM_X\n")
    for i in range(0, len(sym_x_nodes), 10):
        f.write(", ".join(map(str, sym_x_nodes[i:i + 10])) + "\n")

    f.write("*NSET, NSET=SYM_Y\n")
    for i in range(0, len(sym_y_nodes), 10):
        f.write(", ".join(map(str, sym_y_nodes[i:i + 10])) + "\n")

# ==========================================
# STAGE 4: HEAT / COOL (Physics Deck & Solve)
# ==========================================
uf_material_block = """
*MATERIAL, NAME=UNDERFILL
*ELASTIC
8500.0, 0.30
*EXPANSION, ZERO=250.0
30.0E-6
*SOLID SECTION, ELSET=UNDERFILL_LAYER, MATERIAL=UNDERFILL
""" if use_underfill else ""

uf_print_block = """*EL PRINT, ELSET=UNDERFILL_LAYER
S
""" if use_underfill else ""

physics_deck = f"""*INCLUDE, INPUT=mesh_only.inp
*INCLUDE, INPUT=nall.nam

*MATERIAL, NAME=FR4
*ELASTIC
18000.0, 0.28
*EXPANSION, ZERO=250.0
16.0E-6

*MATERIAL, NAME=SILICON
*ELASTIC
130000.0, 0.28
*EXPANSION, ZERO=250.0
2.6E-6

*MATERIAL, NAME=SAC305
*ELASTIC
50000.0, 0.35
*EXPANSION, ZERO=250.0
21.5E-6

*SOLID SECTION, ELSET=FR4_SUBSTRATE, MATERIAL=FR4
*SOLID SECTION, ELSET=SILICON_DIE, MATERIAL=SILICON
*SOLID SECTION, ELSET=SAC305_SOLDER, MATERIAL=SAC305
{uf_material_block}
*BOUNDARY
SYM_X, 1, 1, 0.0
SYM_Y, 2, 2, 0.0
{n_center}, 3, 3, 0.0

*INITIAL CONDITIONS, TYPE=TEMPERATURE
NALL, 250.0

*STEP
*STATIC
*TEMPERATURE
NALL, 25.0
*NODE PRINT, NSET=NALL
U
*EL PRINT, ELSET=SAC305_SOLDER
S
*EL PRINT, ELSET=SILICON_DIE
S
*EL PRINT, ELSET=FR4_SUBSTRATE
S
{uf_print_block}*END STEP
"""

with open("sim.inp", "w") as f:
    f.write(physics_deck)

print(f"Running Quarter-Symmetry 2D Array solver (16 joints = 64-bump full chip)...")
subprocess.run(["ccx", "sim"], check=True)

# ==========================================
# STAGE 5: CHECK (Warpage & Peak Diagonal Corner Solder Stress)
# ==========================================
z_displacements = []
solder_vm_stresses = []

with open("sim.dat", "r") as f:
    mode = None
    current_set = ""
    for line in f:
        if "displacements" in line:
            mode = "U"
            continue
        elif "stresses" in line:
            mode = "S"
            current_set = "SAC305" if "SAC305_SOLDER" in line else "OTHER"
            continue
        parts = line.split()
        if not parts:
            continue
        if mode == "U" and len(parts) == 4 and parts[0].isdigit():
            z_displacements.append(float(parts[3]))
        elif mode == "S" and current_set == "SAC305" and len(parts) == 8 and parts[0].isdigit():
            sxx, syy, szz, sxy, sxz, syz = [float(x) for x in parts[2:8]]
            vm = np.sqrt(
                0.5 * ((sxx - syy)**2 + (syy - szz)**2 + (szz - sxx)**2)
                + 3.0 * (sxy**2 + sxz**2 + syz**2)
            )
            solder_vm_stresses.append(vm)

warpage_um = (max(z_displacements) - min(z_displacements)) * 1000.0
max_solder_stress = max(solder_vm_stresses) if solder_vm_stresses else 0.0

print(f"\n--- QUARTER-SYMMETRY 64-BUMP BGA RESULTS (use_underfill = {use_underfill}) ---")
print(f"2D Square Package Warpage:    {warpage_um:.2f} microns")
print(f"Max Diagonal Corner Stress:   {max_solder_stress:.1f} MPa")
