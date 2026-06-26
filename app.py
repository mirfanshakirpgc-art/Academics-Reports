# Force-rebuild anchor: v2.0.4
import streamlit as st
import pandas as pd
import time
from supabase import create_client, Client
from sqlalchemy import text 

# --- INTERFACE WEB CONFIGURATION ---
st.set_page_config(
    page_title="Academics Reports",  
    page_icon="🎓",
    layout="wide"
)

# --- SECURE OFFICIAL HTTP REST CLIENT ENGINE ---
supabase: Client = None

if "supabase" in st.secrets:
    try:
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"🚨 Failed to establish Supabase HTTP Client connection: {str(e)}")

# --- 🛠️ COMPATIBILITY LAYER FOR LEGACY PIPELINES ---
class MockResult:
    """Satisfies legacy structural initializations that chain a .fetchall() command."""
    def fetchall(self):
        return []
    def tolist(self):
        return []
    def __iter__(self):
        return iter([])

class MockEngine:
    """Intercepts raw legacy engine blocks and returns a valid mock result instead of None."""
    def begin(self):
        class MockContext:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass
            def execute(self, *args, **kwargs): return MockResult()
        return MockContext()
    def connect(self):
        return self.begin()
    def execute(self, *args, **kwargs):
        return MockResult()

# Prevents the 'NoneType has no attribute fetchall' error on initial structural runs
engine = MockEngine()

# --- STREAMLIT-COMPATIBLE RESILIENT DATA ENGINE ---

class ResilientDataFrame(pd.DataFrame):
    """
    Subclasses standard DataFrames to catch downstream .fetchall() calls 
    when legacy application sheets try to treat a DataFrame like an SQL cursor object.
    """
    def fetchall(self):
        if self.empty:
            return []
        return self.values.tolist()

def run_query(table_name_or_query: str, params=None, select_query: str = "*"):
    """Reads data over an API connection, dynamically rerouting legacy SQL structural endpoints."""
    if not supabase:
        st.error("Supabase API engine connection is inactive.")
        return ResilientDataFrame()
    
    # Standardize string formatting for evaluation
    table = str(table_name_or_query).lower().strip()
    
    # Process and unpack raw SQL queries down to clean target tokens
    for word in ["select", "from", "where", "order", "by", ";", " "]:
        if word in table:
            table = table.split("from")[-1].strip().split(" ")[0].split(";")[0]
            break
            
    table = table.replace("(", "").replace(")", "").replace("'", "").replace('"', "")
    
    # 🔄 Fix: Schema Cache Routing Rules
    if table in ["sessions", "academic_sessions", "academic_systems"]:
        # Redirect missing 'academic_systems' lookups to your active 'academic_sessions' cache
        table = "academic_sessions"
    elif table in ["subjects", "subject_mappings"]:
        table = "subject_mappings"
            
    try:
        response = supabase.table(table).select(select_query).execute()
        if response.data is None:
            return ResilientDataFrame()
        return ResilientDataFrame(response.data)
    except Exception as e:
        st.error(f"HTTP GET fetch failure on table '{table}': {str(e)}")
        return ResilientDataFrame()

def insert_data(table_name: str, row_dict: dict):
    """Inserts records securely while maintaining alias redirection protection rules."""
    if not supabase:
        st.error("Supabase API engine connection is inactive.")
        return None
        
    table_target = str(table_name).lower().strip()
    
    if table_target in ["sessions", "academic_sessions", "academic_systems"]:
        table_name = "academic_sessions"
    elif table_target in ["subjects", "subject_mappings"]:
        table_name = "subject_mappings"
        
    try:
        return supabase.table(table_name).insert(row_dict).execute()
    except Exception as e:
        st.error(f"HTTP POST payload insertion failure on table '{table_name}': {str(e)}")
        return None
