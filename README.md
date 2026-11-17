Here is your complete, beginner-friendly Master Study Guide covering everything you built, every terminal command you ran, the physics behind your results, and the exact Python scripts you now have in your portfolio.

Part 1: Every Bash / Terminal Command You Learned

Think of the terminal as a text-based remote control for your computer. Here is every command you used, grouped by what it does.

1. Moving Around & Managing Files

• mkdir bga_fea: Creates a new folder named bga_fea.
• cd bga_fea: Moves your terminal inside the bga_fea folder (cd .. moves one folder back up).
• ls: Lists all files and folders inside your current folder.
• touch file.py: Creates a brand-new, empty file named file.py.
• code file.py: Opens file.py directly inside a VS Code editor tab.
• cp file1.py file2.py: Copies file1.py into a brand-new file named file2.py.
• mv file.py folder/: Moves file.py into folder/.
• rmdir folder: Deletes an empty folder.

2. Chaining Commands Together

• && (e.g., cd bga_fea && python3 script.py): Means "and then, only if the first step worked."
• ;: Means "and then, run the next step no matter what."

3. Python Virtual Environments & Packages

• python3 -m venv venv: Creates a private, isolated box (venv) so your project's Python tools do not mess up the rest of your computer.
• source venv/bin/activate: Turns your private venv box on. You know it is on when (venv) appears at the left side of your terminal line.
• pip install gmsh pyvista numpy matplotlib: Installs the four helper libraries your scripts need into your active (venv).
• python3 script.py: Runs your Python script from top to bottom.

4. Installing & Running Engineering & AI Tools

• sudo apt update: Asks Ubuntu (with administrator password sudo) to refresh its catalog of free software.
• sudo apt install -y calculix-ccx gmsh: Installs the CalculiX physics solver (ccx) and the Gmsh 3D builder (gmsh).
• ccx sim: Runs the CalculiX physics solver on sim.inp (never type the .inp extension).
• ollama list: Shows which local AI models are downloaded on your machine.
• ollama pull qwen2.5-coder:7b: Downloads the 7-billion-parameter Qwen coding AI onto your computer.

5. Saving Your Work to GitHub (Version Control)

• git status: Checks which files were added or changed since your last save.
• git add .: Selects all new and updated files (while automatically skipping files listed in .gitignore).
• git commit -m "message": Takes a permanent, labeled snapshot of your project.
• git push: Uploads your saved snapshot to GitHub.
• git checkout -- file.py: Undoes accidental changes to file.py and restores your last saved Git version.

Part 2: The Physics Behind What You Built (In Plain English)

Every simulation you ran modeled reflow cooling—what happens inside a microchip after molten solder freezes at 250°C and cools down to room temperature (25°C).

1. Why Materials Fight Each Other (CTE Mismatch)

• Every material shrinks when cooled. How much it shrinks is called its Coefficient of Thermal Expansion (CTE).
• FR4 (the circuit board) has a high CTE (16 ppm/°C), so it wants to shrink 6 times more than Silicon (the computer chip), which barely shrinks (2.6 ppm/°C).
• Because the two layers are glued together, the shrinking FR4 pulls inward on the bottom of the Silicon, forcing the flat chip to curl into a dome shape (warpage).

