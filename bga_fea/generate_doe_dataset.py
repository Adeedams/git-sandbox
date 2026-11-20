import csv
import itertools
import subprocess
import gmsh
import numpy as np

# ==========================================
# DOE PARAMETER GRID (3 x 3 x 3 = 27 Runs)
# ==========================================
fr4_thicknesses = [0.6, 0.8, 1.0]          # mm
si_thicknesses = [0.15, 0.25, 0.35]        # mm
uf_moduli = [5000.0, 9000.0, 14000.0]      # MPa

# Fixed Quarter-Symmetry Package Dimensions
L_quarter = 5.0
W_quarter = 5.0
h_gap = 0.1
solder_radius = 0.15
grid_coords = [1.0, 2.0, 3.0, 4.0]
mesh_size = 0.25


def run_simulation(h_fr4, h_si, uf_modulus):
    """Runs one 3D quarter-symmetry BGA simulation and returns (warpage_um, max_solder_stress)."""
    # STAGE 0 & 1: OPEN & GLUE GEOMETRY
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("quarter_doe")

    fr4 = gmsh.model.occ.addBox(0, 0, 0.0, L_quarter, W_quarter, h_fr4)
    si = gmsh.model.occ.addBox(0, 0, h_fr4 + h_gap, L_quarter, W_quarter, h_si)

    solder_cylinders = []
    for x_pos in grid_coords:
        for y_pos in grid_coords:
            cyl = gmsh.model.occ.addCylinder(x_pos, y_pos, h_fr4, 0, 0, h_gap, solder_radius)
            solder_cylinders.append((3, cyl))

    uf_block = gmsh.model.occ.addBox(0, 0, h_fr4, L_quarter, W_quarter, h_gap)
    uf_cut, _ = gmsh.model.occ.cut([(3, uf_block)], solder_cylinders, removeTool=False)
    all_vols = [(3, fr4), (3, si)] + solder_cylinders + uf_cut

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
            if (xmax - xmin) > 2.5:
                uf_tags.append(tag)
            else:
                solder_tags.append(tag)

    gmsh.model.addPhysicalGroup(3, fr4_tags, name="FR4_SUBSTRATE")
    gmsh.model.addPhysicalGroup(3, si_tags, name="SILICON_DIE")
    gmsh.model.addPhysicalGroup(3, solder_tags, name="SAC305_SOLDER")
    gmsh.model.addPhysicalGroup(3, uf_tags, name="UNDERFILL_LAYER")

    # STAGE 2: MESH
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.model.mesh.generate(3)
    gmsh.write("mesh_only.inp")
    gmsh.finalize()

    # STAGE 3: PIN (Mirror Symmetry Walls)
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

    # STAGE 4: HEAT / COOL (Physics Deck & Solve)
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

*MATERIAL, NAME=UNDERFILL
*ELASTIC
{uf_modulus}, 0.30
*EXPANSION, ZERO=250.0
30.0E-6

*SOLID SECTION, ELSET=FR4_SUBSTRATE, MATERIAL=FR4
*SOLID SECTION, ELSET=SILICON_DIE, MATERIAL=SILICON
*SOLID SECTION, ELSET=SAC305_SOLDER, MATERIAL=SAC305
*SOLID SECTION, ELSET=UNDERFILL_LAYER, MATERIAL=UNDERFILL

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
*END STEP
"""

    with open("sim.inp", "w") as f:
        f.write(physics_deck)

    subprocess.run(["ccx", "sim"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # STAGE 5: CHECK RESULTS
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
    max_solder_stress = max(solder_vm_stresses)
    return warpage_um, max_solder_stress


# ==========================================
# MAIN DOE LOOP & CSV EXPORT
# ==========================================
combinations = list(itertools.product(fr4_thicknesses, si_thicknesses, uf_moduli))
csv_filename = "bga_doe_dataset.csv"

print(f"Starting 27-run Multi-Parameter DOE Sweep -> {csv_filename}\n")
print(f"{'Run':<5} | {'h_fr4':<7} | {'h_si':<7} | {'E_uf (MPa)':<11} | {'Warpage (um)':<13} | {'Max Stress (MPa)'}")
print("-" * 72)

with open(csv_filename, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["h_fr4_mm", "h_si_mm", "uf_modulus_MPa", "warpage_um", "max_solder_stress_MPa"])

    for idx, (h_fr4, h_si, uf_mod) in enumerate(combinations, start=1):
        warpage, stress = run_simulation(h_fr4, h_si, uf_mod)
        writer.writerow([h_fr4, h_si, uf_mod, round(warpage, 3), round(stress, 2)])
        print(f"{idx:02d}/27 | {h_fr4:<7.2f} | {h_si:<7.2f} | {uf_mod:<11.1f} | {warpage:<13.2f} | {stress:.1f}")

print(f"\nDone! Saved all 27 simulation rows to {csv_filename}.")
