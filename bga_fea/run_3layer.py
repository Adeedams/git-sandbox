import subprocess
import gmsh

# ==========================================
# PARAMETERS (Define once, use everywhere)
# ==========================================
L = 10.0  # Package length (mm)
W = 2.0  # Package width (mm)
h_fr4 = 0.8  # FR4 substrate thickness (mm)
h_uf = 0.1  # Underfill layer thickness (mm)
h_si = 0.2  # Silicon die thickness (mm)
mesh_size = 0.15  # Smaller mesh so at least 1-2 elements fit across the 0.1 mm layer

# ==========================================
# STAGE 0: OPEN THE LAB
# ==========================================
gmsh.initialize()
gmsh.model.add("three_layer_package")

# ==========================================
# STAGE 1: GLUE (Stack & Weld 3 Layers)
# ==========================================
fr4 = gmsh.model.occ.addBox(0, 0, 0.0, L, W, h_fr4)
uf = gmsh.model.occ.addBox(0, 0, h_fr4, L, W, h_uf)
si = gmsh.model.occ.addBox(0, 0, h_fr4 + h_uf, L, W, h_si)

# Weld all 3 volumes together so they share nodes at z=0.8 and z=0.9
out, _ = gmsh.model.occ.fragment([(3, fr4)], [(3, uf), (3, si)])
gmsh.model.occ.synchronize()

# Assign physical volume names in exact creation order: [0]=FR4, [1]=Underfill, [2]=Silicon
gmsh.model.addPhysicalGroup(3, [out[0][1]], name="FR4_SUBSTRATE")
gmsh.model.addPhysicalGroup(3, [out[1][1]], name="UNDERFILL_LAYER")
gmsh.model.addPhysicalGroup(3, [out[2][1]], name="SILICON_DIE")

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
physics_deck = f"""*INCLUDE, INPUT=mesh_only.inp
*INCLUDE, INPUT=nall.nam

*MATERIAL, NAME=FR4
*ELASTIC
18000.0, 0.28
*EXPANSION, ZERO=250.0
16.0E-6

*MATERIAL, NAME=UNDERFILL
*ELASTIC
8500.0, 0.30
*EXPANSION, ZERO=250.0
30.0E-6

*MATERIAL, NAME=SILICON
*ELASTIC
130000.0, 0.28
*EXPANSION, ZERO=250.0
2.6E-6

*SOLID SECTION, ELSET=FR4_SUBSTRATE, MATERIAL=FR4
*SOLID SECTION, ELSET=UNDERFILL_LAYER, MATERIAL=UNDERFILL
*SOLID SECTION, ELSET=SILICON_DIE, MATERIAL=SILICON

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
*EL PRINT, ELSET=SILICON_DIE
S
*EL PRINT, ELSET=UNDERFILL_LAYER
S
*EL PRINT, ELSET=FR4_SUBSTRATE
S
*END STEP
"""

with open("sim.inp", "w") as f:
    f.write(physics_deck)

print("Running 3-layer CalculiX solver...")
subprocess.run(["ccx", "sim"], check=True)

# ==========================================
# STAGE 5: CHECK (Read Warpage Results)
# ==========================================
z_displacements = []
with open("sim.dat", "r") as f:
    reading = False
    for line in f:
        if "displacements" in line:
            reading = True
            continue
        elif "stresses" in line:
            reading = False
        if reading and line.strip():
            parts = line.split()
            if len(parts) == 4 and parts[0].isdigit():
                z_displacements.append(float(parts[3]))

warpage_mm = max(z_displacements) - min(z_displacements)

print(f"\n--- 3-LAYER RESULTS ---")
print(f"3-Layer FEA Warpage (with 0.1 mm Underfill): {warpage_mm * 1000:.2f} microns")
print(f"Previous 2-Layer Baseline Warpage:           53.75 microns")