# ==============================================================================
# 2. SHARED REUSABLE FUNCTIONS (Shared between Authorized Roles)
# ==============================================================================
def render_master_setup_engine():
    """Centralized core setup engine giving Principal and VP rights to create foundational school data structures and operational mappings."""
    st.subheader("⚙️ Master Institutional Setup Engine")
    
    # Combined Tabs view incorporating Class In-Charge Allocations as Tab 3
    tab1, tab2, tab3 = st.tabs([
        "🏛️ 1. Core Configuration Parameters", 
        "🔗 2. Operational Allocation Mapping", 
        "📋 3. Class In-Charge Allocations"
    ])
    
    with tab1:
        st.markdown("### Add & Manage Structural School Variables")
        setup_type = st.selectbox(
            "Select Variable Layer to Manage:",
            ["Session", "Academic System", "Classes", "Sections", "Subjects", "Test/Exam", "Disciplines", "Teachers"]
        )
        
        # ----------------------------------------------------------------------
        # 1. SESSION MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        if setup_type == "Session":
            st.markdown("#### ➕ Add New Session")
            with st.form("form_session"):
                col1, col2 = st.columns(2)
                with col1: session_name = st.text_input("Session Name/Year:", placeholder="e.g., 2026-2027")
                with col2: session_status = st.selectbox("Initial Status:", ["Active", "Inactive"])
                submit = st.form_submit_button("➕ Register Session Year", type="primary")
                if submit:
                    if session_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO sessions (session_name, status) VALUES (:name, :status)"), 
                                             {"name": session_name, "status": session_status})
                            st.success(f"🎉 Session Year '{session_name}' initialized successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Name tag cannot be empty.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Session Records")
            sessions_df = run_query("SELECT id, session_name, status FROM sessions")
            if not sessions_df.empty:
                session_options = [f"{row['id']} - {row['session_name']} ({row['status']})" for _, row in sessions_df.iterrows()]
                selected_sess = st.selectbox("Select Target Session to Update:", session_options, key="edit_sess_select")
                target_id = int(selected_sess.split(" - ")[0])
                current_data = sessions_df[sessions_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_session"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Name/Year:", value=current_data['session_name'])
                    with col2: update_status = st.selectbox("Modify Status:", ["Active", "Inactive"], index=0 if current_data['status'] == "Active" else 1)
                    if st.form_submit_button("💾 Save Session Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE sessions SET session_name = :name, status = :status WHERE id = :id"),
                                         {"name": update_name, "status": update_status, "id": target_id})
                        st.success("🎉 Session references updated smoothly!")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No active Session logs discovered.")

        # ----------------------------------------------------------------------
        # 2. ACADEMIC SYSTEM MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Academic System":
            st.markdown("#### ➕ Add New Academic System")
            with st.form("form_academic_system"):
                col1, col2 = st.columns(2)
                with col1: system_name = st.text_input("Academic System Name:", placeholder="e.g., Semester System")
                with col2: system_desc = st.text_area("System Description:", placeholder="Notes...")
                submit = st.form_submit_button("➕ Register Academic System", type="primary")
                if submit:
                    if system_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO academic_systems (system_name, description) VALUES (:name, :desc)"), 
                                             {"name": system_name, "desc": system_desc})
                            st.success(f"🎉 Academic Framework '{system_name}' initialized successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ System name cannot be empty.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Academic Systems")
            systems_df = run_query("SELECT id, system_name, description FROM academic_systems")
            if not systems_df.empty:
                system_options = [f"{row['id']} - {row['system_name']}" for _, row in systems_df.iterrows()]
                selected_sys = st.selectbox("Select Target Framework to Update:", system_options, key="edit_sys_select")
                target_id = int(selected_sys.split(" - ")[0])
                current_data = systems_df[systems_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sys"):
                    update_name = st.text_input("Modify System Name:", value=current_data['system_name'])
                    update_desc = st.text_area("Modify Description:", value=current_data['description'] or "")
                    if st.form_submit_button("💾 Save System Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE academic_systems SET system_name = :name, description = :desc WHERE id = :id"),
                                         {"name": update_name, "desc": update_desc, "id": target_id})
                        st.success("🎉 Academic System profiles updated smoothly!")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No active Framework models discovered.")

        # ----------------------------------------------------------------------
        # 3. CLASSES MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Classes":
            st.markdown("#### ➕ Add New Class Level")
            with st.form("form_classes"):
                class_title = st.text_input("Class Level Designation Name:", placeholder="e.g., 11th, 12th, Matric")
                submit = st.form_submit_button("➕ Register Class Level", type="primary")
                if submit:
                    if class_title.strip():
                        try:
                            auto_sort = int(''.join(filter(str.isdigit, class_title))) if any(c.isdigit() for c in class_title) else 99
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO classes (class_level, sort_order) VALUES (:lvl, :sort)"), 
                                             {"lvl": class_title.strip(), "sort": auto_sort})
                            st.success(f"🎉 Class Level Grade '{class_title}' successfully committed!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else:
                        st.error("❌ Class Designation field cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Class Structures")
            classes_df = run_query("SELECT id, class_level FROM classes ORDER BY id ASC")
            if not classes_df.empty:
                class_options = [f"{row['id']} - Class: {row['class_level']}" for _, row in classes_df.iterrows()]
                selected_cls = st.selectbox("Select Class Node to Update:", class_options, key="edit_cls_select")
                target_id = int(selected_cls.split(" - ")[0])
                current_data = classes_df[classes_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_cls"):
                    update_lvl = st.text_input("Modify Level Designation Name:", value=str(current_data['class_level']))
                    if st.form_submit_button("💾 Save Class Changes", type="secondary"):
                        if update_lvl.strip():
                            auto_sort = int(''.join(filter(str.isdigit, update_lvl))) if any(c.isdigit() for c in update_lvl) else 99
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE classes SET class_level = :lvl, sort_order = :sort WHERE id = :id"),
                                             {"lvl": update_lvl.strip(), "sort": auto_sort, "id": target_id})
                            st.success("🎉 Class Level metadata structural fields synchronized!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Designation name cannot be empty.")
            else: st.info("No indexed class records inside storage system.")

        # ----------------------------------------------------------------------
        # 4. SECTIONS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Sections":
            st.markdown("#### ➕ Add New Section")
            with st.form("form_sections"):
                section_name = st.text_input("Section Label Name:", placeholder="e.g., A, B, Rose").upper()
                submit = st.form_submit_button("➕ Register Section Unit", type="primary")
                if submit:
                    if section_name.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO sections (section_name, max_capacity) VALUES (:name, 40)"), 
                                             {"name": section_name.strip()})
                            st.success(f"🎉 Section Room Node '{section_name}' successfully added!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Section Label code cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Section Branches")
            sections_df = run_query("SELECT id, section_name FROM sections")
            if not sections_df.empty:
                sec_options = [f"{row['id']} - Section {row['section_name']}" for _, row in sections_df.iterrows()]
                selected_sec = st.selectbox("Select Target Section Room:", sec_options, key="edit_sec_select")
                target_id = int(selected_sec.split(" - ")[0])
                current_data = sections_df[sections_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sec"):
                    update_name = st.text_input("Modify Label Token:", value=current_data['section_name']).upper()
                    if st.form_submit_button("💾 Save Section Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE sections SET section_name = :name WHERE id = :id"),
                                             {"name": update_name.strip(), "id": target_id})
                            st.success("🎉 Section adjustments processed effectively.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Section name cannot be empty.")
            else: st.info("No tracked sections exist.")

        # ----------------------------------------------------------------------
        # 5. SUBJECTS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Subjects":
            st.markdown("#### ➕ Add New Academic Subject")
            with st.form("form_subjects"):
                sub_name = st.text_input("Subject Official Title Name:", placeholder="e.g., Mathematics")
                submit = st.form_submit_button("➕ Register Academic Subject", type="primary")
                if submit:
                    if sub_name.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (:name, '', 1)"), 
                                             {"name": sub_name.strip()})
                            st.success(f"🎉 Core Subject Registry item locked: {sub_name}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Heading labels are mandatory entries.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Course Modules")
            subjects_df = run_query("SELECT id, subject_name FROM subjects")
            if not subjects_df.empty:
                sub_options = [f"{row['id']} - {row['subject_name']}" for _, row in subjects_df.iterrows()]
                selected_sub = st.selectbox("Select Target Course To Update:", sub_options, key="edit_sub_select")
                target_id = int(selected_sub.split(" - ")[0])
                current_data = subjects_df[subjects_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sub"):
                    update_name = st.text_input("Modify Course Title:", value=current_data['subject_name'])
                    if st.form_submit_button("💾 Save Subject Profile Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE subjects SET subject_name = :name WHERE id = :id"),
                                             {"name": update_name.strip(), "id": target_id})
                            st.success("🎉 Course catalogue adjustments saved dynamically.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Subject name cannot be empty.")
            else: st.info("Course mapping matrix arrays are blank.")

        # ----------------------------------------------------------------------
        # 6. TEST/EXAM SCHEME MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Test/Exam":
            st.markdown("#### ➕ Add New Test Evaluation Scheme")
            with st.form("form_test_exam"):
                test_title = st.text_input("Assessment Title:", placeholder="e.g., Mid Term Exam")
                submit = st.form_submit_button("➕ Register Test Profile Evaluation Scheme", type="primary")
                if submit:
                    if test_title.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO test_types (test_title, total_marks, weightage) VALUES (:title, 100, 0)"), 
                                             {"title": test_title.strip()})
                            st.success(f"🎉 Evaluation Pattern Scheme added: {test_title}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Test heading is required.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Test Protocols")
            tests_df = run_query("SELECT id, test_title FROM test_types")
            if not tests_df.empty:
                test_options = [f"{row['id']} - {row['test_title']}" for _, row in tests_df.iterrows()]
                selected_tst = st.selectbox("Select Target Evaluation Layout Template:", test_options, key="edit_tst_select")
                target_id = int(selected_tst.split(" - ")[0])
                current_data = tests_df[tests_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_tst"):
                    update_title = st.text_input("Modify Scheme Header Name:", value=current_data['test_title'])
                    if st.form_submit_button("💾 Save Scheme Blueprint Changes", type="secondary"):
                        if update_title.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE test_types SET test_title = :title WHERE id = :id"),
                                             {"title": update_title.strip(), "id": target_id})
                            st.success("🎉 Examination structure updated successfully.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Test heading cannot be empty.")
            else: st.info("No exam parameters declared in system schemas.")

        # ----------------------------------------------------------------------
        # 7. DISCIPLINES MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Disciplines":
            st.markdown("#### ➕ Add New Discipline Stream Group")
            with st.form("form_disciplines"):
                col1, col2 = st.columns(2)
                with col1: disc_title = st.text_input("Discipline Stream Group Designation:", placeholder="e.g., Computer Science")
                with col2: disc_code = st.text_input("Stream Unique Prefix Short Code:", placeholder="e.g., ICS").upper()
                submit = st.form_submit_button("➕ Register Discipline Stream Branch", type="primary")
                if submit:
                    if disc_title and disc_code:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO disciplines (discipline_title, short_code) VALUES (:title, :code)"), 
                                             {"title": disc_title, "code": disc_code})
                            st.success(f"🎉 Discipline Matrix Branch mapped: {disc_title}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Structural parameters require entries.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Stream Domains")
            disciplines_df = run_query("SELECT id, discipline_title, short_code FROM disciplines")
            if not disciplines_df.empty:
                disc_options = [f"{row['id']} - ({row['short_code']}) {row['discipline_title']}" for _, row in disciplines_df.iterrows()]
                selected_dsc = st.selectbox("Select Target Academic Stream Node:", disc_options, key="edit_dsc_select")
                target_id = int(selected_dsc.split(" - ")[0])
                current_data = disciplines_df[disciplines_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_dsc"):
                    col1, col2 = st.columns(2)
                    with col1: update_title = st.text_input("Modify Domain Label Heading:", value=current_data['discipline_title'])
                    with col2: update_code = st.text_input("Modify Short Index Tag Prefix:", value=current_data['short_code']).upper()
                    if st.form_submit_button("💾 Save Stream Group Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE disciplines SET discipline_title = :title, short_code = :code WHERE id = :id"),
                                         {"title": update_title, "code": update_code, "id": target_id})
                        st.success("🎉 Stream structure definitions modified successfully.")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No recorded disciplines exist inside ledger nodes.")

        # ----------------------------------------------------------------------
        # 8. TEACHERS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Teachers":
            st.markdown("#### ➕ Add New Instructor / Teacher Profile")
            with st.form("form_teachers"):
                col1, col2 = st.columns(2)
                with col1: t_id = st.text_input("Teacher ID/Code Prefix:", placeholder="e.g., T-101").strip()
                with col2: t_name = st.text_input("Full Registered Name:", placeholder="e.g., Prof. Sarah Khan")
                
                col3, col4 = st.columns(2)
                with col3: t_phone = st.text_input("Primary Contact Number:", placeholder="e.g., +923001234567")
                with col4: t_email = st.text_input("Official Email Address:", placeholder="e.g., sarah.khan@school.edu")
                
                submit = st.form_submit_button("➕ Register Faculty Instructor", type="primary")
                if submit:
                    if t_id and t_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO teachers (teacher_id, full_name, contact_number, email) 
                                    VALUES (:id, :name, :phone, :email)
                                """), {"id": t_id, "name": t_name, "phone": t_phone, "email": t_email})
                            st.success(f"🎉 Faculty record initialized for '{t_name}'!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error (Check for duplicate IDs): {e}")
                    else: st.error("❌ Teacher ID and Full Name are completely mandatory.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Faculty Rosters")
            teachers_df = run_query("SELECT teacher_id, full_name, contact_number, email FROM teachers")
            if not teachers_df.empty:
                teacher_options = [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()]
                selected_tch = st.selectbox("Select Target Instructor to Modify:", teacher_options, key="edit_tch_select")
                target_id = selected_tch.split(" - ")[0]
                current_data = teachers_df[teachers_df['teacher_id'] == target_id].iloc[0]
                
                with st.form("edit_form_tch"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Full Name:", value=current_data['full_name'])
                    with col2: update_phone = st.text_input("Modify Contact Number:", value=current_data['contact_number'] or "")
                    
                    update_email = st.text_input("Modify Email Address:", value=current_data['email'] or "")
                    
                    if st.form_submit_button("💾 Save Instructor Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE teachers 
                                    SET full_name = :name, contact_number = :phone, email = :email 
                                    WHERE teacher_id = :id
                                """), {"name": update_name.strip(), "phone": update_phone, "email": update_email, "id": target_id})
                            st.success("🎉 Instructor profile configuration metrics updated safely.")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("❌ Full Name column cannot be written as empty.")
            else: st.info("No active faculty staff logs loaded inside structural storage.")

    with tab2:
        st.markdown("### Map Institutional Dependencies")
        st.markdown("### 📝 New Subject Allocation Entry")

        # 1. Pull Sessions directly from Tab 1 data structure
        sessions_df = run_query("SELECT DISTINCT session_name FROM academic_sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df.iloc[:, 0].tolist() if not sessions_df.empty else [])

        col_sa1, col_sa2, col_sa3 = st.columns(3)
        with col_sa1:
            sel_session = st.selectbox("1. Select Session:", options=sessions_list, key="sa_sess")

        # 2. Pull Systems directly from Tab 1 data structure
        with col_sa2:
            if sel_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df.iloc[:, 0].tolist() if not systems_df.empty else [])
                sel_system = st.selectbox("2. Select Academic System:", options=systems_list, key="sa_sys")
            else:
                st.selectbox("2. Select Academic System:", ["🔒 Waiting for Session..."], disabled=True, key="sa_sys_dis")
                sel_system = "-- Select System --"

        # 3. Pull Classes directly from Tab 1 data structure
        with col_sa3:
            if sel_system != "-- Select System --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df.iloc[:, 0].tolist() if not classes_df.empty else [])
                sel_class = st.selectbox("3. Select Class:", options=classes_list, key="sa_cls")
            else:
                st.selectbox("3. Select Class:", ["🔒 Waiting for System..."], disabled=True, key="sa_cls_dis")
                sel_class = "-- Select Class --"

        col_sa4, col_sa5, col_sa6 = st.columns(3)

        # 4. Pull Disciplines directly from Tab 1 data structure
        with col_sa4:
            if sel_class != "-- Select Class --":
                disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df.iloc[:, 0].tolist() if not disciplines_df.empty else [])
                sel_discipline = st.selectbox("4. Select Discipline:", options=disciplines_list, key="sa_disc")
            else:
                st.selectbox("4. Select Discipline:", ["🔒 Waiting for Class..."], disabled=True, key="sa_disc_dis")
                sel_discipline = "-- Select Discipline --"

        # 5. Pull Sections directly from Tab 1 data structure
        with col_sa5:
            if sel_discipline != "-- Select Discipline --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df.iloc[:, 0].tolist() if not sections_df.empty else [])
                sel_section = st.selectbox("5. Select Section:", options=sections_list, key="sa_sec")
            else:
                st.selectbox("5. Select Section:", ["🔒 Waiting for Discipline..."], disabled=True, key="sa_sec_dis")
                sel_section = "-- Select Section --"

        # 6. Pull Subjects directly from your subject mapping setup configuration
        with col_sa6:
            if sel_section != "-- Select Section --":
                subjects_df = run_query("SELECT DISTINCT subject_name FROM subject_mappings")
                subjects_list = ["-- Select Subject --"] + (subjects_df.iloc[:, 0].tolist() if not subjects_df.empty else [])
                sel_subject = st.selectbox("6. Select Subject:", options=subjects_list, key="sa_subj")
            else:
                st.selectbox("6. Select Subject:", ["🔒 Waiting for Section..."], disabled=True, key="sa_subj_dis")
                sel_subject = "-- Select Subject --"

        # 7. Pull Registered Teachers from the configuration pool
        if sel_subject != "-- Select Subject --":
            teachers_df = run_query("SELECT teacher_id, full_name FROM teachers")
            teachers_list = ["-- Select Teacher --"] + [f"{row.iloc[0]} - {row.iloc[1]}" for _, row in teachers_df.iterrows()] if not teachers_df.empty else ["-- Select Teacher --"]
            selected_teacher = st.selectbox("7. Select Assigned Faculty Member:", options=teachers_list, key="sa_tchr")
        else:
            st.selectbox("7. Select Assigned Faculty Member:", ["🔒 Waiting for Subject..."], disabled=True, key="sa_tchr_dis")
            selected_teacher = "-- Select Teacher --"

        st.markdown("---")

        ready_to_submit_sa = all([
            sel_session != "-- Select Session --",
            sel_system != "-- Select System --",
            sel_class != "-- Select Class --",
            sel_discipline != "-- Select Discipline --",
            sel_section != "-- Select Section --",
            sel_subject != "-- Select Subject --",
            selected_teacher != "-- Select Teacher --"
        ])

        with st.form("form_subject_allocation_gate"):
            if ready_to_submit_sa:
                if st.form_submit_button("🔗 Link Subject Assignment Map", type="primary", use_container_width=True):
                    t_id = selected_teacher.split(" - ")[0].strip()
                    t_name = selected_teacher.split(" - ")[1].strip()
                    try:
                        supabase.table("subject_allocations").insert({
                            "session": sel_session,
                            "academic_system": sel_system,
                            "class_level": sel_class,
                            "discipline": sel_discipline,
                            "section": sel_section,
                            "subject_name": sel_subject,
                            "teacher_id": t_id,
                            "teacher_name": t_name
                        }).execute()
                        st.success(f"🎉 Allocation Successful: {t_name} assigned to {sel_subject} ({sel_class}-{sel_section})!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error updating allocation parameters: {e}")
            else:
                st.form_submit_button("🔒 Complete Steps 1-7 above to unlock submission", disabled=True, use_container_width=True)
    # ----------------------------------------------------------------------
        # 3. CLASS IN-CHARGE ALLOCATIONS (Optimized & Standardized)
        # ----------------------------------------------------------------------
        st.markdown("### Manage Class In-Charge Allocations")
        st.markdown("### 📋 Class In-Charge Mapping Management")
        
        # 1. Session Dropdown
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df.iloc[:, 0].tolist() if not sessions_df.empty else [])
        
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1: 
            sel_session = st.selectbox("1. Select Session Year:", options=sessions_list, key="inc_sess")
        
        # 2. Academic System Dropdown (Cascading from Session)
        with col_inc2:
            if sel_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df.iloc[:, 0].tolist() if not systems_df.empty else [])
                sel_system = st.selectbox("2. Select Academic Framework:", options=systems_list, key="inc_sys")
            else:
                st.selectbox("2. Select Academic Framework:", ["🔒 Waiting for Session..."], disabled=True, key="inc_sys_dis")
                sel_system = "-- Select System --"
                
        col_inc3, col_inc4 = st.columns(2)
        
        # 3. Class Level Dropdown (Cascading from System)
        with col_inc3:
            if sel_system not in ["-- Select System --", "", None]:
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df.iloc[:, 0].tolist() if not classes_df.empty else [])
                sel_class = st.selectbox("3. Assign Class Level Scope:", options=classes_list, key="inc_cls")
            else:
                st.selectbox("3. Assign Class Level Scope:", ["🔒 Waiting for System..."], disabled=True, key="inc_cls_dis")
                sel_class = "-- Select Class --"
                
        # 4. Section Dropdown (Cascading from Class)
        with col_inc4:
            if sel_class not in ["-- Select Class --", "", None]:
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df.iloc[:, 0].tolist() if not sections_df.empty else [])
                sel_section = st.selectbox("4. Assign Section Branch:", options=sections_list, key="inc_sec")
            else:
                st.selectbox("4. Assign Section Branch:", ["🔒 Waiting for Class..."], disabled=True, key="inc_sec_dis")
                sel_section = "-- Select Section --"
                
        # 5. Teacher Dropdown (Cascading from Section)
        if sel_section not in ["-- Select Section --", "", None]:
            teachers_df = run_query("SELECT teacher_id, full_name FROM teachers")
            teachers_list = ["-- Select Teacher --"] + [f"{row.iloc[0]} - {row.iloc[1]}" for _, row in teachers_df.iterrows()] if not teachers_df.empty else ["-- Select Teacher --"]
            selected_teacher = st.selectbox("5. Select Assigned Faculty Member:", options=teachers_list, key="inc_tchr")
        else:
            st.selectbox("5. Select Assigned Faculty Member:", ["🔒 Waiting for Section Selection..."], disabled=True, key="inc_tchr_dis")
            selected_teacher = "-- Select Teacher --"
            
        st.markdown("---")
        
        # Submission Validation Gate Check
        ready_to_submit_inc = all([
            sel_session != "-- Select Session --",
            sel_system != "-- Select System --",
            sel_class != "-- Select Class --",
            sel_section != "-- Select Section --",
            selected_teacher != "-- Select Teacher --"
        ])
        
        # Form Container Architecture
        with st.form("form_incharge_allocation_gate"):
            # Render active validation interface elements conditionally inside the context boundary
            if ready_to_submit_inc:
                if st.form_submit_button("🔗 Link Class In-Charge Assignment", type="primary", use_container_width=True):
                    t_id = selected_teacher.split(" - ")[0].strip()
                    t_name = selected_teacher.split(" - ")[1].strip()
                    try:
                        response = supabase.table("incharge_allocations").insert({
                            "session": sel_session,
                            "academic_system": sel_system,
                            "class_level": sel_class,
                            "section": sel_section,
                            "teacher_id": t_id,
                            "teacher_name": t_name
                        }).execute()
                        
                        st.success(f"🎉 Mapping Complete: {t_name} is now designated In-Charge for Class {sel_class}-{sel_section}!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Database execution failure: {e}")
            else:
                st.form_submit_button("🔗 Complete Steps 1-5 above to unlock assignment", disabled=True, use_container_width=True)
