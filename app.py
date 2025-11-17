import streamlit as st
import pandas as pd
from utils.parser import DocumentParser
from utils.validator import BudgetValidator
from utils.ai_grader import AIGrader
import json
from io import BytesIO

# ==================== PASSWORD PROTECTION ====================
# def check_password():
#     """Returns `True` if the user had the correct password."""

#     def password_entered():
#         """Checks whether a password entered by the user is correct."""
#         if st.session_state["password"] == st.secrets["password"]:
#             st.session_state["password_correct"] = True
#             del st.session_state["password"]  # Don't store password
#         else:
#             st.session_state["password_correct"] = False

#     if "password_correct" not in st.session_state:
#         # First run, show input for password
#         st.text_input(
#             "Password", 
#             type="password", 
#             on_change=password_entered, 
#             key="password"
#         )
#         st.markdown("### 🔒 Budget Grader - Login Required")
#         st.info("Please enter the password to access the application.")
#         return False
#     elif not st.session_state["password_correct"]:
#         # Password incorrect, show input + error
#         st.text_input(
#             "Password", 
#             type="password", 
#             on_change=password_entered, 
#             key="password"
#         )
#         st.error("😕 Password incorrect")
#         return False
#     else:
#         # Password correct
#         return True

# # Check password before showing app
# if not check_password():
#     st.stop()  # Don't continue if password is wrong

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
st.title("📊 Budget Grader")
#st.markdown("Lebanese American University - Advancement Services")

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
        # AI grading hidden - always use rule-based validation
        use_ai = False
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

                    # Validate that we have data
                    if not extracted_data.get('fixed_expenses') and not extracted_data.get('variable_expenses'):
                        st.error("⚠️ No budget data found in the document. Please check the file format.")
                        st.stop()

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
                    #st.balloons()

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    import traceback
                    st.error(f"Details: {traceback.format_exc()}")
    
    # Show extracted data with validation highlighting
    if st.session_state.extracted_data and st.session_state.grading_report:
        st.divider()
        st.subheader("📊 Extracted Data with Validation")

        data = st.session_state.extracted_data
        report = st.session_state.grading_report

        # Fixed Expenses with validation
        st.markdown("#### 📋 Fixed Expenses")
        if data.get('fixed_expenses'):
            fixed_df = pd.DataFrame(data['fixed_expenses'])

            # Create validation lookup
            validation_map = {}
            for item_result in report.get('fixed_expenses_results', []):
                desc = item_result['description']
                validation_map[desc] = item_result['validations']

            # Apply styling
            def highlight_fixed(row):
                desc = row.get('description', '')
                if desc not in validation_map:
                    return [''] * len(row)

                validations = validation_map[desc]
                styles = []
                for col in fixed_df.columns:
                    col_key = col
                    if col == 'description':
                        styles.append('')  # Don't highlight description column
                    elif col_key in validations:
                        if validations[col_key].get('correct', False):
                            styles.append('background-color: #90EE90')  # Light green
                        else:
                            styles.append('background-color: #FFB6C6')  # Light red
                    else:
                        styles.append('')
                return styles

            styled_fixed = fixed_df.style.apply(highlight_fixed, axis=1)
            st.dataframe(styled_fixed, use_container_width=True, hide_index=True)

        # Variable Expenses with validation
        st.markdown("#### 📋 Variable Expenses")
        if data.get('variable_expenses'):
            var_df = pd.DataFrame(data['variable_expenses'])

            # Create validation lookup
            validation_map = {}
            for item_result in report.get('variable_expenses_results', []):
                desc = item_result['description']
                validation_map[desc] = item_result['validations']

            # Apply styling
            def highlight_variable(row):
                desc = row.get('description', '')
                if desc not in validation_map:
                    return [''] * len(row)

                validations = validation_map[desc]
                styles = []
                for col in var_df.columns:
                    col_key = col
                    if col == 'description':
                        styles.append('')  # Don't highlight description column
                    elif col_key in validations:
                        if validations[col_key].get('correct', False):
                            styles.append('background-color: #90EE90')  # Light green
                        else:
                            styles.append('background-color: #FFB6C6')  # Light red
                    else:
                        styles.append('')
                return styles

            styled_var = var_df.style.apply(highlight_variable, axis=1)
            st.dataframe(styled_var, use_container_width=True, hide_index=True)

        # Total Expenses with validation
        st.markdown("#### 📋 Total Expenses")
        if data.get('total_expenses'):
            total_data = data['total_expenses']
            total_results = report.get('total_expenses_results', {})

            # Debug: Show validation results
            with st.expander("🔍 Debug: Total Validation Results"):
                st.write("**Raw Data:**")
                st.write("Total Data from Document:", total_data)

                st.write("\n**Fixed Expenses 5-month values:**")
                for item in data.get('fixed_expenses', []):
                    st.write(f"  - {item.get('description')}: {item.get('5_month_consumption')}")

                st.write("\n**Variable Expenses 5-month values:**")
                for item in data.get('variable_expenses', []):
                    st.write(f"  - {item.get('description')}: {item.get('5_month_consumption')}")

                st.write("\n**Validation Results:**")
                for col, result in total_results.items():
                    st.write(f"**{col}:**")
                    st.write(f"  - Correct: {result.get('correct')}")
                    st.write(f"  - Expected: {result.get('expected')}")
                    st.write(f"  - Actual: {result.get('actual')}")
                    st.write(f"  - Status: {result.get('status')}")
                    if 'breakdown' in result:
                        st.write(f"  - Breakdown: {result.get('breakdown')}")
                    st.write("")

            # Create dataframe for total expenses
            total_df = pd.DataFrame([total_data])

            # Apply styling
            def highlight_total(row):
                styles = []
                for col in total_df.columns:
                    if col in total_results:
                        if total_results[col].get('correct', False):
                            styles.append('background-color: #90EE90')  # Light green
                        else:
                            styles.append('background-color: #FFB6C6')  # Light red
                    else:
                        styles.append('')
                return styles

            styled_total = total_df.style.apply(highlight_total, axis=1)
            st.dataframe(styled_total, use_container_width=True, hide_index=True)

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