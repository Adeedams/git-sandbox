import subprocess
import gmsh
import numpy as np

# ==========================================
# PARAMETERS & EXPERIMENT TOGGLE
# ==========================================
use_underfill = True  # <-- Flip between False (no underfill) and True (with underfill)!

L = 10.0          # Package length (mm)
W = 2.0           # Package width (mm)
h_fr4 = 0.8       # FR4 substrate thickness (mm)
h_gap = 0.1       # Interconnect gap height (mm)
h_si = 0.2        # Silicon die thickness (mm)

solder_radius = 0.15   # Radius of each SAC305 solder joint (mm)
solder_x_positions = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]  # 9 joints along X
mesh_size = 0.15       # Global mesh size (mm)

# ==========================================
# STAGE 0: OPEN THE LAB
# ==========================================
gmsh.initialize()
gmsh.model.add("flip_chip_solder_bga")

# ==========================================
# STAGE 1: GLUE (Build Solder Joints, Underfill, FR4, Silicon)
# ==========================================
fr4 = gmsh.model.occ.addBox(0, 0, 0.0, L, W, h_fr4)
si = gmsh.model.occ.addBox(0, 0, h_fr4 + h_gap, L, W, h_si)

# Create 9 cylindrical SAC305 solder columns centered along Y = W / 2
solder_cylinders = []
for x_pos in solder_x_positions:
    cyl = gmsh.model.occ.addCylinder(x_pos, W / 2.0, h_fr4, 0, 0, h_gap, solder_radius)
    solder_cylinders.append((3, cyl))

if use_underfill:
    # Create underfill block and punch holes where the solder joints sit
    uf_block = gmsh.model.occ.addBox(0, 0, h_fr4, L, W, h_gap)
    uf_cut, _ = gmsh.model.occ.cut([(3, uf_block)], solder_cylinders, removeTool=False)
    all_vols = [(3, fr4), (3, si)] + solder_cylinders + uf_cut
else:
    all_vols = [(3, fr4), (3, si)] + solder_cylinders

# Weld all touching faces so loads transfer across FR4 -> Solder/Underfill -> Silicon
out, _ = gmsh.model.occ.fragment(all_vols[:1], all_vols[1:])
gmsh.model.occ.synchronize()

# Identify volumes cleanly by their Z-center and volume size
fr4_tags, si_tags, solder_tags, uf_tags = [], [], [], []
for dim, tag in out:
    xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(dim, tag)
    z_mid = 0.5 * (zmin + zmax)
    if z_mid < h_fr4:
        fr4_tags.append(tag)
    elif z_mid > h_fr4 + h_gap:
        si_tags.append(tag)
    else:
        # Inside the 0.1 mm gap: underfill spans the full 10 mm length, solder joints are small
        if (xmax - xmin) > 5.0:
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
# STAGE 3: PIN (3-2-1 Kinematic Constraints)
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
n1 = min(all_node_ids, key=lambda i: (nodes[i][0]**2 + nodes[i][1]**2 + nodes[i][2]**2))
n2 = min(all_node_ids, key=lambda i: ((nodes[i][0] - L)**2 + nodes[i][1]**2 + nodes[i][2]**2))
n3 = min(all_node_ids, key=lambda i: (nodes[i][0]**2 + (nodes[i][1] - W)**2 + nodes[i][2]**2))

with open("nall.nam", "w") as f:
    f.write("*NSET, NSET=NALL\n")
    for i in range(0, len(all_node_ids), 10):
        f.write(", ".join(map(str, all_node_ids[i:i + 10])) + "\n")

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
{n1}, 1, 3, 0.0
{n2}, 2, 3, 0.0
{n3}, 3, 3, 0.0

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

print(f"Running solver (use_underfill = {use_underfill})...")
subprocess.run(["ccx", "sim"], check=True)

# ==========================================
# STAGE 5: CHECK (Warpage & Peak Solder Stress)
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

print(f"\n--- FLIP-CHIP BGA RESULTS (use_underfill = {use_underfill}) ---")
print(f"Package Warpage:         {warpage_um:.2f} microns")
print(f"Max SAC305 Solder Stress: {max_solder_stress:.1f} MPa")
