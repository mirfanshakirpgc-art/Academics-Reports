# ----------------- 🪪 STUDENT RESULT CARDS -----------------
elif menu_choice == "🪪 Student Result Cards":
    st.title("🪪 Student Result Cards — Print Engine")
    
    print_scope = st.radio("𖨾 Select Scope:", ["👤 Single Student Card", "👥 Complete Section Cards"], horizontal=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1: search_id = st.text_input("🔍 Enter Student Roll Number / ID:")
    with col_c2: selected_test = st.selectbox("🎯 Select Test Term:", options=AVAILABLE_EXAMS)

    if search_id and search_id.isdigit() and selected_test:
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if not base_student.empty:
            target_section = base_student['section'].iloc[0].upper().strip()
            
            if print_scope == "👥 Complete Section Cards":
                students_to_print = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": target_section})
            else:
                students_to_print = pd.DataFrame([{"id": int(search_id), "name": base_student['name'].iloc[0], "section": target_section, "class": base_student['class'].iloc[0]}])

            # HTML PAYLOAD WITH INTEGRATED INLINE STYLES AND LAYOUT
            compiled_html = """
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                body { font-family: "Times New Roman", Times, serif; color: #000; background-color: #fff; margin: 0; padding: 10px; }
                .official-card-container { max-width: 850px; margin: 10px auto; padding: 25px; border: 1px solid #000; background: #fff; position: relative; }
                
                /* VERTICAL BLOCK HEADER LAYOUT */
                .header-block { text-align: left; margin-bottom: 20px; width: 100%; }
                .logo-row { display: block; width: 100%; margin-bottom: 12px; }
                .logo-img { max-height: 48px; width: auto; display: block; margin-left: 0; }
                
                .inst-main-header { font-weight: bold; font-size: 28px; letter-spacing: 0.5px; margin: 0; line-height: 1.1; text-align: center; width: 100%; }
                .inst-sub-header { font-size: 13px; font-weight: normal; margin: 4px 0 0 0; text-align: center; color: #444; width: 100%; }
                
                /* 1. HIGHLIGHTED "RESULT CARD" BANNER */
                .doc-type-banner { text-align: center; font-weight: bold; font-size: 18px; text-transform: uppercase; margin: 25px 0 20px 0; letter-spacing: 1px; background-color: #f2f2f2; padding: 8px; border: 1px solid #000; }
                
                /* THE HORIZONTAL STRUCTURAL GRID */
                .meta-layout-table { width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px; font-size: 14px; }
                .meta-layout-table td { border: none; padding: 3px; vertical-align: bottom; white-space: nowrap; }
                .underlined-value-span { border-bottom: 1px solid #000; font-weight: bold; padding: 0 4px; display: inline-block; text-transform: uppercase; }
                
                .doc-data-table { width: 100%; border-collapse: collapse; margin-top: 5px; margin-bottom: 15px; font-size: 14px; }
                .doc-data-table th, .doc-data-table td { border: 1px solid #000; padding: 6px 4px; text-align: center; }
                .doc-data-table th { font-weight: bold; background-color: #f2f2f2; }
                
                /* 2. HIGHLIGHTED SUBJECTS COLUMN CELL */
                .subject-cell { text-align: left; font-weight: bold; padding-left: 10px; background-color: #f9f9f9; }
                
                /* 3. HIGHLIGHTED GRAND TOTAL ROW */
                .grand-total-row { background-color: #fff2cc !important; font-weight: bold; }
                
                .section-header-title { font-size: 15px; font-weight: bold; margin: 25px 0 8px 0; text-align: left; text-transform: uppercase; border-bottom: 1px dashed #000; padding-bottom: 3px; }
                
                /* 4. HORIZONTAL ATTENDANCE LAYOUT WITH HIGHLIGHTED MONTHS ROW */
                .attendance-matrix-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
                .attendance-matrix-table th, .attendance-matrix-table td { border: 1px solid #000; padding: 5px 3px; text-align: center; }
                .attendance-matrix-table th { font-weight: bold; background-color: #f2f2f2; }
                .attendance-matrix-table td.row-title-cell { font-weight: bold; background-color: #fff; text-align: left; padding-left: 5px; font-size: 13px; }
                
                .footer-signatures-table { width: 100%; margin-top: 45px; font-size: 14px; border: none; }
                .footer-signatures-table td { border: none; }
                .sig-marker-line { border-top: 1px solid #000; width: 150px; text-align: center; padding-top: 4px; display: inline-block; font-weight: bold; }
                
                .print-btn { background: #222; color: #fff; padding: 10px 20px; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; margin-bottom: 20px; font-size: 14px; }
                @media print {
                    .print-btn { display: none !important; }
                    .official-card-container { border: none !important; margin: 0 auto 15mm auto !important; page-break-inside: avoid !important; break-inside: avoid !important; }
                    .print-page-break-divider { page-break-after: always !important; break-after: page !important; }
                }
            </style>
            </head>
            <body>
                <button class="print-btn" onclick="window.print();">🖨️ Trigger Document Print (Ctrl+P)</button>
            """

            for idx, student_row in students_to_print.iterrows():
                current_id = int(student_row['id'])
                name = str(student_row['name']).upper()
                section = str(student_row['section']).upper().strip()
                grade_class = str(student_row['class']).upper()
                test_name = selected_test.upper()
                
                matched_disp = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]: 
                        matched_disp = disp
                        break
                
                subjects_list = DISCIPLINE_SUBJECTS_MAP[matched_disp]
                raw_marks = run_query("SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks FROM marks WHERE student_id = :id", {"id": current_id})
                
                db_att = run_query("""
                    SELECT UPPER(TRIM(month_name)) as m_name, total_days, present_days 
                    FROM attendance WHERE student_id = :id
                """, {"id": current_id})
                
                att_cells = {}
                tot_sum, pres_sum = 0, 0
                for m in AVAILABLE_MONTHS:
                    m_upper = m.upper().strip()
                    match_att = db_att[db_att['m_name'] == m_upper]
                    if not match_att.empty:
                        td = int(match_att['total_days'].iloc[0])
                        pd_val = int(match_att['present_days'].iloc[0])
                        tot_sum += td
                        pres_sum += pd_val
                        pct = f"{int((pd_val / td) * 100)}%" if td > 0 else "0%"
                        att_cells[m] = {"td": str(td), "pd": str(pd_val), "pct": pct}
                    else:
                        att_cells[m] = {"td": "", "pd": "", "pct": ""}
                
                attendance_percentage = 0.0
                if tot_sum > 0:
                    attendance_percentage = (pres_sum / tot_sum) * 100
                        
                overall_pct_str = f"{int(attendance_percentage)}%" if tot_sum > 0 else ""
                att_cells["Over All Att."] = {"td": str(tot_sum) if tot_sum > 0 else "", "pd": str(pres_sum) if tot_sum > 0 else "", "pct": overall_pct_str}

                logo_base64 = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
                
                grand_total_marks = 0.0
                grand_obtained_marks = 0.0
                
                compiled_html += f"""
                <div class="official-card-container">
                    <div class="header-block">
                        <div class="logo-row">
                            <img class="logo-img" src="{logo_base64}" alt="Concordia Logo">
                        </div>
                        <div class="inst-main-header">CONCORDIA COLLEGE KASUR</div>
                    </div>
                    
                    <div class="doc-type-banner">Result Card</div>
                    
                    <table class="meta-layout-table">
                        <tr>
                            <td style="width: 40%;"> Name: <span class="underlined-value-span" style="width: 82%;">{name}</span></td>
                            <td style="width: 14%;"> ID: <span class="underlined-value-span" style="width: 68%;">{current_id}</span></td>
                            <td style="width: 16%;"> Section: <span class="underlined-value-span" style="width: 55%;">{section}</span></td>
                            <td style="width: 14%;"> Class: <span class="underlined-value-span" style="width: 55%;">{grade_class}</span></td>
                            <td style="width: 16%;"> Test: <span class="underlined-value-span" style="width: 65%;">{test_name}</span></td>
                        </tr>
                    </table>
                    
                    <table class="doc-data-table">
                        <thead>
                            <tr>
                                <th style="text-align: left; width: 30%; padding-left: 10px;">Subjects</th>
                                <th style="width: 12%;">Obt. Marks</th>
                                <th style="width: 12%;">Total Marks</th>
                                <th style="width: 12%;">Pass Marks</th>
                                <th style="width: 12%;">Age%</th>
                                <th style="width: 22%;">Remarks</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                student_failed_any_subject = False
                has_valid_marks_data = False

                for sub in subjects_list:
                    match = raw_marks[(raw_marks['subject'] == sub) & (raw_marks['exam_type'] == selected_test)]
                    obt_disp, tot_marks_num, pass_marks_num, per_disp, remarks_disp = "", "", "", "", ""
                    if not match.empty:
                        try:
                            obt_val = str(match['marks_obtained'].iloc[0]).strip().upper()
                            tot_val = match['total_marks'].iloc[0]
                            tot_marks_num = int(tot_val) if tot_val else 100
                            pass_marks_num = int(tot_marks_num * 0.4)
                            
                            if obt_val in ["A", "ABSENT"]:
                                obt_disp, per_disp, remarks_disp = "A", "0%", "Absent / Fail"
                                grand_total_marks += tot_marks_num
                                student_failed_any_subject = True
                                has_valid_marks_data = True
                            elif obt_val.replace('.', '', 1).isdigit():
                                num_obt = float(obt_val)
                                obt_disp = str(int(num_obt)) if num_obt.is_integer() else str(num_obt)
                                per_disp = f"{int((num_obt / tot_marks_num) * 100)}%"
                                
                                grand_obtained_marks += num_obt
                                grand_total_marks += tot_marks_num
                                has_valid_marks_data = True
                                
                                if num_obt >= pass_marks_num:
                                    if (num_obt / tot_marks_num) >= 0.8:
                                        remarks_disp = "Excellent"
                                    elif (num_obt / tot_marks_num) >= 0.6:
                                        remarks_disp = "Good"
                                    else:
                                        remarks_disp = "Fair / Pass"
                                else:
                                    remarks_disp = "Fail"
                                    student_failed_any_subject = True
                        except Exception: 
                            pass
                        
                    compiled_html += f"""
                            <tr>
                                <td class="subject-cell">{sub}</td>
                                <td>{obt_disp}</td>
                                <td>{tot_marks_num if tot_marks_num else "-"}</td>
                                <td>{pass_marks_num if pass_marks_num else "-"}</td>
                                <td>{per_disp}</td>
                                <td style="font-weight: bold;">{remarks_disp}</td>
                            </tr>
                    """
                
                grand_per_disp = ""
                grand_remarks_disp = ""
                if has_valid_marks_data and grand_total_marks > 0:
                    grand_per_disp = f"{int((grand_obtained_marks / grand_total_marks) * 100)}%"
                    grand_remarks_disp = "Needs Improvement" if student_failed_any_subject else "Promoted / Pass"

                # Highlighted Grand Total Row with Remarks included
                compiled_html += f"""
                            <tr class="grand-total-row">
                                <td style="text-align: left; padding-left: 10px;">GRAND TOTAL</td>
                                <td>{int(grand_obtained_marks) if grand_obtained_marks.is_integer() else grand_obtained_marks}</td>
                                <td>{int(grand_total_marks)}</td>
                                <td>-</td>
                                <td>{grand_per_disp}</td>
                                <td>{grand_remarks_disp}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <div class="section-header-title">Attendance History Record</div>
                    
                    <table class="attendance-matrix-table">
                        <thead>
                            <tr>
                                <th style="width: 12%;">Type Ledger</th>
                """
                
                for m in AVAILABLE_MONTHS:
                    compiled_html += f"<th>{m}</th>"
                compiled_html += "<th>Over All Att.</th></tr></thead><tbody>"
                
                # Row 1: Total Days
                compiled_html += "<tr><td class='row-title-cell'>Total Days</td>"
                for m in AVAILABLE_MONTHS:
                    compiled_html += f"<td>{att_cells[m]['td']}</td>"
                compiled_html += f"<td style='font-weight:bold;'>{att_cells['Over All Att.']['td']}</td></tr>"
                
                # Row 2: Present Days
                compiled_html += "<tr><td class='row-title-cell'>Present Days</td>"
                for m in AVAILABLE_MONTHS:
                    compiled_html += f"<td>{att_cells[m]['pd']}</td>"
                compiled_html += f"<td style='font-weight:bold;'>{att_cells['Over All Att.']['pd']}</td></tr>"
                
                # Row 3: Percentage
                compiled_html += "<tr><td class='row-title-cell'>Percentage</td>"
                for m in AVAILABLE_MONTHS:
                    compiled_html += f"<td>{att_cells[m]['pct']}</td>"
                compiled_html += f"<td style='font-weight:bold; background-color:#fff2cc;'>{att_cells['Over All Att.']['pct']}</td></tr>"
                
                compiled_html += """
                    </tbody>
                    </table>
                    
                    <table class="footer-signatures-table">
                        <tr>
                            <td style="width: 33.3%; text-align: left;"><span class="sig-marker-line">Class Teacher</span></td>
                            <td style="width: 33.3%; text-align: center;"><span class="sig-marker-line">Controller of Exams</span></td>
                            <td style="width: 33.3%; text-align: right;"><span class="sig-marker-line">Principal Signature</span></td>
                        </tr>
                    </table>
                </div>
                """
                if print_scope == "👥 Complete Section Cards" and idx < len(students_to_print) - 1:
                    compiled_html += '<div class="print-page-break-divider"></div>'

            compiled_html += "</body></html>"
            components.html(compiled_html, height=800, scrolling=True)
        else:
            st.error("❌ This roll number does not exist.")
