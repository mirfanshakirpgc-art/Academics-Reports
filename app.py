Ah! That `SyntaxError` happened because some of my conversational text accidentally got pasted into your `app.py` file.

Here is the clean, raw code block. Make sure you select everything inside this box, copy it, and replace your existing code module completely:

```python
# ---------------------------------------------------------
# 📝 ENTER MARKS & ATTENDANCE MODULE (COMPLETE UPGRADED ENGINE)
# ---------------------------------------------------------
elif menu_choice == "📝 Enter Marks & Attendance":
    st.title("📝 Data Intake Management Dashboard")
    sub_tab_selection = st.radio("🎯 Select Workspace Sub-Module Target:", ["📝 Academic Exam Marks Entry", "📅 Monthly Attendance Entry"], horizontal=True)
    st.markdown("---")

    current_user_id = st.session_state.get('user_id', None)
    current_role = st.session_state.get('role', st.session_state.get('user_role', 'teacher'))

    # =========================================================
    # 1. ACADEMIC EXAM MARKS ENTRY SUB-MODULE
    # =========================================================
    if sub_tab_selection == "📝 Academic Exam Marks Entry":
        entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="marks_workflow_mode")
        st.markdown("---")

        if entry_mode == "📋 By Complete Section":
            c_cls, c_sess, c1, c2, c3 = st.columns([1.2, 1.5, 1.8, 2, 2])
            
            with c_cls:
                sel_class = st.selectbox("Class Level:", ["11th", "12th"], index=1, key="entry_marks_class_lvl")
            
            with c_sess:
                default_sessions = ["2025-2027", "2026-2028"] if sel_class == "12th" else ["2026-2028", "2025-2027"]
                sel_session = st.selectbox("Academic Session:", default_sessions, key="entry_marks_session")

            if current_role == 'teacher' and current_user_id is not None:
                teacher_rights = run_query("SELECT subject, section FROM allocations WHERE user_id = :uid", {"uid": int(current_user_id)})
                if not teacher_rights.empty:
                    allowed_subs = sorted(list(teacher_rights['subject'].unique()))
                    allowed_secs = sorted(list(teacher_rights['section'].unique()))
                    with c1: st.info("🔒 Bound to Allocation Profile")
                    with c2: raw_sel_subject = st.selectbox("Select Subject:", allowed_subs)
                    with c3: sel_section = st.selectbox("Select Section:", allowed_secs)
                else:
                    st.warning("🚨 You do not have any active allocations assigned.")
                    raw_sel_subject, sel_section = None, None
            else:
                with c1: 
                    normalized_keys = {k.upper().strip(): k for k in DISCIPLINE_SECTIONS_MAP.keys()}
                    selected_display_disc = st.selectbox("Select Discipline:", list(normalized_keys.keys()), key="entry_discipline_selector")
                    sel_discipline = normalized_keys[selected_display_disc]
                with c2: 
                    raw_sel_subject = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP.get(sel_discipline, []), key="entry_subject_selector")
                with c3: 
                    sections_options = DISCIPLINE_SECTIONS_MAP.get(sel_discipline, [])
                    sel_section = st.selectbox("Select Section:", sections_options, key="entry_section_selector")
            
            sel_subject = raw_sel_subject
            if sel_class == "12th" and raw_sel_subject:
                cleaned_sub = str(raw_sel_subject).strip().upper()
                if cleaned_sub == 'B_MATH':      sel_subject = "B_stats"
                elif cleaned_sub == 'COMMERCE':   sel_subject = "Banking"
                elif cleaned_sub == 'ECONOMICS':  sel_subject = "GEO"

            if sel_subject and sel_section:
                row2_1, row2_2 = st.columns(2)
                with row2_1: sel_exam = st.selectbox("Test Type:", AVAILABLE_EXAMS)
                with row2_2: total_marks = st.number_input("Total Marks Assigned:", value=100)
                
                try:
                    roster_df = run_query("""
                        SELECT s.id AS "ID", s.name AS "Student Name", m.marks_obtained AS "Marks"
                        FROM students s
                        LEFT JOIN marks m ON s.id = m.student_id AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:subject)) AND TRIM(m.exam_type) = TRIM(:exam)
                        WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                          AND UPPER(TRIM(s.class)) = UPPER(TRIM(:class))
                          AND UPPER(TRIM(s.session)) = UPPER(TRIM(:session))
                          AND (s.status IS NULL OR UPPER(TRIM(s.status)) != 'LEFT')
                        ORDER BY s.id ASC
                    """, {"subject": sel_subject, "exam": sel_exam, "section": sel_section, "class": sel_class, "session": sel_session})
                    
                    if roster_df.empty:
                        st.info(f"💡 No students found registered in {sel_class} ({sel_session}), section '{sel_section}' yet.")
                    else:
                        roster_df['Marks'] = roster_df['Marks'].fillna("")
                        with st.form("bulk_marks_form"):
                            updated_scores = {}
                            for idx, row in roster_df.iterrows():
                                col_s1, col_s2 = st.columns([3, 1])
                                col_s1.write(f"🏷️ **{row['ID']}** — {row['Student Name']}")
                                updated_scores[row['ID']] = col_s2.text_input("Score", value=str(row['Marks']), key=f"sec_{row['ID']}", label_visibility="collapsed")
                            
                            if st.form_submit_button("💾 Save Section Marks", type="primary"):
                                for s_id, score in updated_scores.items():
                                    execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = UPPER(TRIM(:subject)) AND TRIM(exam_type) = TRIM(:exam)", {"s_id": int(s_id), "subject": sel_subject, "exam": sel_exam})
                                    if score.strip() != "":
                                        execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :subject, :exam, :score, :total)", {"s_id": int(s_id), "subject": sel_subject.strip().upper(), "exam": sel_exam.strip(), "score": score.strip(), "total": total_marks})
                                st.success("🎉 Section marks matrix saved completely!")
                                st.rerun()
                except Exception as e:
                    st.error(f"Database sync issue: {e}")

    # =========================================================
    # 2. MONTHLY ATTENDANCE ENTRY SUB-MODULE
    # =========================================================
    elif sub_tab_selection == "📅 Monthly Attendance Entry":
        st.subheader("📅 Monthly Attendance Workspace")
        att_flow_mode = st.radio("Select Entry Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="attendance_workflow_mode")
        st.markdown("---")
        
        if att_flow_mode == "📋 By Complete Section":
            c_att_cls, c_att_sess, col_as1, col_as2, col_as3 = st.columns([1.2, 1.5, 1.8, 2, 2])
            
            with c_att_cls:
                att_class = st.selectbox("Class Level:", ["11th", "12th"], index=1, key="entry_att_class_lvl")
            
            with c_att_sess:
                att_default_sessions = ["2025-2027", "2026-2028"] if att_class == "12th" else ["2026-2028", "2025-2027"]
                att_session = st.selectbox("Academic Session:", att_default_sessions, key="entry_att_session")

            if current_role == 'teacher' and current_user_id is not None:
                teacher_rights = run_query("SELECT section FROM allocations WHERE user_id = :uid", {"uid": int(current_user_id)})
                allowed_secs = sorted(list(teacher_rights['section'].unique())) if not teacher_rights.empty else []
                with col_as1: st.info("🔒 Logged Teacher Roster View")
                with col_as2: att_section = st.selectbox("Select Target Section:", allowed_secs, key="att_sec")
                with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month")
            else:
                with col_as1: 
                    normalized_keys_att = {k.upper().strip(): k for k in DISCIPLINE_SECTIONS_MAP.keys()}
                    selected_display_disc_att = st.selectbox("Select Discipline Context:", list(normalized_keys_att.keys()), key="att_disc")
                    att_discipline = normalized_keys_att[selected_display_disc_att]
                with col_as2: 
                    sections_options = DISCIPLINE_SECTIONS_MAP.get(att_discipline, [])
                    att_section = st.selectbox("Select Target Section:", sections_options, key="att_sec")
                with col_as3: 
                    att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month")
            
            if att_section:
                default_days = st.number_input("Set Total Working Days:", min_value=1, max_value=31, value=24, key="sec_global_days")
                
                try:
                    students_att_list = run_query("""
                        SELECT s.id AS "ID", s.name AS "Student Name", a.present_days
                        FROM students s
                        LEFT JOIN attendance a ON s.id = a.student_id AND UPPER(TRIM(a.month_name)) = UPPER(TRIM(:month))
                        WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                          AND UPPER(TRIM(s.class)) = UPPER(TRIM(:class))
                          AND UPPER(TRIM(s.session)) = UPPER(TRIM(:session))
                          AND (s.status IS NULL OR UPPER(TRIM(s.status)) != 'LEFT')
                        ORDER BY s.id ASC
                    """, {"month": att_month, "section": att_section, "class": att_class, "session": att_session})
                    
                    if not students_att_list.empty:
                        with st.form("bulk_attendance_form"):
                            saved_att_presents = {}
                            for idx, row in students_att_list.iterrows():
                                c_b1, c_b2 = st.columns([3, 1])
                                c_b1.write(f"👤 **{row['ID']}** — {row['Student Name']}")
                                init_pres = int(row['present_days']) if pd.notna(row['present_days']) else default_days
                                saved_att_presents[row['ID']] = c_b2.number_input("Days Present", min_value=0, max_value=int(default_days), value=min(int(init_pres), int(default_days)), key=f"pres_{row['ID']}")
                            
                            if st.form_submit_button("💾 Save Attendance Ledger", type="primary"):
                                for s_id, p_d in saved_att_presents.items():
                                    execute_db_command("""
                                        INSERT INTO attendance (student_id, month_name, total_days, present_days)
                                        VALUES (:s_id, :month, :td, :pd)
                                        ON CONFLICT (student_id, month_name) DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                                    """, {"s_id": int(s_id), "month": att_month.strip(), "td": default_days, "pd": int(p_d)})
                                st.success("🎉 Section Attendance saved successfully!")
                                rerun()
                    else:
                        st.info(f"💡 No students found registered in {att_class} ({att_session}), section '{att_section}' for this query selection.")
                except Exception as e:
                    st.error(f"Attendance sync error: {e}")

```