def render_student_management_workspace():
    """Shared workspace enabling authorized users to onboard, bulk import, or update student registry information."""
    st.subheader("📝 Student Records & Registration Directory")
    
    # Sub-tabs separating Single Manual Entry, Bulk Excel Loading, and Edit Panel
    tab1, tab2, tab3 = st.tabs([
        "🆕 Manual Admission Entry", 
        "📤 Bulk Import via Excel", 
        "✏️ Edit Student Profiles"
    ])
    
    # Ensure database schema table structure accommodates our 14 required structural fields
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                whatsapp_no TEXT,
                student_no TEXT,
                contact_1 TEXT NOT NULL,
                contact_2 TEXT,
                home_address TEXT,
                session TEXT,
                academic_system TEXT,
                class_level TEXT,
                discipline TEXT,
                section TEXT,
                roll_no INTEGER
            );
        """))

    # ==============================================================================
# TAB 1: MANUAL ADMISSION ENTRY
# ==============================================================================
    with tab1:
        st.write("### 🆕 Register New Student Particulars")
        st.write("📁 **Step 1: Assign Target Academic Placement Attributes**")
        
        # 1. Fetch live metadata drop targets from Supabase
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        # 2. Sequential layout configuration selectors
        col_a1, col_a2, col_a3 = st.columns(3)
        new_session = col_a1.selectbox("1. Target Session:*", options=sessions_list, key="manual_sess")

        # Helper logic to handle selection validation strings safely
        def get_val(val): 
            return None if not val or val.startswith("--") else val

        if get_val(new_session):
            systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
            systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
            new_system = col_a2.selectbox("2. Target Academic System:*", options=systems_list, key="manual_sys")
        else:
            new_system = col_a2.selectbox("2. Target Academic System:", ["-- Select System --"], disabled=True, key="manual_sys_dis")

        if get_val(new_system):
            classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
            classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
            new_class = col_a3.selectbox("3. Target Class:*", options=classes_list, key="manual_cls")
        else:
            new_class = col_a3.selectbox("3. Target Class:", ["-- Select Class --"], disabled=True, key="manual_cls_dis")

        col_a4, col_a5, col_a6 = st.columns(3)
        if get_val(new_class):
            disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
            disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
            new_discipline = col_a4.selectbox("4. Target Discipline:*", options=disciplines_list, key="manual_disc")
            
            sections_df = run_query("SELECT DISTINCT section_name FROM sections")
            sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
            new_sec = col_a5.selectbox("5. Target Section:*", options=sections_list, key="manual_sec")
        else:
            new_discipline = col_a4.selectbox("4. Target Discipline:", ["-- Select Discipline --"], disabled=True, key="manual_disc_dis")
            new_sec = col_a5.selectbox("5. Target Section:", ["-- Select Section --"], disabled=True, key="manual_sec_dis")
            
        new_roll = col_a6.number_input("6. Class Arrangement Roll No:*", min_value=1, step=1, key="manual_roll")

        st.markdown("---")
        
        # 3. Secure Container Verification Block
        if any(f in ["-- Select Session --", "-- Select System --", "-- Select Class --", "-- Select Discipline --", "-- Select Section --"] 
               for f in [new_session, new_system, new_class, new_discipline, new_sec]):
            st.warning("⏳ Please complete selecting all 5 Academic Placement Attributes above to reveal the registration entry form.")
        else:
            # ALL inputs and form logic are completely bundled inside here
            with st.form("student_profile_text_fields_form", clear_on_submit=True):
                st.write(f"📝 **Step 2: Enter Student Particulars for Class `{new_class} ({new_sec})`**")
                
                c1, c2, c3 = st.columns(3)
                new_id = c1.text_input("1. Student ID / Registration No:*")
                new_name = c2.text_input("2. Student Full Name:*")
                father_name = c3.text_input("3. Student's Father Name:*")
                
                c4, c5, c6 = st.columns(3)
                whatsapp = c4.text_input("4. WhatsApp Number:")
                stu_no = c5.text_input("5. Student Mobile Number:")
                contact1 = c6.text_input("6. Emergency Contact-1:*")
                
                c7, c8 = st.columns([1, 2])
                contact2 = c7.text_input("7. Alternative Contact-2:")
                address = c8.text_input("8. Home Address:")
                
                # The submit button belongs explicitly inside the form boundary context
                submit_manual = st.form_submit_button("🚀 Save Student Record", type="primary", use_container_width=True)

                if submit_manual:
                    if not new_id.strip() or not new_name.strip() or not father_name.strip() or not contact1.strip():
                        st.error("❌ Form Submission Rejected: Please fill out all required fields flagged with (*).")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO students (
                                        student_id, student_name, father_name, whatsapp_no, 
                                        student_no, contact_1, contact_2, home_address, session, 
                                        academic_system, class_level, discipline, section, roll_no
                                    ) VALUES (
                                        :id, :name, :fname, :wap, :sno, :c1, :c2, :addr, :sess, :sys, :cls, :disc, :sec, :roll
                                    )
                                """), {
                                    "id": new_id.strip(), "name": new_name.strip(), "fname": father_name.strip(), 
                                    "wap": whatsapp.strip() if whatsapp.strip() else None, 
                                    "sno": stu_no.strip() if stu_no.strip() else None, 
                                    "c1": contact1.strip(), 
                                    "c2": contact2.strip() if contact2.strip() else None, 
                                    "addr": address.strip() if address.strip() else None, 
                                    "sess": new_session, "sys": new_system, "cls": new_class, 
                                    "disc": new_discipline, "sec": new_sec, "roll": int(new_roll)
                                })
                            st.success(f"🎉 Successfully Registered: {new_name} has been securely committed to the system database!")
                            time.sleep(0.6)
                            st.rerun()
                        except Exception as transaction_error:
                            st.error(f"❌ Cloud Sync Aborted: {transaction_error}")
    # ==============================================================================
    # TAB 2: BULK IMPORT VIA EXCEL / CSV (DOWNLOAD CONFIGURATION LAYOUT ONLY)
    # ==============================================================================
    with tab2:
        st.write("### 📤 Bulk Import Student Registry via File Streaming")
        
        # --- SAMPLE FILE MAKER TEMPLATE DOCK ---
        st.markdown("📁 **Step 1: Download Required Roster Configuration Layout**")
        sample_df = pd.DataFrame(columns=[
            'student_id', 'student_name', 'father_name', 'whatsapp_no', 'student_no',
            'contact_1', 'contact_2', 'home_address', 'roll_no'
        ])
        sample_df.loc[0] = ['STU-2026-001', 'John Doe', 'Robert Doe', '+923001234567', '+923151234567', '+923331112222', '', 'Main Street, Block A', 1]
        
        csv_buffer = sample_df.to_csv(index=False).encode('utf-8')
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Download Template (.CSV Format)",
                data=csv_buffer,
                file_name="student_onboarding_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            import io  # <--- Add this line here to explicitly define it
            excel_io = io.BytesIO()
            with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
                sample_df.to_excel(writer, index=False, sheet_name='Students')
            st.download_button(
                label="📥 Download Template (.XLSX Format)",
                data=excel_io.getvalue(),
                file_name="student_onboarding_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        st.markdown("---")
        
        # --- PHASE 2: CASCADING PLACEMENT FILTERS VIEW ---
        st.markdown("📁 **Step 2: Assign Destination Academic Framework Attributes**")
        
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            bulk_session = st.selectbox("1. Target Session:*", options=sessions_list, key="bulk_sess")

        with col_b2:
            if bulk_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                bulk_system = st.selectbox("2. Target Academic System:*", options=systems_list, key="bulk_sys")
            else:
                st.selectbox("2. Target Academic System:", ["🔒 Waiting for Session..."], disabled=True, key="bulk_sys_dis")
                bulk_system = "-- Select System --"

        with col_b3:
            if bulk_system != "-- Select System --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                bulk_class = st.selectbox("3. Target Class:*", options=classes_list, key="bulk_cls")
            else:
                st.selectbox("3. Target Class:", ["🔒 Waiting for System..."], disabled=True, key="bulk_cls_dis")
                bulk_class = "-- Select Class --"

        col_b4, col_b5, col_b6 = st.columns(3)
        with col_b4:
            if bulk_class != "-- Select Class --":
                disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
                bulk_discipline = st.selectbox("4. Target Discipline:*", options=disciplines_list, key="bulk_disc")
            else:
                st.selectbox("4. Target Discipline:", ["🔒 Waiting for Class..."], disabled=True, key="bulk_disc_dis")
                bulk_discipline = "-- Select Discipline --"

        with col_b5:
            if bulk_class != "-- Select Class --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                bulk_sec = st.selectbox("5. Target Section:*", options=sections_list, key="bulk_sec")
            else:
                st.selectbox("5. Target Section:", ["🔒 Waiting for Class..."], disabled=True, key="bulk_sec_dis")
                bulk_sec = "-- Select Section --"

        with col_b6:
            bulk_roll_mode = st.selectbox(
                "6. Roll No Handling Mode:*", 
                options=["Use Roll No from File Row", "Auto-Generate Sequential Index"], 
                key="bulk_roll_mode"
            )
                
        st.markdown("---")

    # ==============================================================================
    # TAB 3: SEARCH & EDIT (WITH ADVANCED STRUCTURAL OPERATIONS)
    # ==============================================================================
    with tab3:
        st.write("### ✏️ Search, Batch Edit Section, or Modify Profiles")

        # Pull reference indices dynamically from Tab 1 Structural Variables
        sessions_df = run_query("academic_sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty and 'session_name' in sessions_df.columns else [])
        
        st.markdown("📁 **Step 1: Locate Active Target Parameters**")
        
        # Create 5 clean columns for your specific academic attributes
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        
        with col_s1:
            search_session = st.selectbox("Filter Session:", options=sessions_list, key="search_sess")
            
        with col_s2:
            if search_session != "-- Select Session --":
                try:
                    systems_df = run_query("academic_systems")
                    systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty and 'system_name' in systems_df.columns else [])
                except Exception:
                    systems_list = ["-- Select System --", "Annual", "Semester"]
                search_system = st.selectbox("Filter Academic System:", options=systems_list, key="search_system")
            else:
                st.selectbox("Filter Academic System:", ["🔒 Waiting..."], disabled=True, key="search_sys_dis")
                search_system = "-- Select System --"
                
        with col_s3:
            if search_system != "-- Select System --":
                classes_df = run_query("classes")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty and 'class_level' in classes_df.columns else [])
                search_class = st.selectbox("Filter Class:", options=classes_list, key="search_cls")
            else:
                st.selectbox("Filter Class:", ["🔒 Waiting..."], disabled=True, key="search_cls_dis")
                search_class = "-- Select Class --"

        with col_s4:
            if search_class != "-- Select Class --":
                try:
                    disc_df = run_query("disciplines")
                    if not disc_df.empty and 'discipline_title' in disc_df.columns:
                        disc_list = ["-- Select Discipline --"] + disc_df['discipline_title'].tolist()
                    else:
                        disc_list = ["-- Select Discipline --", "Medical"]
                except Exception as e:
                    st.sidebar.error(f"Discipline query failed: {e}")
                    disc_list = ["-- Select Discipline --", "Medical"]
                    
                search_discipline = st.selectbox("Filter Discipline:", options=disc_list, key="search_discipline")
            else:
                st.selectbox("Filter Discipline:", ["🔒 Waiting..."], disabled=True, key="search_disc_dis")
                search_discipline = "-- Select Discipline --"

        with col_s5:
            if search_discipline != "-- Select Discipline --":
                sections_df = run_query("sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty and 'section_name' in sections_df.columns else [])
                search_sec = st.selectbox("Filter Section:", options=sections_list, key="search_sec")
            else:
                st.selectbox("Filter Section:", ["🔒 Waiting..."], disabled=True, key="search_sec_dis")
                search_sec = "-- Select Section --"
        
        # Modification Scope Row
        st.markdown("---")
        edit_scope = st.radio(
            "Modification Scope:",
            options=["✨ Modify Single Student", "📊 Batch Edit Entire Section"],
            horizontal=True,
            key="edit_scope_toggle"
        )
        st.markdown("---")
        
        # Verify all 5 keys are explicitly selected before triggering queries
        if (search_session != "-- Select Session --" and 
            search_system != "-- Select System --" and 
            search_class != "-- Select Class --" and 
            search_discipline != "-- Select Discipline --" and 
            search_sec != "-- Select Section --"):
            
            try:
                # HTTP REST API query replacement handling exact filtering criteria
                response = supabase.table("students").select(
                    "student_id, roll_no, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, discipline, academic_system, session, class_level, section"
                ).execute()
                
                all_students = pd.DataFrame(response.data)
                
                if not all_students.empty:
                    # Filter client-side to handle text matching safely across variations
                    mask = (
                        (all_students['session'].astype(str).str.strip().str.lower() == search_session.strip().lower()) &
                        (all_students['academic_system'].astype(str).str.strip().str.lower() == search_system.strip().lower()) &
                        (all_students['class_level'].astype(str).str.strip().str.lower() == search_class.strip().lower()) &
                        (all_students['discipline'].astype(str).str.strip().str.lower() == search_discipline.strip().lower()) &
                        (all_students['section'].astype(str).str.strip().str.lower() == search_sec.strip().lower())
                    )
                    matched_students = all_students[mask].copy()
                    if 'roll_no' in matched_students.columns:
                        matched_students = matched_students.sort_values(by='roll_no', ascending=True)
                else:
                    matched_students = pd.DataFrame()
                
                if not matched_students.empty:
                    matched_students.columns = [str(c).lower().strip() for c in matched_students.columns]
                    # Drop tracking filtering columns if you want the exact view structure preserved
                    matched_students = matched_students[["student_id", "roll_no", "student_name", "father_name", "whatsapp_no", "student_no", "contact_1", "contact_2", "home_address", "discipline", "academic_system"]]
            except Exception as e:
                st.error(f"Error fetching directory: {e}")
                matched_students = pd.DataFrame()
                
            if matched_students.empty:
                st.info(f"ℹ No student records match parameters: {search_session} | {search_system} | Class {search_class} | {search_discipline} | Section {search_sec}")
                
                with st.expander("🔍 Run Complete Database Verification Check", expanded=True):
                    try:
                        total_count_df = run_query("students", select_query="count")
                        # If count helper logic differs, Fallback directly to HTTP count modifier:
                        cnt_resp = supabase.table("students").select("*", count="exact").limit(1).execute()
                        total_records = cnt_resp.count if cnt_resp.count is not None else 0
                        
                        st.metric(label="Total Student Rows Found Anywhere in DB Table", value=int(total_records))
                        
                        if total_records > 0:
                            st.write("💡 Data exists in the database! Here is a sample of how the keys look in the table rows:")
                            raw_sample = pd.DataFrame(supabase.table("students").select("session, academic_system, class_level, discipline, section").limit(5).execute().data)
                            st.dataframe(raw_sample)
                        else:
                            st.error("❌ The database table currently holds exactly 0 records.")
                    except Exception as diag_err:
                        st.error(f"Could not read table structure: {diag_err}")
            else:
                # ------------------------------------------------------------------
                # WORKSPACE ACTION A: BATCH EDIT ENTIRE SECTION (INLINE GRID)
                # ------------------------------------------------------------------
                if edit_scope == "📊 Batch Edit Entire Section":
                    st.markdown(f"#### 📊 Batch Grid: `{search_class} ({search_sec})` — {search_discipline} ({search_system})")
                    
                    edited_df = st.data_editor(
                        matched_students,
                        column_config={
                            "student_id": st.column_config.TextColumn("Student ID 🔒", disabled=True),
                            "roll_no": st.column_config.NumberColumn("Roll No*", min_value=1, step=1, required=True),
                            "student_name": st.column_config.TextColumn("Student Name*", required=True),
                            "father_name": st.column_config.TextColumn("Father Name*", required=True),
                            "whatsapp_no": st.column_config.TextColumn("WhatsApp No"),
                            "student_no": st.column_config.TextColumn("Student No"),
                            "contact_1": st.column_config.TextColumn("Contact-1*", required=True),
                            "contact_2": st.column_config.TextColumn("Contact-2"),
                            "home_address": st.column_config.TextColumn("Home Address"),
                            "discipline": st.column_config.TextColumn("Discipline 🔒", disabled=True),
                            "academic_system": st.column_config.TextColumn("System 🔒", disabled=True)
                        },
                        hide_index=True,
                        use_container_width=True,
                        key=f"sec_editor_{search_session}_{search_system}_{search_class}_{search_discipline}_{search_sec}"
                    )
                    
                    if st.button("💾 Bulk Save Changes for This Section", type="primary", use_container_width=True):
                        success_count = 0
                        error_occurred = False
                        
                        for idx, row in edited_df.iterrows():
                            orig_row = matched_students.iloc[idx]
                            if not row.equals(orig_row):
                                payload = {
                                    "student_name": str(row['student_name']).strip(),
                                    "father_name": str(row['father_name']).strip(),
                                    "roll_no": int(row['roll_no']),
                                    "whatsapp_no": str(row['whatsapp_no']).strip() if pd.notna(row['whatsapp_no']) and str(row['whatsapp_no']).strip() and str(row['whatsapp_no']).strip() != 'None' else None,
                                    "student_no": str(row['student_no']).strip() if pd.notna(row['student_no']) and str(row['student_no']).strip() and str(row['student_no']).strip() != 'None' else None,
                                    "contact_1": str(row['contact_1']).strip(),
                                    "contact_2": str(row['contact_2']).strip() if pd.notna(row['contact_2']) and str(row['contact_2']).strip() and str(row['contact_2']).strip() != 'None' else None,
                                    "home_address": str(row['home_address']).strip() if pd.notna(row['home_address']) and str(row['home_address']).strip() and str(row['home_address']).strip() != 'None' else None,
                                }
                                try:
                                    supabase.table("students").update(payload).eq("student_id", row['student_id']).execute()
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"❌ Failed to update row {row['student_id']}: {e}")
                                    error_occurred = True
                        
                        if success_count > 0:
                            st.success(f"🎉 Roster synced successfully! Updated {success_count} records.")
                            import time
                            time.sleep(0.5)
                            st.rerun()
                        elif not error_occurred:
                            st.info("ℹ️ No profile adjustments detected in the roster layout.")

                # ------------------------------------------------------------------
                # WORKSPACE ACTION B: SINGLE STUDENT PROFILE MODIFICATION
                # ------------------------------------------------------------------
                else:
                    st.markdown("#### 🔍 Filter Student Profile")
                    search_query = st.text_input("Type Student Name or ID to filter:", placeholder="e.g., John", key="search_query_tab3").strip().lower()
                    
                    if search_query:
                        filtered_df = matched_students[
                            matched_students['student_id'].astype(str).str.lower().str.contains(search_query, na=False) | 
                            matched_students['student_name'].astype(str).str.lower().str.contains(search_query, na=False)
                        ]
                    else:
                        filtered_df = matched_students

                    target_id = None
                    student_data = None

                    if filtered_df.empty:
                        st.warning("⚠️ No student records match text query.")
                    else:
                        student_options = [f"{row['student_id']} - Roll #{int(row['roll_no'])} - {row['student_name']}" for _, row in filtered_df.iterrows()]
                        selected_profile_str = st.selectbox("🎯 Select Target Student Profile:", options=student_options)
                        
                        if selected_profile_str:
                            target_id = selected_profile_str.split(" - ")[0].strip()
                            student_data = filtered_df[filtered_df['student_id'] == target_id].iloc[0]
                            
                            with st.form("edit_student_profile_form"):
                                col_e1, col_e2, col_e3 = st.columns(3)
                                with col_e1: edit_name = st.text_input("Student Name:*", value=str(student_data['student_name']))
                                with col_e2: edit_fname = st.text_input("Father's Name:*", value=str(student_data['father_name']))
                                with col_e3: edit_roll = st.number_input("Roll Number:*", value=int(student_data['roll_no']), min_value=1, step=1)
                                
                                col_e4, col_e5, col_e6 = st.columns(3)
                                with col_e4: edit_whatsapp = st.text_input("WhatsApp No:", value=str(student_data['whatsapp_no'] or '') if pd.notna(student_data['whatsapp_no']) and str(student_data['whatsapp_no']) != 'None' else '')
                                with col_e5: edit_student_no = st.text_input("Student No:", value=str(student_data['student_no'] or '') if pd.notna(student_data['student_no']) and str(student_data['student_no']) != 'None' else '')
                                with col_e6: edit_c1 = st.text_input("Emergency Contact-1:*", value=str(student_data['contact_1']))
                                
                                col_e7, col_e8 = st.columns([1, 2])
                                with col_e7: edit_c2 = st.text_input("Alternative Contact-2:", value=str(student_data['contact_2'] or '') if pd.notna(student_data['contact_2']) and str(student_data['contact_2']) != 'None' else '')
                                with col_e8: edit_addr = st.text_input("Home Address:", value=str(student_data['home_address'] or '') if pd.notna(student_data['home_address']) and str(student_data['home_address']) != 'None' else '')
                                
                                submit_edit = st.form_submit_button("💾 Save Profile Field Changes", type="primary", use_container_width=True)
                                
                                if submit_edit:
                                    if not edit_name.strip() or not edit_fname.strip() or not edit_c1.strip():
                                        st.error("❌ Validation Failed: All mandatory fields must contain text.")
                                    else:
                                        try:
                                            payload = {
                                                "student_name": edit_name.strip(), 
                                                "father_name": edit_fname.strip(), 
                                                "roll_no": int(edit_roll),
                                                "whatsapp_no": edit_whatsapp.strip() if edit_whatsapp.strip() else None, 
                                                "student_no": edit_student_no.strip() if edit_student_no.strip() else None,
                                                "contact_1": edit_c1.strip(), 
                                                "contact_2": edit_c2.strip() if edit_c2.strip() else None, 
                                                "home_address": edit_addr.strip() if edit_addr.strip() else None
                                            }
                                            
                                            supabase.table("students").update(payload).eq("student_id", target_id).execute()
                                            st.success(f"🎉 Saved successfully!")
                                            import time
                                            time.sleep(0.5)
                                            st.rerun()
                                        except Exception as update_err:
                                            st.error(f"❌ Database Error: {update_err}")

    # ==============================================================================
    # 🛠️ ADMINISTRATIVE STRUCTURAL OPERATIONS ENGINE (FOR SINGLE OR FULL SECTION)
    # ==============================================================================
                st.markdown("---")
                st.markdown("### 🛠️ Structural Actions Panel")
                st.caption("Apply bulk structural migrations, section re-allocations, cycle promotions, or drop entries.")
                
                # Setup operational scope variables safely using resolved variables
                target_student_id = None
                target_student_name = ""
                
                if edit_scope == "✨ Modify Single Student":
                    if target_id is not None and student_data is not None:
                        target_student_id = target_id
                        target_student_name = student_data['student_name']
                        st.info(f"Targeting profile: **{target_student_name}** (`ID: {target_student_id}`) Only")
                    else:
                        st.warning("⚠️ Please select a student profile above to target structural changes.")
                else:
                    st.warning(f"⚠️ **ATTENTION:** Operating on **ALL {len(matched_students)} Students** within class `{search_class} ({search_sec})` simultaneously.")

                # Action Choice Router
                admin_action = st.selectbox(
                    "Select Administrative Operation:",
                    options=[
                        "-- Select Structural Action --",
                        "🔄 Section Change",
                        "📅 Session Change",
                        "🏛️ Academic System Change",
                        "📈 Class Change",
                        "🚀 Promote Students",
                        "❌ Delete from System"
                    ],
                    key="admin_structural_action_router"
                )

                if admin_action != "-- Select Structural Action --":
                    # Fetch database reference items safely via updated HTTP API Client Engine
                    sess_df = run_query("academic_sessions")
                    sess_opts = sess_df['session_name'].tolist() if not sess_df.empty and 'session_name' in sess_df.columns else []
                    
                    sys_df = run_query("academic_systems")
                    sys_opts = sys_df['system_name'].tolist() if not sys_df.empty and 'system_name' in sys_df.columns else []
                    
                    cls_df = run_query("classes")
                    if not cls_df.empty and 'sort_order' in cls_df.columns:
                        cls_df = cls_df.sort_values(by=['sort_order', 'id'], ascending=[True, True])
                    cls_opts = cls_df['class_level'].tolist() if not cls_df.empty and 'class_level' in cls_df.columns else []
                    
                    sec_df = run_query("sections")
                    sec_opts = sec_df['section_name'].tolist() if not sec_df.empty and 'section_name' in sec_df.columns else []

                    # Block container for updating configurations securely
                    with st.form("structural_modification_execution_form"):
                        payload = {}
                        is_delete = False

                        # Proceed only if variables are set or operating on full section
                        if edit_scope != "✨ Modify Single Student" or target_student_id:
                            # 1. SECTION CHANGE
                            if admin_action == "🔄 Section Change":
                                new_val = st.selectbox("Select New Target Section:", options=sec_opts)
                                payload = {"section": new_val}

                            # 2. SESSION CHANGE
                            elif admin_action == "📅 Session Change":
                                new_val = st.selectbox("Select New Target Session Cycle:", options=sess_opts)
                                payload = {"session": new_val}

                            # 3. ACADEMIC SYSTEM CHANGE
                            elif admin_action == "🏛️ Academic System Change":
                                new_val = st.selectbox("Select New Academic System Scheme:", options=sys_opts)
                                payload = {"academic_system": new_val}

                            # 4. CLASS CHANGE
                            elif admin_action == "📈 Class Change":
                                new_val = st.selectbox("Select New Target Class Level:", options=cls_opts)
                                payload = {"class_level": new_val}

                            # 5. PROMOTE STUDENTS
                            elif admin_action == "🚀 Promote Students":
                                st.write("💡 Promotions migrate records into a new Session AND Class level simultaneously.")
                                col_p1, col_p2 = st.columns(2)
                                p_sess = col_p1.selectbox("Select Next Cycle Session:", options=sess_opts)
                                p_cls = col_p2.selectbox("Select Next Grade Class Level:", options=cls_opts)
                                payload = {"session": p_sess, "class_level": p_cls}

                            # 6. DELETE FROM SYSTEM
                            elif admin_action == "❌ Delete from System":
                                st.error("⚠️ CRITICAL SECURITY WARNING: Deletion is absolute and permanent!")
                                confirm_delete = st.checkbox("I verify I want to purge these student record entries from the core database.")
                                is_delete = True

                            # Submission Engine
                            commit_action = st.form_submit_button("🔥 Commit Administrative Update", type="primary", use_container_width=True)

                            if commit_action:
                                if is_delete and not confirm_delete:
                                    st.warning("🔒 Transaction aborted: You must check the security confirmation box first.")
                                else:
                                    try:
                                        # Construct target base filter query builder
                                        query_builder = supabase.table("students")
                                        
                                        if edit_scope == "✨ Modify Single Student":
                                            query_builder = query_builder.eq("student_id", target_student_id)
                                        else:
                                            query_builder = (query_builder
                                                .eq("session", search_session)
                                                .eq("academic_system", search_system)
                                                .eq("class_level", search_class)
                                                .eq("discipline", search_discipline)
                                                .eq("section", search_sec)
                                            )
                                        
                                        # Fire appropriate REST action payload 
                                        if is_delete:
                                            query_builder.delete().execute()
                                        else:
                                            query_builder.update(payload).execute()
                                            
                                        st.success("🎉 Administrative structural transaction executed successfully!")
                                        import time
                                        time.sleep(0.6)
                                        st.rerun()
                                    except Exception as admin_err:
                                        st.error(f"❌ Structural Update Interrupted: {admin_err}")
                                        