2. Why Stress Builds Up (Stiffness / Young's Modulus)

• Silicon is over 7 times stiffer (130,000 MPa) than FR4 (18,000 MPa).
• When a stiff material and a stretchy material are forced to bend together, internal pulling and pushing forces (von Mises stress) build up along the glued seam. If stress gets too high, the chip cracks or peels apart (delamination).

3. What Your Four Experiments Proved

1. 2-Layer Strip (run_warpage.py): Bare Silicon glued straight onto FR4 curled by 53.75 microns (matching the 1925 Timoshenko textbook formula of 55.06 microns within 2.4%) and created a dangerous 837.0 MPa corner stress spike.
2. 3-Layer Cushioned Stack (run_3layer.py): Inserting a soft 0.1 mm epoxy underfill layer (8,500 MPa) between the Silicon and FR4 acted like a shock absorber—dropping peak stress by 80% (down to 172.4 MPa).
3. Flip-Chip BGA With 9 Solder Balls (run_solder_bga.py): Adding 9 discrete SAC305 solder columns proved why underfill is mandatory in real chips:
	• Without underfill (False): Peak solder stress hit 503 MPa.
	• With underfill (True): Peak solder stress dropped by 40% down to 302 MPa.
4. Centerline Cutaway & Gap Sweep (plot_cross_section.py & run_doe_sweep.py):
	• Slicing down the middle showed the Distance to Neutral Point (DNP) effect—the center solder ball stays calm, while the outermost edge solder balls take the highest stress.
	• Sweeping the gap height (0.06 mm to 0.12 mm) proved that taller solder joints flex more easily and reduce peak solder stress (312.7 MPa → 302.3 MPa).

Part 3: Your 6-Stage Mental Blueprint (O – G – M – P – H – C)

Every single simulation script you wrote follows the exact same 6 steps in order. Memory sentence: "Old Gears Make Parts Hot Carefully."
1. O — Open the Lab: Bring in your Python helpers (import gmsh, subprocess, numpy) and turn on the 3D drafting engine (gmsh.initialize()).
2. G — Glue (Geometry): Draw your stacked 3D boxes and cylinders (addBox, addCylinder), weld touching faces together (fragment), and put name tags on each material (addPhysicalGroup).
3. M — Mesh: Chop the 3D shapes into tiny pyramids (generate(3)), save only the tagged volumes (Mesh.SaveAll = 0) to mesh_only.inp, and shut down Gmsh (finalize()).
4. P — Pin (Boundary Conditions): Lock 3 bottom corners (n1, n2, n3) using a 3-2-1 constraint so the chip cannot float or spin away in space, while still shrinking and bending freely.
5. H — Heat / Cool (Physics Deck): Write sim.inp with consistent mm–N–MPa material rules (*ELASTIC, *EXPANSION), cool from 250°C to 25°C, and run subprocess.run(["ccx", "sim"]).
6. C — Check (Post-Processing): Read sim.dat to calculate warpage (max - min) and von Mises stress, then render 3D plots with PyVista.

Part 4: Your Complete Working Code Library

Here are your four core scripts so you have them all in one clean reference place.

Script 1: run_warpage.py (Validated 2-Layer Baseline)

python
import subprocess
import gmsh

# 0. Open the lab
gmsh.initialize()
gmsh.model.add("silicon_fr4_strip")

# 1. Glue (Bottom FR4 = 0.8 mm, Top Silicon = 0.2 mm)
fr4 = gmsh.model.occ.addBox(0, 0, 0, 10.0, 2.0, 0.8)
si = gmsh.model.occ.addBox(0, 0, 0.8, 10.0, 2.0, 0.2)
out, _ = gmsh.model.occ.fragment([(3, fr4)], [(3, si)])
gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [out], name="FR4_SUBSTRATE")
gmsh.model.addPhysicalGroup(3, [out], name="SILICON_DIE")

# 2. Mesh
gmsh.option.setNumber("Mesh.SaveAll", 0)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.25)
gmsh.model.mesh.generate(3)
gmsh.write("mesh_only.inp")
gmsh.finalize()

# 3. Pin (3-2-1 corner constraints)
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
            nodes[int(parts)] = (float(parts), float(parts), float(parts))

all_node_ids = sorted(nodes.keys())
n1 = min(all_node_ids, key=lambda i: (nodes[i]**2 + nodes[i]**2 + nodes[i]**2))
n2 = min(all_node_ids, key=lambda i: ((nodes[i] - 10.0)**2 + nodes[i]**2 + nodes[i]**2))
n3 = min(all_node_ids, key=lambda i: (nodes[i]**2 + (nodes[i] - 2.0)**2 + nodes[i]**2))

with open("nall.nam", "w") as f:
    f.write("*NSET, NSET=NALL\n")
    for i in range(0, len(all_node_ids), 10):
        f.write(", ".join(map(str, all_node_ids[i:i + 10])) + "\n")

