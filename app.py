# 3. CORE DATA LOADING & TABLE RENDERING LOGIC
    if search_id and search_id.isdigit():
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if base_student.empty:
            st.error("❌ No student record discovered with that Roll Number.")
        elif not selected_tests:
            st.warning("Please pick at least one test type option.")
        else:
            target_section = base_student['section'].iloc[0].upper().strip()
            num_selected_tests = len(selected_tests)
            
            if print_scope == "👥 Print Complete Section Cards":
                students_to_print = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": target_section})
            else:
                students_to_print = pd.DataFrame([{
                    "id": int(search_id),
                    "name": base_student['name'].iloc[0],
                    "section": target_section,
                    "class": base_student['class'].iloc[0]
                }])

            for idx, student_row in students_to_print.iterrows():
                current_id = int(student_row['id'])
                name = str(student_row['name']).upper()
                section = str(student_row['section']).upper().strip()
                grade_class = str(student_row['class'])
                
                st.markdown(f"""
                <div style="background-color:#f8a100; padding:15px; border-radius:5px; color:white; font-weight:bold; margin-top:20px; margin-bottom:10px; font-family:sans-serif;">
                    <h2 style='margin:0; color:white;'>ACADEMICS PERFORMANCE REPORT</h2>
                    <p style='margin:5px 0 0 0; font-size:16px; color:white;'>
                        <b>NAME:</b> {name} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>ID:</b> {current_id} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>SECTION:</b> {section} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>CLASS:</b> {grade_class}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                raw_marks = run_query("""
                    SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks 
                    FROM marks 
                    WHERE student_id = :id AND exam_type IN :exams
                """, {"id": current_id, "exams": tuple(selected_tests)})
                
                assigned_discipline = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]:
                        assigned_discipline = disp
                        break
                
                ordered_subjects = DISCIPLINE_SUBJECTS_MAP[assigned_discipline]
                matrix_data = []
                
                # Global tracking for Multi-test Total Age%
                grand_total_obtained = 0.0
                grand_total_max = 0.0
                
                for subj in ordered_subjects:
                    row_entry = {"SUBJECTS": subj}
                    subj_total_obt = 0.0
                    subj_total_max = 0.0
                    
                    if num_selected_tests == 1:
                        # --- SINGLE TEST MODE COLUMNS ---
                        exam = selected_tests[0]
                        match = raw_marks[(raw_marks['subject'] == subj.upper().strip()) & (raw_marks['exam_type'] == exam.strip())]
                        if not match.empty:
                            obt = str(match['marks_obtained'].iloc[0]).strip().upper()
                            tot = match['total_marks'].iloc[0]
                            row_entry["Obt. Marks"] = obt
                            row_entry["Total Marks"] = str(tot)
                            if str(obt).replace('.', '', 1).isdigit():
                                row_entry["Age%"] = f"{int(float(obt)/tot * 100)}%"
                            elif obt == "A":
                                row_entry["Age%"] = "A"
                            else:
                                row_entry["Age%"] = "-"
                        else:
                            row_entry["Obt. Marks"] = "-"
                            row_entry["Total Marks"] = "-"
                            row_entry["Age%"] = "-"
                    else:
                        # --- MULTI TEST MODE COLUMNS ---
                        for exam in selected_tests:
                            match = raw_marks[(raw_marks['subject'] == subj.upper().strip()) & (raw_marks['exam_type'] == exam.strip())]
                            if not match.empty:
                                obt = str(match['marks_obtained'].iloc[0]).strip().upper()
                                tot = match['total_marks'].iloc[0]
                                row_entry[f"{exam} (Obt)"] = obt
                                if str(obt).replace('.', '', 1).isdigit():
                                    row_entry[f"{exam} (%)"] = f"{int(float(obt)/tot * 100)}%"
                                    subj_total_obt += float(obt)
                                    subj_total_max += tot
                                    grand_total_obtained += float(obt)
                                    grand_total_max += tot
                                elif obt == "A":
                                    row_entry[f"{exam} (%)"] = "A"
                                else:
                                    row_entry[f"{exam} (%)"] = "-"
                            else:
                                row_entry[f"{exam} (Obt)"] = "-"
                                row_entry[f"{exam} (%)"] = "-"
                        
                        if subj_total_max > 0:
                            row_entry["Total Age%"] = f"{int((subj_total_obt / subj_total_max) * 100)}%"
                        else:
                            row_entry["Total Age%"] = "-"
                            
                    matrix_data.append(row_entry)
                
                report_df = pd.DataFrame(matrix_data)
                total_row = {"SUBJECTS": "⚡ TOTAL"}
                
                if num_selected_tests == 1:
                    # Calculate single test column totals
                    exam = selected_tests[0]
                    exam_matches = raw_marks[raw_marks['exam_type'] == exam.strip()]
                    valid_matches = exam_matches[exam_matches['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
                    
                    if not valid_matches.empty:
                        t_obt = valid_matches['marks_obtained'].astype(float).sum()
                        t_max = exam_matches['total_marks'].iloc[0] * len(ordered_subjects)
                        total_row["Obt. Marks"] = f"{int(t_obt)}"
                        total_row["Total Marks"] = f"{int(t_max)}"
                        total_row["Age%"] = f"{int((t_obt/t_max)*100)}%"
                    else:
                        total_row["Obt. Marks"] = "-"
                        total_row["Total Marks"] = "-"
                        total_row["Age%"] = "-"
                else:
                    # Calculate multi test column totals
                    for exam in selected_tests:
                        exam_matches = raw_marks[raw_marks['exam_type'] == exam.strip()]
                        valid_exam_matches = exam_matches[exam_matches['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
                        if not valid_exam_matches.empty:
                            t_obt = valid_exam_matches['marks_obtained'].astype(float).sum()
                            t_max = exam_matches['total_marks'].iloc[0] * len(ordered_subjects)
                            total_row[f"{exam} (Obt)"] = f"{int(t_obt)}"
                            total_row[f"{exam} (%)"] = f"{int((t_obt/t_max)*100)}%"
                        else:
                            total_row[f"{exam} (Obt)"] = "-"
                            total_row[f"{exam} (%)"] = "-"
                    
                    if grand_total_max > 0:
                        total_row["Total Age%"] = f"{int((grand_total_obtained / grand_total_max) * 100)}%"
                    else:
                        total_row["Total Age%"] = "-"
                
                report_df = pd.concat([report_df, pd.DataFrame([total_row])], ignore_index=True)
                st.dataframe(report_df.set_index("SUBJECTS"), use_container_width=True, key=f"tbl_{current_id}")
                st.markdown('<div class="print-card-break"></div>', unsafe_allow_html=True)
