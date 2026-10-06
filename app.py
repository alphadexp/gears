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