# 4. Heat / Cool (250 C -> 25 C)
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
*EL PRINT, ELSET=SILICON_DIE
S
*EL PRINT, ELSET=FR4_SUBSTRATE
S
*END STEP
"""

with open("sim.inp", "w") as f:
    f.write(physics_deck)

subprocess.run(["ccx", "sim"], check=True)

# 5. Check against Timoshenko textbook formula
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
            if len(parts) == 4 and parts.isdigit():
                z_displacements.append(float(parts))

warpage_mm = max(z_displacements) - min(z_displacements)

L, dT = 10.0, 25.0 - 250.0
E1, h1, a1 = 18000.0, 0.8, 16.0e-6
E2, h2, a2 = 130000.0, 0.2, 2.6e-6
h, m, n = h1 + h2, h1 / h2, E1 / E2

curvature = (6 * (a2 - a1) * dT * (1 + m)**2) / (
    h * (3 * (1 + m)**2 + (1 + m * n) * (m**2 + 1 / (m * n)))
)
timoshenko_warpage_mm = abs(curvature) * (L**2) / 8.0

print(f"3D FEA Simulated Warpage:   {warpage_mm * 1000:.2f} microns")
print(f"Timoshenko Analytical Math: {timoshenko_warpage_mm * 1000:.2f} microns")
Use code with caution.

Script 2: run_solder_bga.py (9-Bump Flip-Chip BGA with Underfill Toggle)

python
import subprocess
import gmsh
import numpy as np

use_underfill = True  # Toggle False (503 MPa) vs True (302 MPa)

L, W = 10.0, 2.0
h_fr4, h_gap, h_si = 0.8, 0.1, 0.2
solder_radius = 0.15
solder_x_positions = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
mesh_size = 0.15

# 0. Open & 1. Glue
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

# 2. Mesh
gmsh.option.setNumber("Mesh.SaveAll", 0)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
gmsh.model.mesh.generate(3)
gmsh.write("mesh_only.inp")
gmsh.finalize()

# 3. Pin
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
            nodes[int(parts)] = (float(parts), float(parts), float(parts))

all_node_ids = sorted(nodes.keys())
n1 = min(all_node_ids, key=lambda i: (nodes[i]**2 + nodes[i]**2 + nodes[i]**2))
n2 = min(all_node_ids, key=lambda i: ((nodes[i] - L)**2 + nodes[i]**2 + nodes[i]**2))
n3 = min(all_node_ids, key=lambda i: (nodes[i]**2 + (nodes[i] - W)**2 + nodes[i]**2))

with open("nall.nam", "w") as f:
    f.write("*NSET, NSET=NALL\n")
    for i in range(0, len(all_node_ids), 10):
        f.write(", ".join(map(str, all_node_ids[i:i + 10])) + "\n")

# 4. Heat / Cool
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

# 5. Check
z_displacements, solder_vm_stresses = [], []
with open("sim.dat", "r") as f:
    mode, current_set = None, ""
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
        if mode == "U" and len(parts) == 4 and parts.isdigit():
            z_displacements.append(float(parts))
        elif mode == "S" and current_set == "SAC305" and len(parts) == 8 and parts.isdigit():
            sxx, syy, szz, sxy, sxz, syz = [float(x) for x in parts[2:8]]
            vm = np.sqrt(
                0.5 * ((sxx - syy)**2 + (syy - szz)**2 + (szz - sxx)**2)
                + 3.0 * (sxy**2 + sxz**2 + syz**2)
            )
            solder_vm_stresses.append(vm)

print(f"Package Warpage:          {(max(z_displacements) - min(z_displacements)) * 1000.0:.2f} microns")
print(f"Max SAC305 Solder Stress: {max(solder_vm_stresses):.1f} MPa")
Use code with caution.

Script 3: plot_cross_section.py (3D Cutaway of the 9 Solder Joints)

python
import numpy as np
import pyvista as pv

# 1. Read nodes & elements from mesh_only.inp
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
            node_ids.append(int(parts))
            coords.append([float(parts), float(parts), float(parts)])

id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}
points = np.array(coords)

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
            elem_ids.append(parts)
            cells.append( + [id_to_idx[n] for n in parts[1:5]])

elem_to_idx = {eid: idx for idx, eid in enumerate(elem_ids)}
grid = pv.UnstructuredGrid(
    np.hstack(cells), np.full(len(cells), pv.CellType.TETRA, dtype=np.uint8), points
)

# 2. Read displacements & von Mises stress from sim.dat
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
        parts = line.split()
        if not parts:
            continue
        if mode == "U" and len(parts) == 4 and parts.isdigit():
            displacements[id_to_idx[int(parts)]] = [float(parts), float(parts), float(parts)]
        elif mode == "S" and len(parts) == 8 and parts.isdigit():
            eid = int(parts)
            if eid in elem_to_idx:
                sxx, syy, szz, sxy, sxz, syz = [float(x) for x in parts[2:8]]
                vm = np.sqrt(
                    0.5 * ((sxx - syy)**2 + (syy - szz)**2 + (szz - sxx)**2)
                    + 3.0 * (sxy**2 + sxz**2 + syz**2)
                )
                elem_stresses[eid].append(vm)

vm_array = np.zeros(len(elem_ids))
for eid, vals in elem_stresses.items():
    if vals:
        vm_array[elem_to_idx[eid]] = np.mean(vals)

grid.point_data["U"] = displacements
grid.cell_data["von_Mises_MPa"] = vm_array

# 3. Slice down the centerline (Y = 1.0 mm) and save image
grid = grid.cell_data_to_point_data()
warped = grid.warp_by_vector("U", factor=30.0)
cross_section = warped.slice(normal="y", origin=[5.0, 1.0, 0.5])

plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(
    cross_section,
    scalars="von_Mises_MPa",
    cmap="turbo",
    clim=[0.0, 300.0],
    show_edges=True,
    edge_opacity=0.2,
    scalar_bar_args={"title": "von Mises Stress (MPa)"},
)
plotter.view_xz()
plotter.add_axes()
plotter.add_text("Centerline Cross-Section: 9 Solder Joints & Underfill", font_size=12)
plotter.reset_camera()
plotter.screenshot("solder_cross_section.png")
Use code with caution.
