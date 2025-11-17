import streamlit as st
import pandas as pd
from utils.parser import DocumentParser
from utils.validator import BudgetValidator
from utils.ai_grader import AIGrader
import json
from io import BytesIO

# ==================== PASSWORD PROTECTION ====================
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.markdown("### 🔒 Budget Grader - Login Required")
        st.info("Please enter the password to access the application.")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

# Check password before showing app
if not check_password():
    st.stop()  # Don't continue if password is wrong

# ==================== MAIN APP (only shows if password correct) ====================

# Page config
st.set_page_config(
    page_title="Budget Grader",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    h1 {
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'grading_report' not in st.session_state:
    st.session_state.grading_report = None

# Header
st.title("📊 Nursing Budget Grader")
st.markdown("Lebanese American University - Advancement Services")

# Main tabs - Only Upload and Results
tab1, tab2 = st.tabs(["📤 Upload & Grade", "📥 Results"])

# TAB 1: Upload & Grade
with tab1:
    st.header("Upload Assignment")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['docx', 'xlsx', 'pdf'],
            help="Supports Word, Excel, and PDF formats"
        )
    
    with col2:
        st.markdown("### Settings")
        inflation_rate = st.number_input("Inflation Rate (%)", value=5, min_value=0, max_value=100)
        tolerance = st.number_input("Tolerance (±)", value=0.5, min_value=0.0, max_value=5.0, step=0.1)
        use_ai = st.checkbox("Use AI Grading", value=True)
        
        if use_ai:
            api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        else:
            api_key = None
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
        
        if st.button("🔍 Extract & Grade", type="primary", use_container_width=True):
            with st.spinner("Processing..."):
                try:
                    # Extract
                    parser = DocumentParser()
                    extracted_data = parser.parse(uploaded_file)
                    st.session_state.extracted_data = extracted_data
                    
                    # Grade immediately
                    if use_ai and api_key:
                        grader = AIGrader(
                            provider="openai",
                            api_key=api_key,
                            model="gpt-4o"
                        )
                        report = grader.grade(
                            extracted_data,
                            inflation_rate=inflation_rate,
                            tolerance=tolerance
                        )
                    else:
                        validator = BudgetValidator(
                            inflation_rate=inflation_rate,
                            tolerance=tolerance
                        )
                        report = validator.validate(extracted_data)
                    
                    st.session_state.grading_report = report
                    st.success("✅ Grading complete!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Show extracted data preview (expanded)
    if st.session_state.extracted_data:
        st.divider()
        st.subheader("Extracted Data")
        
        data = st.session_state.extracted_data
        
        # Fixed Expenses - EXPANDED
        st.markdown("#### 📋 Fixed Expenses")
        if data.get('fixed_expenses'):
            st.dataframe(pd.DataFrame(data['fixed_expenses']), use_container_width=True, hide_index=True)
        
        # Variable Expenses - EXPANDED
        st.markdown("#### 📋 Variable Expenses")
        if data.get('variable_expenses'):
            st.dataframe(pd.DataFrame(data['variable_expenses']), use_container_width=True, hide_index=True)
        
        # Total Expenses - EXPANDED
        st.markdown("#### 📋 Total Expenses")
        if data.get('total_expenses'):
            st.json(data['total_expenses'])

# TAB 2: Results (Vertical Layout)
with tab2:
    st.header("Grading Results")
    
    if not st.session_state.grading_report:
        st.warning("⚠️ Please upload and grade an assignment first")
    else:
        report = st.session_state.grading_report
        
        # Score Card
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score", f"{report['correct_count']}/{report['total_calculations']}")
        with col2:
            st.metric("Percentage", f"{report['percentage']:.1f}%")
        with col3:
            grade = "🟢 Pass" if report['percentage'] >= 70 else "🔴 Fail"
            st.metric("Grade", grade)
        
        st.divider()
        
        # FIXED EXPENSES - Vertical
        st.subheader("Fixed Expenses Results")
        for item in report.get('fixed_expenses_results', []):
            st.markdown(f"### {item['description']}")
            for field, result in item['validations'].items():
                icon = "✅" if result['correct'] else "❌"
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"{icon} **{field.replace('_', ' ').title()}**")
                with col2:
                    st.write(f"Expected: {result['expected']}")
                with col3:
                    st.write(f"Actual: {result['actual']}")
            st.divider()
        
        # VARIABLE EXPENSES - Vertical
        st.subheader("Variable Expenses Results")
        for item in report.get('variable_expenses_results', []):
            st.markdown(f"### {item['description']}")
            for field, result in item['validations'].items():
                icon = "✅" if result['correct'] else "❌"
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"{icon} **{field.replace('_', ' ').title()}**")
                with col2:
                    st.write(f"Expected: {result['expected']}")
                with col3:
                    st.write(f"Actual: {result['actual']}")
            st.divider()
        
        # TOTAL EXPENSES - Vertical
        st.subheader("Total Expenses Results")
        total_results = report.get('total_expenses_results', {})
        for field, result in total_results.items():
            icon = "✅" if result['correct'] else "❌"
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"{icon} **{field.replace('_', ' ').title()}**")
            with col2:
                st.write(f"Expected: {result['expected']}")
            with col3:
                st.write(f"Actual: {result['actual']}")
        
        st.divider()
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            from utils.report_generator import generate_pdf_report
            pdf_buffer = generate_pdf_report(report)
            st.download_button(
                "📥 Download PDF Report",
                data=pdf_buffer,
                file_name=f"grading_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        with col2:
            json_str = json.dumps(report, indent=2)
            st.download_button(
                "📥 Download JSON Data",
                data=json_str,
                file_name=f"grading_data.json",
                mime="application/json",
                use_container_width=True
            )