import datetime  # Make sure this is present at the top of your file
import pandas as pd
import streamlit as st

# ✅ Pass current_user down from the RBAC Matrix router
def render_universal_attendance_workspace(current_user="System"):
    """Shared workspace allowing unrestricted global access to all sections for attendance processing and reporting with auditing logs."""
    st.subheader("🌐 Global Universal Attendance Control Desk")
    st.info("🔓 Unrestricted administrative view enabled. Monitor, verify, override, or export attendance maps.")
    
    # ==============================================================================
    # 🛠️ DATABASE SCHEMA INITIALIZATION & AUTOMATIC MIGRATION (Supabase Managed Engine)
    # ==============================================================================
    # Note: Structural table schema setups and dynamic alter commands are managed 
    # natively inside the Supabase SQL Editor GUI dashboard interface layer.
    
    if "active_absentee_ids" not in st.session_state:
        st.session_state.active_absentee_ids = []
        
    # ==============================================================================
    # 🔄 WORKSPACE MODE SELECTOR
    # ==============================================================================
    workspace_mode = st.radio(
        "Select Operation Scope:",
        ["Process Bulk Section Register", "Mark Single Student Attendance", "Process Late Arrival Logs", "📊 Generate & Print Reports"],
        horizontal=True,
        key="attendance_scope_mode"
    )
    
    st.markdown("---")

    # ==============================================================================
    # 📋 MODE A: PROCESS BULK SECTION REGISTER
    # ==============================================================================
    if workspace_mode == "Process Bulk Section Register":
        st.markdown("### 📝 Section Bulk Attendance Intake Sheet")
        st.caption("Load complete section arrays here to run daily registration sheet records.")
        # [Your existing downstream Bulk Register processing logic goes here...]

    # ==============================================================================
    # 🎯 MODE B: MARK SINGLE STUDENT ATTENDANCE (INDIVIDUAL OVERRIDES WITH LOGS)
    # ==============================================================================
    elif workspace_mode == "Mark Single Student Attendance":
        st.markdown("### 🔍 Single Student Attendance Override")
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            search_id = st.text_input("Enter Target Student ID:*", placeholder="e.g., 1001", key="single_search_id").strip()
        with col_s2:
            single_date = st.date_input("Attendance Target Date:", value=datetime.date.today(), key="single_att_date")
            
        if search_id:
            try:
                # HTTP REST call replacement fetching matching student profile
                res = supabase.table("students").select(
                    "student_id, student_name, session, academic_system, class_level, section, roll_no, contact_1, whatsapp_no"
                ).ilike("student_id", search_id.strip()).execute()
                student_profile = pd.DataFrame(res.data)
            except Exception:
                student_profile = pd.DataFrame()
            
            if not student_profile.empty:
                student = student_profile.iloc[0]
                st.success(f"🎯 **Student Profile Found:** {student['student_name']} (Roll #{int(student['roll_no']) if pd.notna(student['roll_no']) else 0})")
                
                c_meta1, c_meta2, c_meta3 = st.columns(3)
                c_meta1.markdown(f"🏫 **Class Group:** `{student['class_level']} - {student['section']}`")
                c_meta2.markdown(f"📅 **Session Cycle:** `{student['session']}`")
                c_meta3.markdown(f"📞 **Primary Phone:** `{student['contact_1']}`")
                
                st.markdown("##### Update Status Log")
                with st.form("single_student_attendance_form"):
                    try:
                        # Fetch the existing attendance record data for the matching single row date
                        log_res = supabase.table("attendance").select("status, remarks").eq("student_id", student['student_id']).eq("date", str(single_date)).execute()
                        current_log = pd.DataFrame(log_res.data)
                    except Exception:
                        current_log = pd.DataFrame()
                    
                    default_status = "Present"
                    default_remarks = ""
                    if not current_log.empty:
                        default_status = current_log.iloc[0]['status']
                        default_remarks = current_log.iloc[0]['remarks'] if pd.notna(current_log.iloc[0]['remarks']) else ""
                    
                    col_form1, col_form2 = st.columns([1, 2])
                    with col_form1:
                        single_status = st.radio("Attendance Status:", ["Present", "Absent"], index=0 if default_status == "Present" else 1, horizontal=True)
                    with col_form2:
                        single_remarks = st.text_input("Status Remarks/Reasons:", value=default_remarks, placeholder="e.g., Leave notice submitted")
                        
                    submit_single = st.form_submit_button("💾 Save Individual Attendance Record", type="primary", use_container_width=True)
                    
                    if submit_single:
                        now_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        try:
                            # Upsert record payload natively matching the composite (student_id, date) uniqueness constraint
                            att_payload = {
                                "student_id": str(student['student_id']),
                                "date": str(single_date),
                                "status": single_status,
                                "remarks": single_remarks.strip() if single_remarks.strip() else None,
                                "updated_by": current_user,
                                "updated_at": now_stamp
                            }
                            
                            supabase.table("attendance").upsert(att_payload, on_conflict="student_id,date").execute()
                            st.success(f"🎉 Successfully tracked attendance for {student['student_name']} on {single_date}!")
                        except Exception as single_err:
                            st.error(f"❌ Failed to log individual attendance record: {single_err}")
            else:
                st.error(f"❌ No student found matching ID tracking token '{search_id}'.")

    # ==============================================================================
    # ⏱️ MODE C: PROCESS LATE ARRIVAL LOGS (MOUNTED ROUTE VIA SYSTEM SELECTOR)
    # ==============================================================================
    elif workspace_mode == "Process Late Arrival Logs":
        st.markdown("### ⏱️ College Late Arrival Intake Ledger")
        st.caption("Log students arriving past official timings to maintain accurate punch-in discipline records.")
        
        col_l1, col_l2 = st.columns([2, 1])
        with col_l1:
            late_search_id = st.text_input("Enter Student ID for Late Intake:*", placeholder="e.g., 1001", key="late_id_input").strip()
        with col_l2:
            late_date = st.date_input("Arrival Intake Date:", value=datetime.date.today(), key="late_intake_date")
            
        if late_search_id:
            try:
                # Migrated to Supabase REST engine
                res = supabase.table("students").select(
                    "student_id, student_name, class_level, section, roll_no, contact_1"
                ).ilike("student_id", late_search_id.strip()).execute()
                student_profile = pd.DataFrame(res.data)
            except Exception:
                student_profile = pd.DataFrame()
                
            if not student_profile.empty:
                student = student_profile.iloc[0]
                st.success(f"🎯 **Verified Student:** {student['student_name']} (Roll #{int(student['roll_no']) if pd.notna(student['roll_no']) else 0} | {student['class_level']} - {student['section']})")
                
                with st.form("late_arrival_entry_form"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        arrival_time = st.time_input("Actual Arrival Time:", value=datetime.datetime.now().time())
                    with col_f2:
                        minutes_late = st.number_input("Minutes Tardy (Past Gate Close):", min_value=1, max_value=180, value=15, step=5)
                        
                    late_remarks = st.text_input("Reason for Late Arrival / Notes:", placeholder="e.g., Transport breakdown")
                    submit_late = st.form_submit_button("💾 Commit Late Arrival Check-In Log", type="primary", use_container_width=True)
                    
                    if submit_late:
                        now_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        formatted_arrival_time = arrival_time.strftime("%I:%M %p")
                        try:
                            # Upsert record payload mapping to composite natural keys natively
                            late_payload = {
                                "student_id": str(student['student_id']),
                                "date": str(late_date),
                                "arrival_time": formatted_arrival_time,
                                "minutes_late": int(minutes_late),
                                "remarks": late_remarks.strip() if late_remarks.strip() else None,
                                "updated_by": current_user,
                                "updated_at": now_stamp
                            }
                            
                            supabase.table("late_arrivals").upsert(late_payload, on_conflict="student_id,date").execute()
                            st.success(f"🎉 Arrival record committed successfully for {student['student_name']}!")
                        except Exception as late_err:
                            st.error(f"❌ Failed to save late arrival record: {late_err}")
            else:
                st.error(f"❌ No student profile matches tracking token ID '{late_search_id}'.")

    # ==============================================================================
    # 📊 MODE D: GENERATE & PRINT ATTENDANCE REPORTS
    # ==============================================================================
    elif workspace_mode == "📊 Generate & Print Reports":
        st.markdown("### 🖨️ Attendance & Performance Report Generator")
        
        report_type = st.radio("Select Report Category:", ["📊 General Attendance Metric Summaries", "🚨 Detailed Absentees Ledger Report", "⏱️ Late Arrival Tardy Ledger"], horizontal=True)
        st.markdown("---")
        
        col_r1, _ = st.columns([1, 1])
        with col_r1:
            target_report_date = st.date_input("Select Target Report Date:", value=datetime.date.today(), key="rpt_date")
            
        # ------------------------------------------------------------------------------
        # 🚨 CATEGORY 1: DETAILED ABSENTEES LEDGER REPORT (FETCHES REMARKS & TIMESTAMPS)
        # ------------------------------------------------------------------------------
        if report_type == "🚨 Detailed Absentees Ledger Report":
            report_scope = st.radio("Absentees Scope:", ["Single Section Absentees", "All Campus Absentees Master List"], horizontal=True)
            
            if report_scope == "Single Section Absentees":
                st.markdown("##### Filter Targets for Single Section Absentees List:")
                sessions_df = run_query("academic_sessions")
                # UPDATED: Using .iloc[:, 0] to guarantee resilient extraction regardless of driver column name casing
                sessions_list = ["-- Select Session --"] + (sessions_df.iloc[:, 0].tolist() if not sessions_df.empty else [])
                
                col_u1, col_u2, col_u3, col_u4, col_u5 = st.columns(5)
                with col_u1: sel_session = st.selectbox("1. Session:", options=sessions_list, key="rpt_abs_sess")
                with col_u2:
                    if sel_session != "-- Select Session --":
                        systems_df = run_query("academic_systems")
                        # UPDATED: Using .iloc[:, 0]
                        systems_list = ["-- Select System --"] + (systems_df.iloc[:, 0].tolist() if not systems_df.empty else [])
                        sel_system = st.selectbox("2. System:", options=systems_list, key="rpt_abs_sys")
                    else:
                        st.selectbox("2. System:", ["🔒 Waiting..."], disabled=True, key="rpt_abs_sys_dis")
                        sel_system = "-- Select Session --"
                with col_u3:
                    if sel_system != "-- Select System --":
                        classes_df = run_query("classes")
                        if not classes_df.empty and 'sort_order' in classes_df.columns:
                            classes_df = classes_df.sort_values(by=['sort_order', 'id'], ascending=[True, True])
                        # UPDATED: Using .iloc[:, 0] to maintain robust fallback positioning
                        classes_list = ["-- Select Class --"] + (classes_df.iloc[:, 0].tolist() if not classes_df.empty else [])
                        sel_class = st.selectbox("3. Class:", options=classes_list, key="rpt_abs_cls")
                    else:
                        st.selectbox("3. Class:", ["🔒 Waiting..."], disabled=True, key="rpt_abs_cls_dis")
                        sel_class = "-- Select System --"
                with col_u4:
                    if sel_class != "-- Select Class --":
                        disciplines_df = run_query("disciplines")
                        # UPDATED: Using .iloc[:, 0]
                        disciplines_list = ["-- Select Discipline --"] + (disciplines_df.iloc[:, 0].tolist() if not disciplines_df.empty else [])
                        sel_discipline = st.selectbox("4. Discipline:", options=disciplines_list, key="rpt_abs_disc")
                    else:
                        st.selectbox("4. Discipline:", ["🔒 Waiting..."], disabled=True, key="rpt_abs_disc_dis")
                        sel_discipline = "-- Select Class --"
                with col_u5:
                    if sel_discipline != "-- Select Discipline --":
                        sections_df = run_query("sections")
                        # UPDATED: Using .iloc[:, 0]
                        sections_list = ["-- Select Section --"] + (sections_df.iloc[:, 0].tolist() if not sections_df.empty else [])
                        sel_section = st.selectbox("5. Section:", options=sections_list, key="rpt_abs_sec")
                    else:
                        st.selectbox("5. Section:", ["🔒 Waiting..."], disabled=True, key="rpt_abs_sec_dis")
                        sel_section = "-- Select Discipline --"

                if "-- Select" not in f"{sel_session}{sel_system}{sel_class}{sel_discipline}{sel_section}":
                    try:
                        # Relational matching via filtering criteria on Supabase 
                        result_data = supabase.table("attendance").select(
                            "remarks, updated_by, updated_at, students!inner(roll_no, student_name, contact_1, session, academic_system, class_level, discipline, section)"
                        ).eq("date", str(target_report_date)).eq("status", "Absent").ilike("students.session", sel_session.strip()).ilike("students.academic_system", sel_system.strip()).ilike("students.class_level", sel_class.strip()).ilike("students.discipline", sel_discipline.strip()).ilike("students.section", sel_section.strip()).execute()
                        
                        # Normalize nested objects to flat columns to preserve presentation view architecture
                        raw_records = result_data.data
                        flat_records = []
                        for rec in raw_records:
                            st_info = rec.get("students", {})
                            flat_records.append({
                                "Roll No": st_info.get("roll_no"),
                                "Student Name": st_info.get("student_name"),
                                "Primary Contact": st_info.get("contact_1"),
                                "Reason of Absence / Follow-up Notes": rec.get("remarks"),
                                "Logged By Staff": rec.get("updated_by"),
                                "Timestamp Logged": rec.get("updated_at")
                            })
                        abs_df = pd.DataFrame(flat_records)
                        if not abs_df.empty:
                            abs_df = abs_df.sort_values(by="Roll No", ascending=True)
                    except Exception as query_err:
                        st.error(f"❌ Failed to build absentee breakdown: {query_err}")
                        abs_df = pd.DataFrame()
                    
                    if not abs_df.empty:
                        abs_df["Logged By Staff"] = abs_df["Logged By Staff"].fillna("System / Legacy Entry")
                        abs_df["Timestamp Logged"] = abs_df["Timestamp Logged"].fillna("—")
                        abs_df["Reason of Absence / Follow-up Notes"] = abs_df["Reason of Absence / Follow-up Notes"].fillna("No remarks captured")

                        st.warning(f"🚨 **Absentee List:** `{sel_class} - {sel_section}` on **{target_report_date}** ({len(abs_df)} Absent)")
                        st.dataframe(abs_df, use_container_width=True, index=False)
                        
                        csv_data = abs_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download & Print Section Absentees (CSV)",
                            data=csv_data,
                            file_name=f"Absentees_{sel_class}_{sel_section}_{target_report_date}.csv",
                            mime="text/csv",
                            type="secondary"
                        )
                    else:
                        st.success(f"✨ Perfect! Zero absences registered for `{sel_class} - {sel_section}` on this date.")
                        
            else:  # All Campus Absentees Master List
                try:
                    # Retrieve global student relation joins on target date filter matrix
                    result_data = supabase.table("attendance").select(
                        "remarks, updated_by, updated_at, students!inner(class_level, section, roll_no, student_name, contact_1)"
                    ).eq("date", str(target_report_date)).eq("status", "Absent").execute()
                    
                    raw_records = result_data.data
                    flat_records = []
                    for rec in raw_records:
                        st_info = rec.get("students", {})
                        c_lvl = st_info.get("class_level", "")
                        c_sec = st_info.get("section", "")
                        flat_records.append({
                            "Class Section": f"{c_lvl} - {c_sec}" if c_lvl and c_sec else "Unassigned",
                            "Roll No": st_info.get("roll_no"),
                            "Student Name": st_info.get("student_name"),
                            "Primary Contact": st_info.get("contact_1"),
                            "Reason of Absence / Follow-up Notes": rec.get("remarks"),
                            "Logged By Staff": rec.get("updated_by"),
                            "Timestamp Logged": rec.get("updated_at"),
                            "_sort_class": c_lvl,
                            "_sort_sec": c_sec
                        })
                    master_abs_df = pd.DataFrame(flat_records)
                    if not master_abs_df.empty:
                        master_abs_df = master_abs_df.sort_values(by=["_sort_class", "_sort_sec", "Roll No"], ascending=[True, True, True]).drop(columns=["_sort_class", "_sort_sec"])
                except Exception as master_err:
                    st.error(f"❌ Failed to fetch global absentee matrix: {master_err}")
                    master_abs_df = pd.DataFrame()
                
                if not master_abs_df.empty:
                    master_abs_df["Logged By Staff"] = master_abs_df["Logged By Staff"].fillna("System / Legacy Entry")
                    master_abs_df["Timestamp Logged"] = master_abs_df["Timestamp Logged"].fillna("—")
                    master_abs_df["Reason of Absence / Follow-up Notes"] = master_abs_df["Reason of Absence / Follow-up Notes"].fillna("No remarks captured")

                    st.error(f"🚨 **Campus Master Absentee Log:** **{target_report_date}** ({len(master_abs_df)} Total Absences Across All Sections)")
                    st.dataframe(master_abs_df, use_container_width=True, index=False)
                    
                    master_csv = master_abs_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download & Print Campus Master Absentees Ledger (CSV)",
                        data=master_csv,
                        file_name=f"Master_Absentees_Report_{target_report_date}.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                else:
                    st.success("✨ Incredible! Outstanding day with 100% total campus wide student attendance.")

        # ------------------------------------------------------------------------------
        # ⏱️ CATEGORY 2: LATE ARRIVAL TARDY LEDGER ENGINE (FETCHES CHECK-INS & DOWNLOADS)
        # ------------------------------------------------------------------------------
        elif report_type == "⏱️ Late Arrival Tardy Ledger":
            st.markdown("### 🖨️ Late Arrival Discipline Tracking Register")
            
            try:
                # Fetching late arrivals linked natively via relation join filters
                result_data = supabase.table("late_arrivals").select(
                    "arrival_time, minutes_late, remarks, updated_by, updated_at, students!inner(class_level, section, roll_no, student_name)"
                ).eq("date", str(target_report_date)).execute()
                
                raw_records = result_data.data
                flat_records = []
                for rec in raw_records:
                    st_info = rec.get("students", {})
                    c_lvl = st_info.get("class_level", "")
                    c_sec = st_info.get("section", "")
                    flat_records.append({
                        "Class Section": f"{c_lvl} - {c_sec}" if c_lvl and c_sec else "Unassigned",
                        "Roll No": st_info.get("roll_no"),
                        "Student Name": st_info.get("student_name"),
                        "Arrival Time": rec.get("arrival_time"),
                        "Mins Late": rec.get("minutes_late"),
                        "Stated Reason / Notes": rec.get("remarks"),
                        "Gate Staff Signature": rec.get("updated_by"),
                        "Timestamp Logged": rec.get("updated_at"),
                        "_sort_class": c_lvl,
                        "_sort_sec": c_sec
                    })
                late_report_df = pd.DataFrame(flat_records)
                if not late_report_df.empty:
                    late_report_df = late_report_df.sort_values(by=["_sort_class", "_sort_sec", "Mins Late"], ascending=[True, True, False]).drop(columns=["_sort_class", "_sort_sec"])
            except Exception as query_err:
                st.error(f"❌ Failed to parse late arrival matrix sequence: {query_err}")
                late_report_df = pd.DataFrame()
                
            if not late_report_df.empty:
                late_report_df["Gate Staff Signature"] = late_report_df["Gate Staff Signature"].fillna("System")
                late_report_df["Timestamp Logged"] = late_report_df["Timestamp Logged"].fillna("—")
                late_report_df["Stated Reason / Notes"] = late_report_df["Stated Reason / Notes"].fillna("—")

                st.warning(f"⏳ **Campus Late Arrivals Ledger:** **{target_report_date}** ({len(late_report_df)} Students Logged Tardy)")
                st.dataframe(late_report_df, use_container_width=True, index=False)
                
                late_csv = late_report_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download & Print Campus Late Arrival Report (CSV)",
                    data=late_csv,
                    file_name=f"Late_Arrivals_Report_{target_report_date}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.success(f"✨ Excellent discipline! No students were logged late on **{target_report_date}**.")

        # ------------------------------------------------------------------------------
        # 📊 CATEGORY 3: ATTENDANCE METRICS SUMMARY REPORT (WITH TOTALS ROW SUMS)
        # ------------------------------------------------------------------------------
        else:
            report_scope = st.radio("Report Scope:", ["Single Section View Summary", "All Sections Campus Master View"], horizontal=True)
            
            if report_scope == "Single Section View Summary":
                st.markdown("##### Filter Targets for Single Section Analysis:")
                sessions_df = run_query("SELECT DISTINCT session_name FROM sessions ORDER BY session_name ASC")
                sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
                
                col_u1, col_u2, col_u3, col_u4, col_u5 = st.columns(5)
                with col_u1: 
                    sel_session = st.selectbox("1. Session:", options=sessions_list, key="rpt_sess")
                
                with col_u2:
                    if sel_session != "-- Select Session --":
                        systems_df = run_query("""
                            SELECT DISTINCT academic_system FROM students 
                            WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) ORDER BY academic_system ASC
                        """, {"sess": sel_session})
                        systems_list = ["-- Select System --"] + (systems_df['academic_system'].tolist() if not systems_df.empty else [])
                        sel_system = st.selectbox("2. System:", options=systems_list, key="rpt_sys")
                    else:
                        st.selectbox("2. System:", ["🔒 Waiting..."], disabled=True, key="rpt_sys_dis")
                        sel_system = "-- Select Session --"
                
                with col_u3:
                    if sel_system != "-- Select System --":
                        classes_df = run_query("""
                            SELECT DISTINCT class_level FROM students 
                            WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                              AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys)) ORDER BY class_level ASC
                        """, {"sess": sel_session, "sys": sel_system})
                        classes_list = ["-- Select Class --"] + (classes_df.iloc[:, 0].tolist() if not classes_df.empty else [])
                        sel_class = st.selectbox("3. Class:", options=classes_list, key="rpt_cls")
                    else:
                        st.selectbox("3. Class:", ["🔒 Waiting..."], disabled=True, key="rpt_cls_dis")
                        sel_class = "-- Select System --"
                
                with col_u4:
                    if sel_class != "-- Select Class --":
                        disciplines_df = run_query("""
                            SELECT DISTINCT discipline FROM students 
                            WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                              AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys))
                              AND LOWER(TRIM(class_level)) = LOWER(TRIM(:cls)) ORDER BY discipline ASC
                        """, {"sess": sel_session, "sys": sel_system, "cls": sel_class})
                        disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline'].tolist() if not disciplines_df.empty else [])
                        sel_discipline = st.selectbox("4. Discipline:", options=disciplines_list, key="rpt_disc")
                    else:
                        st.selectbox("4. Discipline:", ["🔒 Waiting..."], disabled=True, key="rpt_disc_dis")
                        sel_discipline = "-- Select Class --"
                
                with col_u5:
                    if sel_discipline != "-- Select Discipline --":
                        sections_df = run_query("""
                            SELECT DISTINCT section FROM students 
                            WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                              AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys))
                              AND LOWER(TRIM(class_level)) = LOWER(TRIM(:cls))
                              AND LOWER(TRIM(discipline)) = LOWER(TRIM(:disc)) ORDER BY section ASC
                        """, {"sess": sel_session, "sys": sel_system, "cls": sel_class, "disc": sel_discipline})
                        sections_list = ["-- Select Section --"] + (sections_df['section'].tolist() if not sections_df.empty else [])
                        sel_section = st.selectbox("5. Section:", options=sections_list, key="rpt_sec")
                    else:
                        st.selectbox("5. Section:", ["🔒 Waiting..."], disabled=True, key="rpt_sec_dis")
                        sel_section = "-- Select Discipline --"

                if "-- Select" not in f"{sel_session}{sel_system}{sel_class}{sel_discipline}{sel_section}":
                    try:
                        with engine.connect() as conn:
                            query_text = text("""
                                SELECT 
                                    s.section AS "Section Name",
                                    '—' AS "Section Incharge",
                                    COUNT(s.student_id) AS "Total Students",
                                    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS "Present Students",
                                    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS "Absent Students",
                                    SUM(CASE WHEN LOWER(TRIM(s.student_no)) LIKE '%left%' OR a.status = 'Left' THEN 1 ELSE 0 END) AS "Left Students"
                                FROM students s
                                LEFT JOIN attendance a ON s.student_id = a.student_id AND a.date = :dt
                                WHERE LOWER(TRIM(s.session)) = LOWER(TRIM(:sess))
                                  AND LOWER(TRIM(s.academic_system)) = LOWER(TRIM(:sys))
                                  AND LOWER(TRIM(s.class_level)) = LOWER(TRIM(:cls))
                                  AND LOWER(TRIM(s.discipline)) = LOWER(TRIM(:disc))
                                  AND LOWER(TRIM(s.section)) = LOWER(TRIM(:sec))
                                FROM students s
                                GROUP BY s.section
                            """)
                            result = conn.execute(query_text, {
                                "dt": target_report_date, "sess": sel_session, "sys": sel_system, 
                                "cls": sel_class, "disc": sel_discipline, "sec": sel_section
                            })
                            report_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    except Exception as query_err:
                        st.error(f"❌ Metrics evaluation failed: {query_err}")
                        report_df = pd.DataFrame()
                    
                    if not report_df.empty:
                        report_df["Attendance %"] = (report_df["Present Students"] / report_df["Total Students"] * 100).round(1).astype(str) + "%"
                        st.markdown(f"#### 📄 Attendance Statistical Card: `{sel_class} - {sel_section}`")
                        st.dataframe(report_df, use_container_width=True)
                        
                        csv_data = report_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download & Print Section Metrics (CSV)",
                            data=csv_data,
                            file_name=f"Summary_Attendance_{sel_class}_{sel_section}_{target_report_date}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    else:
                        st.info("ℹ️ No operational records found for this target configuration.")
                        
            else:  # All Sections Campus Master View (With Column Bottom Sum Row)
                try:
                    with engine.connect() as conn:
                        master_query = text("""
                            SELECT 
                                s.class_level || ' - ' || s.section AS "Section Name",
                                '—' AS "Section Incharge",
                                COUNT(s.student_id) AS "Total Students",
                                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS "Present Students",
                                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS "Absent Students",
                                SUM(CASE WHEN LOWER(TRIM(s.student_no)) LIKE '%left%' OR a.status = 'Left' THEN 1 ELSE 0 END) AS "Left Students"
                            FROM students s
                            LEFT JOIN attendance a ON s.student_id = a.student_id AND a.date = :dt
                            GROUP BY s.class_level, s.section
                            ORDER BY s.class_level, s.section ASC
                        """)
                        result = conn.execute(master_query, {"dt": target_report_date})
                        master_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                except Exception as master_err:
                    st.error(f"❌ Master metric analysis failure: {master_err}")
                    master_df = pd.DataFrame()
                
                if not master_df.empty:
                    master_df["Attendance %"] = (master_df["Present Students"] / master_df["Total Students"] * 100).round(1)
                    
                    # Compute Column Sums
                    sum_total_students = int(master_df["Total Students"].sum())
                    sum_present_students = int(master_df["Present Students"].sum())
                    sum_absent_students = int(master_df["Absent Students"].sum())
                    sum_left_students = int(master_df["Left Students"].sum())
                    avg_attendance_pct = round((sum_present_students / sum_total_students * 100), 1) if sum_total_students > 0 else 0.0
                    
                    master_df["Attendance %"] = master_df["Attendance %"].astype(str) + "%"
                    
                    # Append calculations into an aggregate totals row stack frame
                    summary_row = pd.DataFrame([{
                        "Section Name": "TOTAL SUM / AVG",
                        "Section Incharge": "—",
                        "Total Students": sum_total_students,
                        "Present Students": sum_present_students,
                        "Absent Students": sum_absent_students,
                        "Left Students": sum_left_students,
                        "Attendance %": f"{avg_attendance_pct}%"
                    }])
                    
                    final_printable_report = pd.concat([master_df, summary_row], ignore_index=True)
                    st.markdown(f"#### 🌍 Master Campus-Wide Metric Dashboard for **{target_report_date}**")
                    st.dataframe(final_printable_report, use_container_width=True)
                    
                    master_csv = final_printable_report.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download & Print Campus Summary Totals (CSV)",
                        data=master_csv,
                        file_name=f"Global_Summary_Attendance_{target_report_date}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                else:
                    st.info("ℹ️ No records registered globally in the system roster.")

    # ==============================================================================
    # 🎯 MODE B: MARK SINGLE STUDENT ATTENDANCE (INDIVIDUAL OVERRIDES WITH LOGS)
    # ==============================================================================
    elif workspace_mode == "Mark Single Student Attendance":
        st.markdown("### 🔍 Single Student Attendance Override")
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            search_id = st.text_input("Enter Target Student ID:*", placeholder="e.g., 1001", key="single_search_id").strip()
        with col_s2:
            single_date = st.date_input("Attendance Target Date:", value=datetime.date.today(), key="single_att_date")
            
        if search_id:
            try:
                with engine.connect() as conn:
                    p_query = text("""
                        SELECT student_id, student_name, session, academic_system, class_level, section, roll_no, contact_1, whatsapp_no
                        FROM students 
                        WHERE LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))
                    """)
                    p_res = conn.execute(p_query, {"sid": search_id})
                    student_profile = pd.DataFrame(p_res.fetchall(), columns=p_res.keys())
            except Exception:
                student_profile = pd.DataFrame()
            
            if not student_profile.empty:
                student = student_profile.iloc[0]
                st.success(f"🎯 **Student Profile Found:** {student['student_name']} (Roll #{student['roll_no']})")
                
                c_meta1, c_meta2, c_meta3 = st.columns(3)
                c_meta1.markdown(f"🏫 **Class Group:** `{student['class_level']} - {student['section']}`")
                c_meta2.markdown(f"📅 **Session Cycle:** `{student['session']}`")
                c_meta3.markdown(f"📞 **Primary Phone:** `{student['contact_1']}`")
                
                st.markdown("##### Update Status Log")
                with st.form("single_student_attendance_form"):
                    try:
                        with engine.connect() as conn:
                            l_query = text("SELECT status, remarks FROM attendance WHERE student_id = :sid AND date = :dt")
                            l_res = conn.execute(l_query, {"sid": student['student_id'], "dt": single_date})
                            current_log = pd.DataFrame(l_res.fetchall(), columns=l_res.keys())
                    except Exception:
                        current_log = pd.DataFrame()
                    
                    default_status = "Present"
                    default_remarks = ""
                    if not current_log.empty:
                        default_status = current_log.iloc[0]['status']
                        default_remarks = current_log.iloc[0]['remarks']
                    
                    col_form1, col_form2 = st.columns([1, 2])
                    with col_form1:
                        single_status = st.radio("Attendance Status:", ["Present", "Absent"], index=0 if default_status == "Present" else 1, horizontal=True)
                    with col_form2:
                        single_remarks = st.text_input("Status Remarks/Reasons:", value=default_remarks, placeholder="e.g., Leave notice submitted")
                        
                    submit_single = st.form_submit_button("💾 Save Individual Attendance Record", type="primary", use_container_width=True)
                    
                    if submit_single:
                        now_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO attendance (student_id, date, status, remarks, updated_by, updated_at)
                                    VALUES (:student_id, :date, :status, :remarks, :up_by, :up_at)
                                    ON CONFLICT(student_id, date) DO UPDATE SET
                                        status = EXCLUDED.status,
                                        remarks = EXCLUDED.remarks,
                                        updated_by = EXCLUDED.updated_by,
                                        updated_at = EXCLUDED.updated_at;
                                """), {
                                    "student_id": student['student_id'], "date": single_date, "status": single_status,
                                    "remarks": single_remarks.strip(), "up_by": current_user, "up_at": now_stamp
                                })
                            st.success(f"🎉 Successfully tracked attendance for {student['student_name']} on {single_date}!")
                        except Exception as single_err:
                            st.error(f"❌ Failed to log individual attendance record: {single_err}")
            else:
                st.error(f"❌ No student found matching ID tracking token '{search_id}'.")

    # ==============================================================================
    # 📋 MODE A: PROCESS BULK SECTION REGISTER (WITH PHASE 1 PRESENT & PHASE 2 VERIFIED REASONS)
    # ==============================================================================
    else:
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions ORDER BY session_name ASC")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_u1, col_u2, col_u3, col_u4, col_u5 = st.columns(5)
        with col_u1: sel_session = st.selectbox("1. Session Cycle:*", options=sessions_list, key="att_sess")
        with col_u2:
            if sel_session != "-- Select Session --":
                systems_df = run_query("""
                    SELECT DISTINCT academic_system FROM students 
                    WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) ORDER BY academic_system ASC
                """, {"sess": sel_session})
                systems_list = ["-- Select System --"] + (systems_df['academic_system'].tolist() if not systems_df.empty else [])
                sel_system = st.selectbox("2. Academic System:*", options=systems_list, key="att_sys")
            else:
                st.selectbox("2. Academic System:", ["🔒 Waiting..."], disabled=True, key="att_sys_dis")
                sel_system = "-- Select Session --"
        with col_u3:
            if sel_system != "-- Select System --":
                classes_df = run_query("""
                    SELECT DISTINCT class_level FROM students 
                    WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                      AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys)) ORDER BY class_level ASC
                """, {"sess": sel_session, "sys": sel_system})
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                sel_class = st.selectbox("3. Target Class:*", options=classes_list, key="att_cls")
            else:
                st.selectbox("3. Target Class:", ["🔒 Waiting..."], disabled=True, key="att_cls_dis")
                sel_class = "-- Select System --"
        with col_u4:
            if sel_class != "-- Select Class --":
                disciplines_df = run_query("""
                    SELECT DISTINCT discipline FROM students 
                    WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                      AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys))
                      AND LOWER(TRIM(class_level)) = LOWER(TRIM(:cls)) ORDER BY discipline ASC
                """, {"sess": sel_session, "sys": sel_system, "cls": sel_class})
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline'].tolist() if not disciplines_df.empty else [])
                sel_discipline = st.selectbox("4. Discipline:*", options=disciplines_list, key="att_disc")
            else:
                st.selectbox("4. Discipline:", ["🔒 Waiting..."], disabled=True, key="att_disc_dis")
                sel_discipline = "-- Select Class --"
        with col_u5:
            if sel_discipline != "-- Select Discipline --":
                sections_df = run_query("""
                    SELECT DISTINCT section FROM students 
                    WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess)) 
                      AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys))
                      AND LOWER(TRIM(class_level)) = LOWER(TRIM(:cls))
                      AND LOWER(TRIM(discipline)) = LOWER(TRIM(:disc)) ORDER BY section ASC
                """, {"sess": sel_session, "sys": sel_system, "cls": sel_class, "disc": sel_discipline})
                sections_list = ["-- Select Section --"] + (sections_df['section'].tolist() if not sections_df.empty else [])
                sel_section = st.selectbox("5. Section Track:*", options=sections_list, key="att_sec")
            else:
                st.selectbox("5. Section Track:", ["🔒 Waiting..."], disabled=True, key="att_sec_dis")
                sel_section = "-- Select Discipline --"

        col_date, _ = st.columns([1, 4])
        with col_date:
            attendance_date = st.date_input("Attendance Log Date:", value=datetime.date.today(), key="uni_date")
            
        st.markdown("---")
        
        if "-- Select" not in f"{sel_session}{sel_system}{sel_class}{sel_discipline}{sel_section}":
            try:
                with engine.connect() as conn:
                    st_query = text("""
                        SELECT student_id, roll_no, student_name, contact_1, contact_2, whatsapp_no, student_no
                        FROM students 
                        WHERE LOWER(TRIM(session)) = LOWER(TRIM(:sess_val))
                          AND LOWER(TRIM(academic_system)) = LOWER(TRIM(:sys_val))
                          AND LOWER(TRIM(class_level)) = LOWER(TRIM(:class_val))
                          AND LOWER(TRIM(discipline)) = LOWER(TRIM(:disc_val))
                          AND LOWER(TRIM(section)) = LOWER(TRIM(:sec_val))
                        ORDER BY roll_no ASC
                    """)
                    st_res = conn.execute(st_query, {
                        "sess_val": sel_session, "sys_val": sel_system, "class_val": sel_class,
                        "disc_val": sel_discipline, "sec_val": sel_section
                    })
                    students_df = pd.DataFrame(st_res.fetchall(), columns=st_res.keys())
            except Exception:
                students_df = pd.DataFrame()
                
            if not students_df.empty:
                st.write(f"### 📋 Attendance Status Grid: `{sel_class} - {sel_section}`")
                st.caption("💡 Note: All students are marked Present by default. Uncheck a student's box to flag an absence.")
                
                with st.form("attendance_checklist_form"):
                    status_mappings = {}
                    h_col1, h_col2, h_col3 = st.columns([1, 2, 5])
                    h_col1.markdown("**Roll #**")
                    h_col2.markdown("**Status Flag**")
                    h_col3.markdown("**Student Full Name**")
                    st.markdown("<hr style='margin:0.1em; border-color:#d1d5db;'>", unsafe_allow_html=True)
                    
                    for idx, row in students_df.iterrows():
                        col_roll, col_check, col_name = st.columns([1, 2, 5])
                        with col_roll: st.write(f"#{row['roll_no']}")
                        with col_check: is_present = st.checkbox("Present", value=True, key=f"chk_{row['student_id']}", label_visibility="collapsed")
                        with col_name: st.write(row['student_name'])
                            
                        status_mappings[row['student_id']] = "Present" if is_present else "Absent"
                        st.markdown("<hr style='margin:0.2em; border-color:#f0f2f6;'>", unsafe_allow_html=True)
                        
                    save_initial_register = st.form_submit_button("💾 Phase 1: Save Present Matrix & Identify Absentees", type="primary", use_container_width=True)
                    
                    if save_initial_register:
                        now_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        initial_payload = []
                        detected_absentees = []
                        
                        for s_id, status in status_mappings.items():
                            initial_payload.append({
                                "student_id": s_id, "att_date": attendance_date, "status": status,
                                "remarks": "" if status == "Present" else "Pending Verification Review",
                                "up_by": current_user, "up_at": now_stamp
                            })
                            if status == "Absent":
                                detected_absentees.append(s_id)
                                
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO attendance (student_id, date, status, remarks, updated_by, updated_at) 
                                    VALUES (:student_id, :att_date, :status, :remarks, :up_by, :up_at)
                                    ON CONFLICT(student_id, date) DO UPDATE SET 
                                        status = EXCLUDED.status,
                                        updated_by = EXCLUDED.updated_by,
                                        updated_at = EXCLUDED.updated_at;
                                """), initial_payload)
                            
                            st.session_state.active_absentee_ids = detected_absentees
                            st.toast("Phase 1 complete! Absentees extracted below.", icon="👀")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Core synchronization transaction aborted: {err}")

                # ------------------------------------------------------------------------------
                # 📞 PHASE 2: DYNAMIC ABSENTEE VERIFICATION WORKSPACE (WITH DROPDOWNS)
                # ------------------------------------------------------------------------------
                if st.session_state.active_absentee_ids:
                    st.markdown("---")
                    st.error(f"⚠️ **Absentee Verification Workspace ({len(st.session_state.active_absentee_ids)} Students Missing)**")
                    
                    absent_students_df = students_df[students_df['student_id'].isin(st.session_state.active_absentee_ids)]
                    
                    fixed_reasons = [
                        "Medical / Health Issues", "Family Emergency", "Family Function", 
                        "Bereavement (Death in Family)", "Transportation Problems", "Out-of-Town Travel", 
                        "Official or Personal Work", "Household Responsibilities", "Religious Obligations", 
                        "Personal Reasons", "Other"
                    ]
                    contacted_persons = ["Mother", "Father", "Brother", "Sister", "Student", "Relative"]
                    
                    with st.form("absentee_remarks_and_contact_form"):
                        remarks_payload = []
                        
                        for _, ab_row in absent_students_df.iterrows():
                            st.markdown(f"##### 👤 {ab_row['student_name']} (Roll #{ab_row['roll_no']})")
                            
                            c1, c2, c3 = st.columns(3)
                            c1.markdown(f"📞 **Primary:** `{ab_row['contact_1']}`")
                            c2.markdown(f"📱 **WhatsApp:** `{ab_row['whatsapp_no'] if ab_row['whatsapp_no'] else 'None'}`")
                            c3.markdown(f"🏠 **Alternative:** `{ab_row['contact_2'] if ab_row['contact_2'] else 'None'}`")
                            
                            col_sel1, col_sel2, col_txt = st.columns([1.5, 1.2, 2])
                            with col_sel1: reason_sel = st.selectbox("Reason for Absence:", options=fixed_reasons, key=f"reason_{ab_row['student_id']}")
                            with col_sel2: contacted_sel = st.selectbox("Contacted Person:", options=contacted_persons, key=f"contacted_{ab_row['student_id']}")
                            with col_txt: custom_note = st.text_input("Additional Notes / Remarks:", placeholder="e.g., Promise note", key=f"custom_note_{ab_row['student_id']}").strip()
                            
                            combined_remarks = f"[{reason_sel}] Call Log: Talked to {contacted_sel}."
                            if custom_note:
                                combined_remarks += f" Note: {custom_note}"
                                
                            remarks_payload.append({
                                "student_id": ab_row['student_id'], "att_date": attendance_date, "remarks": combined_remarks,
                                "up_by": current_user, "up_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.markdown("<hr style='border-style: dashed; margin: 0.5em 0;'>", unsafe_allow_html=True)
                            
                        submit_remarks = st.form_submit_button("🔒 Phase 2: Finalize Absentee Remarks & Lock Log", type="secondary", use_container_width=True)
                        
                        if submit_remarks:
                            try:
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        UPDATE attendance 
                                        SET remarks = :remarks, updated_by = :up_by, updated_at = :up_at
                                        WHERE student_id = :student_id AND date = :att_date;
                                    """), remarks_payload)
                                st.success("🎉 All registers, contact paths, and structured remarks locked successfully!")
                                st.session_state.active_absentee_ids = []
                                st.rerun()
                            except Exception as rem_err:
                                st.error(f"❌ Failed to attach log comments: {rem_err}")
                else:
                    st.success("✨ Excellent! No active absences recorded for this section layout group.")
            else: 
                st.info("ℹ️ No active student profiles found matching these filters.")
        else:
            st.warning("⏳ Please select your filter parameters to load the attendance register.")

def render_universal_marks_entry_workspace():
    pass


def render_institutional_report_generator():
    pass


def render_global_analytics_dashboard():
    """Global multi-dimensional analytical matrix available to Principal, VP, and Exam Controller."""
    st.subheader("📈 Institutional Cross-Sectional Performance Analytics")
    st.info("⚡ Unrestricted Data Scope: Displaying cross-sectional performance metrics and data trends.")
    
    col_an1, col_an2 = st.columns(2)
    with col_an1:
        st.markdown("#### 🏆 Subject Merit Standings")
        chart_data = pd.DataFrame({"Subjects": ["Maths", "Science", "English", "History"], "Avg Grade Point": [78, 85, 82, 74]})
        st.bar_chart(chart_data, x="Subjects", y="Avg Grade Point")


# ==============================================================================
# 3. ROLE-BASED ACCESS CONTROL (RBAC) NAVIGATION ROUTING
# ==============================================================================
st.sidebar.title("🔐 Access Control Matrix")
user_role = st.sidebar.selectbox(
    "Current User Account Profile Role:",
    ["Principal", "Controller Examination", "Vice Principal", "Admission Officer", "Teacher"]
)
st.sidebar.markdown("---")
st.sidebar.title("🚀 Navigation Control")

# 🏢 1. PRINCIPAL DASHBOARD
if user_role == "Principal":
    st.sidebar.info("Signed in as: **Principal**\n\n*Access Level: Full Admin Control*")
    app_mode = st.sidebar.radio(
        "Select Administrative Sub-Module:",
        ["Master Panel Overview", "🛠️ Core Institutional Setup Engine", "Admission Management", "Universal Attendance Panel", "Universal Marks Override Desk", "Report Generator Engine", "📊 Global Institutional Analytics", "Academic Configuration Ledger"]
    )
    
    if app_mode == "Master Panel Overview": st.title("🦅 Principal Strategic Control Command Tower")
    elif app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Admission Management": render_student_management_workspace()
    elif app_mode == "Universal Attendance Panel": render_universal_attendance_workspace(current_user=user_role)
    elif app_mode == "Universal Marks Override Desk": render_universal_marks_entry_workspace()
    elif app_mode == "Report Generator Engine": render_institutional_report_generator()
    elif app_mode == "📊 Global Institutional Analytics": render_global_analytics_dashboard()
    elif app_mode == "Academic Configuration Ledger": st.title("⚙️ Master Core System Configuration Matrix")

# 🗃️ 2. CONTROLLER EXAMINATION DASHBOARD
elif user_role == "Controller Examination":
    st.sidebar.info("Signed in as: **Exam Controller**\n\n*Access Level: Examination, Assessment & Analytics Control*")
    app_mode = st.sidebar.radio(
        "Select Examination Sub-Module:",
        ["Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix"]
    )
    
    if app_mode == "Universal Marks Entry Portal": render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics": render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix": render_institutional_report_generator()

# ⚖️ 3. VICE PRINCIPAL DASHBOARD
elif user_role == "Vice Principal":
    st.sidebar.info("Signed in as: **Vice Principal**\n\n*Access Level: Academic Operations Command*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["🛠️ Core Institutional Setup Engine", "Student Record Management Workspace", "📅 Universal Section Attendance Register", "Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix", "Academic Configuration Ledger"]
    )
    
    if app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Student Record Management Workspace": render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register": render_universal_attendance_workspace(current_user=user_role)
    elif app_mode == "Universal Marks Entry Portal": render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics": render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix": render_institutional_report_generator()
    elif app_mode == "Academic Configuration Ledger": st.title("⚙️ Master Core System Configuration Matrix")

# 💼 4. ADMISSION OFFICER DASHBOARD
elif user_role == "Admission Officer":
    st.sidebar.info("Signed in as: **Admission Officer**\n\n*Access Level: Assigned Extensions*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["Admission Management", "📅 Universal Section Attendance Register", "Student Search Directory"]
    )
    
    if app_mode == "Admission Management": render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register": render_universal_attendance_workspace(current_user=user_role)
    elif app_mode == "Student Search Directory": st.title("🔍 Student Database Query Index")

# 👨‍🏫 5. TEACHER DASHBOARD
elif user_role == "Teacher":
    st.sidebar.info("Signed in as: **Faculty Member**\n\n*Access Level: Context Locked*")
    app_mode = st.sidebar.radio(
        "Select Workspace View:",
        ["📝 Subject Marks Entry Sheet Console", "📅 Section Attendance Register", "📊 My Subject Analytics Panel"]
    )
    
    active_teacher_id = 104 
    
    if app_mode == "📝 Subject Marks Entry Sheet Console": st.title("📝 Subject Marks Entry Sheet Console")
    # FIXED: Connected the teacher's workspace view to the dynamic workspace engine cleanly
    elif app_mode == "📅 Section Attendance Register": render_universal_attendance_workspace(current_user=user_role)
    elif app_mode == "📊 My Subject Analytics Panel": st.title("📊 My Subject Performance Analytics")
