import subprocess
import gmsh
import numpy as np
import matplotlib.pyplot as plt

def run_case(h_gap):
    use_underfill = True
    L = 10.0
    W = 2.0
    h_fr4 = 0.8
    h_si = 0.2
    solder_radius = 0.15
    solder_x_positions = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    mesh_size = 0.15

    gmsh.initialize()
    gmsh.model.add("flip_chip_solder_bga")

    fr4 = gmsh.model.occ.addBox(0, 0, 0.0, L, W, h_fr4)
    si = gmsh.model.occ.addBox(0, 0, h_fr4 + h_gap, L, W, h_si)

    solder_cylinders = []
    for x_pos in solder_x_positions:
        cyl = gmsh.model.occ.addCylinder(x_pos, W / 2.0, h_fr4, 0, 0, h_gap, solder_radius)
        solder_cylinders.append((3, cyl))

    if use_underfill:
        uf_block = gmsh.model.occ.addBox(0, 0, h_fr4, L, W, h_gap)
        uf_cut, _ = gmsh.model.occ.cut([(3, uf_block)], solder_cylinders, removeTool=False)
        all_vols = [(3, fr4), (3, si)] + solder_cylinders + uf_cut
    else:
        all_vols = [(3, fr4), (3, si)] + solder_cylinders

    out, _ = gmsh.model.occ.fragment(all_vols[:1], all_vols[1:])
    gmsh.model.occ.synchronize()

    fr4_tags, si_tags, solder_tags, uf_tags = [], [], [], []
    for dim, tag in out:
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(dim, tag)
        z_mid = 0.5 * (zmin + zmax)
        if z_mid < h_fr4:
            fr4_tags.append(tag)
        elif z_mid > h_fr4 + h_gap:
            si_tags.append(tag)
        else:
            if (xmax - xmin) > 5.0:
                uf_tags.append(tag)
            else:
                solder_tags.append(tag)

    gmsh.model.addPhysicalGroup(3, fr4_tags, name="FR4_SUBSTRATE")
    gmsh.model.addPhysicalGroup(3, si_tags, name="SILICON_DIE")
    gmsh.model.addPhysicalGroup(3, solder_tags, name="SAC305_SOLDER")
    if use_underfill and uf_tags:
        gmsh.model.addPhysicalGroup(3, uf_tags, name="UNDERFILL_LAYER")

    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.model.mesh.generate(3)
    gmsh.write("mesh_only.inp")
    gmsh.finalize()

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

    subprocess.run(["ccx", "sim"], check=True)

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

    return warpage_um, max_solder_stress

gap_heights = [0.06, 0.08, 0.10, 0.12]
results = []

for h_gap in gap_heights:
    warpage, max_solder = run_case(h_gap)
    results.append((h_gap, warpage, max_solder))
    print(f"h_gap = {h_gap}, Warpage = {warpage:.2f} um, Max Solder Stress = {max_solder:.1f} MPa")

# Create summary table
print("\nSummary Table:")
print("h_gap (mm)\tWarpage (um)\tMax Solder Stress (MPa)")
for h_gap, warpage, max_solder in results:
    print(f"{h_gap:.2f}\t{warpage:.2f}\t\t{max_solder:.1f}")

# Plot gap_heights vs max_solder_stress
plt.plot([r[0] for r in results], [r[2] for r in results], marker='o')
plt.xlabel('Interconnect Gap Height (mm)')
plt.ylabel('Max SAC305 Solder Stress (MPa)')
plt.title('Max SAC305 Solder Stress vs Interconnect Gap Height')
plt.savefig('doe_gap_sweep.png')
plt.show()