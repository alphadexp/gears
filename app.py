import math
import tempfile
import cadquery as cq
import streamlit as st

st.set_page_config(page_title="NIHS 20-02 Gear Generator", page_icon="⚙️", layout="wide")

st.title("⚙️ NIHS 20-02 Watch Gear Generator")
st.caption("Swiss Horological Epicycloidal & Ogival 3D STEP Gear Profiler")

st.sidebar.header("Gear Parameters")
module = st.sidebar.number_input("Module (m in mm)", min_value=0.05, max_value=1.00, value=0.12, step=0.01, format="%.2f")
z = st.sidebar.number_input("Tooth Count (z)", min_value=6, max_value=150, value=60, step=1)
z_mate = st.sidebar.number_input("Mating Gear Count (z_mate)", min_value=6, max_value=150, value=10, step=1)
face_width = st.sidebar.number_input("Face Width / Thickness (mm)", min_value=0.05, max_value=5.00, value=0.20, step=0.05, format="%.2f")
bore_diameter = st.sidebar.number_input("Center Bore Diameter (mm)", min_value=0.10, max_value=5.00, value=0.50, step=0.05, format="%.2f")
backlash = st.sidebar.number_input("Backlash Allowance (mm)", min_value=0.000, max_value=0.030, value=0.005, step=0.001, format="%.3f")

is_pinion = z <= 12
comp_type = "Pinion (Ogival Arc)" if is_pinion else "Wheel (Epicycloidal)"

R_p = (module * z) / 2.0
d_p = 2.0 * R_p
a = (module * (z + z_mate)) / 2.0
h_f = 1.40 * module
R_r = R_p - h_f
d_r = 2.0 * R_r

if is_pinion:
    h_a = 1.25 * module if z <= 7 else (1.15 * module if z <= 9 else 1.05 * module)
else:
    h_a = 0.95 * module

R_a = R_p + h_a
d_a = 2.0 * R_a
total_depth = h_a + h_f

col1, col2, col3, col4 = st.columns(4)
col1.metric("Component Type", comp_type)
col2.metric("Pitch Diameter (d_p)", f"{d_p:.3f} mm")
col3.metric("Outside Diameter (d_a)", f"{d_a:.3f} mm")
col4.metric("Center Distance (a)", f"{a:.3f} mm")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Root Diameter (d_r)", f"{d_r:.3f} mm")
col6.metric("Addendum (h_a)", f"{h_a:.3f} mm")
col7.metric("Dedendum (h_f)", f"{h_f:.3f} mm")
col8.metric("Total Depth (h)", f"{total_depth:.3f} mm")

st.divider()

def generate_nihs2002_points(z, z_mate, module, backlash=0.005, num_arc_points=25):
    R_p = (module * z) / 2.0
    h_f = 1.40 * module
    R_r = R_p - h_f
    is_pinion = z <= 12

    if is_pinion:
        s = 1.05 * module
        h_a = 1.25 * module if z <= 7 else (1.15 * module if z <= 9 else 1.05 * module)
        R_a = R_p + h_a
    else:
        s = (math.pi * module / 2.0) - backlash
        h_a = 0.95 * module
        R_a = R_p + h_a
        R_g = (module * z_mate) / 4.0

    pitch_angle = (2 * math.pi) / z
    tooth_angle = s / R_p
    half_tooth = tooth_angle / 2.0
    right_flank = []

    if is_pinion:
        P0 = (R_p * math.cos(half_tooth), R_p * math.sin(half_tooth))
        A = (R_a, 0.0)
        dx, dy = A[0] - P0[0], A[1] - P0[1]
        mid_x, mid_y = (P0[0] + A[0]) / 2.0, (P0[1] + A[1]) / 2.0
        perp_slope = -dx / dy
        x_c = R_p * 0.8
        y_c = mid_y + perp_slope * (x_c - mid_x)
        R_ogive = math.hypot(A[0] - x_c, A[1] - y_c)
        start_angle = math.atan2(P0[1] - y_c, P0[0] - x_c)
        end_angle = math.atan2(A[1] - y_c, A[0] - x_c)

        for i in range(num_arc_points + 1):
            t = start_angle + (end_angle - start_angle) * (i / num_arc_points)
            px = x_c + R_ogive * math.cos(t)
            py = y_c + R_ogive * math.sin(t)
            right_flank.append((px, py))
    else:
        theta = 0.0
        step = 0.002
        epicycloid_pts = []
        while True:
            x = (R_p + R_g) * math.cos(theta) - R_g * math.cos((R_p + R_g) / R_g * theta)
            y = (R_p + R_g) * math.sin(theta) - R_g * math.sin((R_p + R_g) / R_g * theta)
            r = math.hypot(x, y)
            if r >= R_a:
                scale = R_a / r
                epicycloid_pts.append((x * scale, y * scale))
                break
            epicycloid_pts.append((x, y))
            theta += step

        for x, y in epicycloid_pts:
            angle = math.atan2(y, x) + half_tooth
            r = math.hypot(x, y)
            right_flank.append((r * math.cos(angle), r * math.sin(angle)))

    left_flank = [(x, -y) for x, y in reversed(right_flank)]
    r_start_angle = math.atan2(right_flank[0][1], right_flank[0][0])
    l_start_angle = math.atan2(left_flank[-1][1], left_flank[-1][0])

    dedendum_right = (R_r * math.cos(r_start_angle), R_r * math.sin(r_start_angle))
    dedendum_left = (R_r * math.cos(l_start_angle), R_r * math.sin(l_start_angle))
    single_tooth = [dedendum_left] + left_flank + right_flank + [dedendum_right]

    full_profile = []
    for i in range(z):
        rot = i * pitch_angle
        cos_a, sin_a = math.cos(rot), math.sin(rot)
        for px, py in single_tooth:
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            full_profile.append((rx, ry))

    return full_profile

if st.button("🚀 Generate 3D STEP Model", type="primary", use_container_width=True):
    with st.spinner("Building CadQuery 3D Solid Geometry..."):
        pts = generate_nihs2002_points(z=z, z_mate=z_mate, module=module, backlash=backlash)
        gear = (
            cq.Workplane("XY")
            .polyline(pts)
            .close()
            .extrude(face_width)
            .faces(">Z")
            .workplane()
            .hole(bore_diameter)
        )

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            cq.exporters.export(gear, tmp.name)
            with open(tmp.name, "rb") as f:
                step_data = f.read()

        file_label = f"nihs2002_z{z}_m{module}.step"
        st.success(f"Success! Model generated: {file_label}")
        st.download_button(
            label="⬇️ Download STEP File",
            data=step_data,
            file_name=file_label,
            mime="application/step",
            use_container_width=True
        )
