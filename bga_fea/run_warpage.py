import subprocess
import gmsh

# 1. Initialize Gmsh and build a 3D two-layer strip (10mm x 2mm)
gmsh.initialize()
gmsh.model.add("silicon_fr4_strip")

# Bottom layer: FR4 substrate (0.8 mm thick, z from 0 to 0.8)
fr4 = gmsh.model.occ.addBox(0, 0, 0, 10.0, 2.0, 0.8)
# Top layer: Silicon die (0.2 mm thick, z from 0.8 to 1.0)
si = gmsh.model.occ.addBox(0, 0, 0.8, 10.0, 2.0, 0.2)

# Glue the shared interface so nodes match seamlessly
out, _ = gmsh.model.occ.fragment([(3, fr4)], [(3, si)])
gmsh.model.occ.synchronize()

# Assign volume groups so CalculiX knows which part is FR4 vs Silicon
gmsh.model.addPhysicalGroup(3, [out[0][1]], name="FR4_SUBSTRATE")
gmsh.model.addPhysicalGroup(3, [out[1][1]], name="SILICON_DIE")

# Export ONLY physical 3D volume elements (prevents 1D/2D element errors in ccx)
gmsh.option.setNumber("Mesh.SaveAll", 0)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.25)
gmsh.model.mesh.generate(3)

gmsh.write("mesh_only.inp")
gmsh.finalize()

# 2. Extract all node IDs from mesh_only.inp so we can create NALL and pin 3 corners
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
# Pick 3 non-collinear nodes on z=0 to prevent rigid-body floating without restricting bending
n1 = min(all_node_ids, key=lambda i: (nodes[i][0]**2 + nodes[i][1]**2 + nodes[i][2]**2))
n2 = min(all_node_ids, key=lambda i: ((nodes[i][0]-10.0)**2 + nodes[i][1]**2 + nodes[i][2]**2))
n3 = min(all_node_ids, key=lambda i: (nodes[i][0]**2 + (nodes[i][1]-2.0)**2 + nodes[i][2]**2))

# Write NALL node set file
with open("nall.nam", "w") as f:
    f.write("*NSET, NSET=NALL\n")
    for i in range(0, len(all_node_ids), 10):
        f.write(", ".join(map(str, all_node_ids[i:i+10])) + "\n")

# 3. Write the CalculiX physics & thermal load deck
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

*SOLID SECTION, ELSET=FR4_SUBSTRATE, MATERIAL=FR4
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
*NODE FILE
U
*EL FILE
S
*EL PRINT, ELSET=SILICON_DIE
S
*EL PRINT, ELSET=FR4_SUBSTRATE
S
*END STEP
"""

with open("sim.inp", "w") as f:
    f.write(physics_deck)

# 4. Run the CalculiX solver
print("Running CalculiX solver...")
subprocess.run(["ccx", "sim"], check=True)

# 5. Read displacements from sim.dat and compute warpage (peak-to-valley Z)
z_displacements = []
with open("sim.dat", "r") as f:
    reading = False
    for line in f:
        if "displacements" in line:
            reading = True
            continue
        if reading and line.strip():
            parts = line.split()
            if len(parts) == 4 and parts[0].isdigit():
                z_displacements.append(float(parts[3]))

warpage_mm = max(z_displacements) - min(z_displacements)

# 6. Compare with Timoshenko bi-material thermostat equation
L = 10.0  # length (mm)
dT = 25.0 - 250.0  # temperature change (-225 C)
E1, h1, a1 = 18000.0, 0.8, 16.0e-6  # FR4
E2, h2, a2 = 130000.0, 0.2, 2.6e-6  # Silicon
h = h1 + h2
m = h1 / h2
n = E1 / E2

curvature = (6 * (a2 - a1) * dT * (1 + m) ** 2) / (
    h * (3 * (1 + m) ** 2 + (1 + m * n) * (m**2 + 1 / (m * n)))
)
timoshenko_warpage_mm = abs(curvature) * (L**2) / 8.0

print(f"\n--- RESULTS ---")
print(f"3D FEA Simulated Warpage:   {warpage_mm * 1000:.2f} microns")
print(f"Timoshenko Analytical Math: {timoshenko_warpage_mm * 1000:.2f} microns")
