import streamlit as st
import pandas as pd
import os
import tempfile
import json
import datetime
from dotenv import load_dotenv
from utils.file_processing import find_dataframe_with_columns, find_columns
from utils.census_processing import standardize_data, analyze_census, create_excel_analysis_bytes
from utils.pdf_processing import extract_tob_data, extract_company_from_trade_license
from utils.download_utils import to_excel_bytes
from utils.visualizations import plot_gender_distribution, plot_age_distribution, plot_relation_distribution, display_image
from utils.json_conversion import to_json_string
from utils.email_processing import extract_structured_data_from_email  # Import the email extraction function
from utils.browser_base import main
import subprocess

def install_playwright():
    try:
        result = subprocess.run(["playwright", "install"], check=True, capture_output=True, text=True)
        result_2 = subprocess.run(["sudo","playwright","install-deps"], check=True, capture_output=True, text=True)
        print("Playwright installed successfully:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error during Playwright installation:")
        print(e.stderr)

install_playwright()
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
st.set_page_config(page_title="Census Data Processor", layout="wide")

# Session state initialization
if 'standardized_df' not in st.session_state:
    st.session_state.standardized_df = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'changes_info' not in st.session_state:
    st.session_state.changes_info = None
if 'tob_data' not in st.session_state:
    st.session_state.tob_data = None
if 'company_data' not in st.session_state:
    st.session_state.company_data = None
if 'email_data' not in st.session_state:
    st.session_state.email_data = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0
# New session state variables for combined JSONs
if 'quote_data' not in st.session_state:
    st.session_state.quote_data = None
if 'benefit_details_data' not in st.session_state:
    st.session_state.benefit_details_data = None
if 'submission_complete' not in st.session_state:
    st.session_state.submission_complete = False
if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'automation_complete' not in st.session_state:
    st.session_state.automation_complete = False

st.title("Census Data Processor")

# Text input
email_content = st.text_area("Email Data", 
                          placeholder="Enter the email data for processing...", 
                          height=100)

# Email extraction button
if st.button("Extract Email Data"):
    if email_content:
        with st.spinner("Extracting data from email..."):
            try:
                # Extract data from email content using the imported function
                extracted_data = extract_structured_data_from_email(email_content, GEMINI_API_KEY)
                st.session_state.email_data = extracted_data
                st.session_state.active_tab = 5  # Set active tab to Email tab (6th tab, 0-indexed)
                st.success("Email data extracted successfully! Check the Email Data tab.")
                st.rerun()  # Rerun to show the Email tab
            except Exception as e:
                st.error(f"Error extracting email data: {str(e)}")
    else:
        st.warning("Please enter email content to extract data.")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "File Upload", 
    "Data Standardization", 
    "Data Analysis", 
    "Benefits Analysis", 
    "Company Information",
    "Email Data",
    "Combined Data"  # New tab for combined data
])

# Set the active tab based on session state
tabs = [tab1, tab2, tab3, tab4, tab5, tab6, tab7]
active_tab = tabs[st.session_state.active_tab]

with tab1:
    st.header("Upload Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Census Data")
        census_file = st.file_uploader(
            "Upload Census File (CSV/XLS/XLSX)", 
            type=["csv", "xls", "xlsx", "xlsm"]
        )
    
    with col2:
        st.subheader("Trade License")
        trade_license = st.file_uploader(
            "Upload Trade License (PDF)", 
            type=["pdf"]
        )
    
    with col3:
        st.subheader("Table of Benefits")
        benefits_table = st.file_uploader(
            "Upload Table of Benefits (PDF)", 
            type=["pdf"]
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if census_file:
            st.success(f"Census file '{census_file.name}' uploaded successfully!")
            
            # Process button
            if st.button("Process Census Data"):
                with st.spinner("Processing census data..."):
                    try:
                        # Standardize data
                        standardized_df, changes_info = standardize_data(census_file)
                        st.session_state.standardized_df = standardized_df
                        st.session_state.changes_info = changes_info
                        
                        # Analyze data
                        analysis_results = analyze_census(standardized_df)
                        st.session_state.analysis_results = analysis_results
                        
                        st.success("Census data processed successfully! Check the Standardization and Analysis tabs.")
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")
        
        if trade_license:
            st.success(f"Trade license '{trade_license.name}' uploaded successfully!")
            
            # Add process button for Trade License
            if st.button("Process Trade License"):
                with st.spinner("Processing Trade License..."):
                    try:
                        # Extract company name from the PDF
                        company_data = extract_company_from_trade_license(trade_license, GEMINI_API_KEY)
                        if company_data:
                            st.session_state.company_data = company_data
                            st.success("Trade License processed successfully! Check the Company Information tab.")
                    except Exception as e:
                        st.error(f"Error processing Trade License: {str(e)}")
    
    with col2:
        if benefits_table:
            st.success(f"Table of benefits '{benefits_table.name}' uploaded successfully!")
            
            # Add process button for Table of Benefits
            if st.button("Process Table of Benefits"):
                with st.spinner("Processing Table of Benefits..."):
                    try:
                        # Extract structured data from the PDF
                        tob_data = extract_tob_data(benefits_table, GEMINI_API_KEY)
                        if tob_data:
                            st.session_state.tob_data = tob_data
                            st.success("Table of Benefits processed successfully! Check the Benefits Analysis tab.")
                    except Exception as e:
                        st.error(f"Error processing Table of Benefits: {str(e)}")

with tab2:
    st.header("Data Standardization Results")
    
    if st.session_state.standardized_df is not None and st.session_state.changes_info is not None:
        standardized_df = st.session_state.standardized_df
        changes_info = st.session_state.changes_info
        
        # Display standardization info
        st.subheader("Standardization Applied")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Display relation column changes if applicable
            relation_column = changes_info.get('relation_column')
            if relation_column:
                st.write(f"**Relation column**: '{relation_column}'")
                st.write("Sample of standardized relation values:")
                relation_sample = standardized_df[relation_column].head(5).tolist()
                for i, val in enumerate(relation_sample):
                    st.write(f"  {i+1}. {val}")
            else:
                st.write("No relation column found.")
            
            # Display gender column changes if applicable
            gender_column = changes_info.get('gender_column')
            if gender_column:
                st.write(f"**Gender column**: '{gender_column}'")
                st.write("Sample of standardized gender values:")
                gender_sample = standardized_df[gender_column].head(5).tolist()
                for i, val in enumerate(gender_sample):
                    st.write(f"  {i+1}. {val}")
            else:
                st.write("No gender column found.")
        
        with col2:
            # Display date column changes
            date_columns = changes_info.get('date_columns', [])
            if date_columns:
                st.write(f"**Date columns**:")
                for date_col in date_columns[:3]:  # Limit to first 3 columns
                    st.write(f"- '{date_col}'")
            else:
                st.write("No date columns found.")
        
        # Preview standardized data
        st.subheader("Preview of Standardized Data")
        st.dataframe(standardized_df.head(10))
        
        # Download section
        st.subheader("Download Standardized Data")
        
        # Information about the downloads
        st.info("""
        - **Excel**: Contains all standardized data with organized column names
        - **JSON**: Groups records by category in a structured format suitable for API requests
          - Note: The 'category' field will only be included if it exists in your uploaded file
          - If no category exists, records will be grouped under an 'all' category in the JSON
        """)
        
        # Download options in columns
        col1, col2 = st.columns(2)
        
        with col1:
            # Download standardized data as Excel
            excel_bytes = to_excel_bytes(standardized_df)
            st.download_button(
                label="Download as Excel",
                data=excel_bytes,
                file_name="standardized_census.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download the standardized data as an Excel file"
            )
            
        with col2:
            # Download standardized data as JSON
            json_str = to_json_string(standardized_df)
            st.download_button(
                label="Download as JSON",
                data=json_str,
                file_name="census_data.json",
                mime="application/json",
                help="Download the standardized data as a JSON file with records grouped by category"
            )
            
        # Add JSON preview
        with st.expander("Preview JSON Structure"):
            st.write("""
            **Important Note**: The 'category' field will only be included in the JSON if it exists in your uploaded data file.
            
            The JSON structure will depend on whether a category column exists in your data:
            
            1. **If a category column exists in your data**, records will be grouped by category:
            """)
            
            st.code("""
{
    "census_list": {
        "A": [
            {
                "age": 25,
                "dob": 44562,
                "name": "John Smith",
                "gender": "male",
                "rawGender": "M",
                "category": "A",  // Only included if it exists in original data
                "relation": "primary",
                "relationType": "Principal",
                "marital_status": "married",
                "rawMarital_status": "Married"
            },
            ...
        ],
        "B": [
            ...
        ]
    }
}
            """, language="json")
            
            st.write("""
            2. **If no category column exists in your data**, all records will be placed in an "all" category:
            """)
            
            st.code("""
{
    "census_list": {
        "all": [
            {
                "age": 25,
                "dob": 44562,
                "name": "John Smith",
                "gender": "male",
                "rawGender": "M",
                // No category field since it's not in the original data
                "relation": "primary",
                "relationType": "Principal",
                "marital_status": "married",
                "rawMarital_status": "Married"
            },
            ...
        ]
    }
}
            """, language="json")
    else:
        st.info("Please upload and process a census file in the 'File Upload' tab.")

with tab3:
    st.header("Census Analysis Results")
    
    if st.session_state.analysis_results is not None and st.session_state.standardized_df is not None:
        results = st.session_state.analysis_results
        standardized_df = st.session_state.standardized_df
        changes_info = st.session_state.changes_info
        
        # Display analysis results in a nice format
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Census Demographics")
            st.metric("Total Census Count", results['census_count'])
            st.metric("Average Adult Age", results['avg_adult_age'])
            st.metric("People Over 64 Years", f"{results['over_64_count']} ({results['pct_elderly']}%)")
            
            # Gender breakdown
            st.subheader("Gender Breakdown")
            gender_data = pd.DataFrame({
                'Gender': ['Male', 'Female'],
                'Count': [results['male_count'], results['female_count']],
                'Percentage': [f"{results['male_pct']}%", f"{results['female_pct']}%"]
            })
            st.table(gender_data)
            
            # Add gender distribution visualization
            if results['male_count'] > 0 or results['female_count'] > 0:
                st.subheader("Gender Distribution Chart")
                gender_chart = plot_gender_distribution(results['male_count'], results['female_count'])
                display_image(gender_chart)
        
        with col2:
            st.subheader("Relations Analysis")
            relations_data = pd.DataFrame({
                'Relation': ['Principal', 'Dependent'],
                'Count': [results['principal_count'], results['dependent_count']],
                'Percentage': [f"{results['principal_pct']}%", f"{results['dependent_pct']}%"]
            })
            st.table(relations_data)
            
            # Add relation distribution visualization
            if results['principal_count'] > 0 or results['dependent_count'] > 0:
                st.subheader("Relation Distribution Chart")
                relation_chart = plot_relation_distribution(results['principal_count'], results['dependent_count'])
                display_image(relation_chart)
            
            st.subheader("Special Demographics")
            st.metric("Married Females Under 45", 
                      f"{results['married_f_under_45']} ({results['pct_married_f_under_45']}% of females)")
        
        # Add age distribution visualization
        st.subheader("Age Distribution")
        age_column = changes_info.get('age_column')
        dob_column = changes_info.get('dob_column')
        age_chart = plot_age_distribution(standardized_df, age_column, dob_column)
        if age_chart:
            display_image(age_chart)
        else:
            st.write("Could not generate age distribution chart due to insufficient age data.")
        
        # Download analysis report
        excel_analysis_bytes = create_excel_analysis_bytes(standardized_df)
        st.download_button(
            label="Download Analysis Report",
            data=excel_analysis_bytes,
            file_name="census_analysis_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Please upload and process a census file in the 'File Upload' tab.")

# Add Benefits Analysis tab
with tab4:
    st.header("Table of Benefits Analysis")
    
    if st.session_state.tob_data is not None:
        tob_data = st.session_state.tob_data
        
        # Display structured data
        st.subheader("Extracted Benefits Data")
        
        # Create a more user-friendly display of the data
        cols = st.columns(2)
        
        with cols[0]:
            st.write("**Basic Coverage Details:**")
            
            if "annual_medical" in tob_data:
                st.metric("Annual Medical Limit", tob_data["annual_medical"])
            
            if "territorial_cover" in tob_data:
                st.metric("Territorial Cover", tob_data["territorial_cover"])
            
            if "ip_room_type" in tob_data:
                st.metric("Inpatient Room Type", tob_data["ip_room_type"])
            
            if "deductible_for_consultation" in tob_data:
                st.metric("Consultation Deductible", tob_data["deductible_for_consultation"])
            
            if "diagnostic_investigation_op_copay" in tob_data:
                st.metric("Diagnostic Copay", tob_data["diagnostic_investigation_op_copay"])
            
        with cols[1]:
            st.write("**Additional Benefits:**")
            
            if "maternity" in tob_data:
                st.metric("Maternity", tob_data["maternity"])
            
            if "dental" in tob_data:
                st.metric("Dental", tob_data["dental"])
            
            if "optical" in tob_data:
                st.metric("Optical", tob_data["optical"])
            
            if "pharmacy_copay" in tob_data:
                st.metric("Pharmacy Copay", tob_data["pharmacy_copay"])
            
            if "pharmacy_limit" in tob_data:
                st.metric("Pharmacy Limit", tob_data["pharmacy_limit"])
        
        # Display the full JSON
        st.subheader("Complete Benefits Data (JSON)")
        st.json(tob_data)
        
        # Create a downloadable JSON file
        tob_json = json.dumps(tob_data, indent=4)
        st.download_button(
            label="Download Benefits Data as JSON",
            data=tob_json,
            file_name="benefits_data.json",
            mime="application/json"
        )
    else:
        st.info("Please upload and process a Table of Benefits PDF in the 'File Upload' tab.")

# Add Company Information tab
with tab5:
    st.header("Company Information")
    
    if st.session_state.company_data is not None:
        company_data = st.session_state.company_data
        
        # Display company information
        st.subheader("Extracted Company Details")
        
        if "company_name" in company_data:
            st.metric("Company Name", company_data["company_name"])
            
            # Create a styled card for the company
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">{company_data["company_name"]}</h3>
                <p>Trade License verified ✓</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create a downloadable JSON file
        company_json = json.dumps(company_data, indent=4)
        st.download_button(
            label="Download Company Data as JSON",
            data=company_json,
            file_name="company_data.json",
            mime="application/json"
        )
    else:
        st.info("Please upload and process a Trade License PDF in the 'File Upload' tab.")

# Add Email Data tab
with tab6:
    st.header("Email Data Extraction")
    
    if st.session_state.email_data is not None:
        email_data = st.session_state.email_data
        
        # Display extracted email data
        st.subheader("Extracted Email Information")
        
        # Create a card layout for the extracted information
        col1, col2 = st.columns(2)
        
        with col1:
            if "broker_name" in email_data:
                st.metric("Broker Name", email_data["broker_name"])
            
            if "relationship_manager" in email_data:
                st.metric("Relationship Manager", email_data["relationship_manager"])
                
        with col2:
            if "broker_fee" in email_data:
                fee_value = email_data["broker_fee"] if email_data["broker_fee"] is not None else "Not specified"
                st.metric("Broker Fee", fee_value)
        
        # Create a styled card for the broker information
        if "broker_name" in email_data and "relationship_manager" in email_data:
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; margin-top: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">Broker Information</h3>
                <p><strong>Broker:</strong> {email_data["broker_name"]}</p>
                <p><strong>Relationship Manager:</strong> {email_data["relationship_manager"]}</p>
                <p><strong>Broker Fee:</strong> {email_data.get("broker_fee", "Not specified")}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display the full JSON
        st.subheader("Complete Email Data (JSON)")
        st.json(email_data)
        
        # Create a downloadable JSON file
        email_json = json.dumps(email_data, indent=4)
        st.download_button(
            label="Download Email Data as JSON",
            data=email_json,
            file_name="email_data.json",
            mime="application/json"
        )
    else:
        # Email extraction form directly in the tab
        st.info("No email data has been extracted yet. You can extract email data from the main page.")
        
        # Additional email content text area in the tab
        tab_email_content = st.text_area(
            "Or paste email content here:",
            height=200, 
            placeholder="From: John Smith <john.smith@abcinsurance.com>\nTo: Sarah Johnson <sarah.johnson@rgabroker.com>\n..."
        )
        
        if st.button("Extract Email Data", key="extract_email_tab"):
            if tab_email_content:
                with st.spinner("Extracting data from email..."):
                    try:
                        # Extract data from email content
                        extracted_data = extract_structured_data_from_email(tab_email_content, GEMINI_API_KEY)
                        st.session_state.email_data = extracted_data
                        st.success("Email data extracted successfully!")
                        st.rerun()  # Rerun to refresh the tab with extracted data
                    except Exception as e:
                        st.error(f"Error extracting email data: {str(e)}")
            else:
                st.warning("Please enter email content to extract data.")

with tab7:
    st.header("Combined Data")
    
    if st.session_state.submission_complete:
        st.success("Data submission complete! You can now download the combined data.")
        
        # Display QUOTE_DATA
        if st.session_state.quote_data:
            st.subheader("Quote Data")
            st.json(st.session_state.quote_data)
            
            # Create downloadable JSON for QUOTE_DATA
            quote_json = json.dumps(st.session_state.quote_data, indent=4)
            st.download_button(
                label="Download Quote Data as JSON",
                data=quote_json,
                file_name="quote_data.json",
                mime="application/json"
            )
        
        # Display BENEFIT_DETAILS_DATA
        if st.session_state.benefit_details_data:
            st.subheader("Benefit Details Data")
            st.json(st.session_state.benefit_details_data)
            
            # Create downloadable JSON for BENEFIT_DETAILS_DATA
            benefit_json = json.dumps(st.session_state.benefit_details_data, indent=4)
            st.download_button(
                label="Download Benefit Details as JSON",
                data=benefit_json,
                file_name="benefit_details_data.json",
                mime="application/json"
            )
        
        # If census data is available, provide download
        if st.session_state.standardized_df is not None:
            st.subheader("Census Data")
            excel_bytes = to_excel_bytes(st.session_state.standardized_df)
            st.download_button(
                label="Download Census Data as Excel",
                data=excel_bytes,
                file_name="census_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Also provide JSON option
            json_str = to_json_string(st.session_state.standardized_df)
            st.download_button(
                label="Download Census Data as JSON",
                data=json_str,
                file_name="census_data.json",
                mime="application/json"
            )
        
        # Add PDF download option if available
        if st.session_state.automation_complete and st.session_state.pdf_path:
            st.subheader("Generated Quote PDF")
            
            try:
                with open(st.session_state.pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                st.download_button(
                    label="Download Quote PDF",
                    data=pdf_bytes,
                    file_name=os.path.basename(st.session_state.pdf_path),
                    mime="application/pdf"
                )
                
                st.success(f"Quote PDF generated successfully! Click the button above to download.")
            except Exception as e:
                st.error(f"Error reading PDF file: {str(e)}")
        elif st.session_state.automation_running:
            st.info("Automation is running... please wait for the PDF to be generated.")
    else:
        st.info("Please submit all information using the 'Submit All Information' button below.")

# Helper function to generate QUOTE_DATA
def generate_quote_data():
    """
    Generate QUOTE_DATA from collected information
    """
    # Get current date for policy_start_date
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Default values
    quote_data = {
        "client_name": "",
        "policy_start_date": current_date,
        "broker_name": "",
        "relationship_manager": "",
        "adjustments_discount": "0",
        "discount_comment": "",
        "brokerage_fees": "12.50",
        "healthx": "7.50",
        "tpa": "5",
        "insurer": "5"
    }
    
    # Update with company_name from trade license if available
    if st.session_state.company_data and "company_name" in st.session_state.company_data:
        quote_data["client_name"] = st.session_state.company_data["company_name"]
    
    # Update with broker info from email data if available
    if st.session_state.email_data:
        if "broker_name" in st.session_state.email_data:
            quote_data["broker_name"] = st.session_state.email_data["broker_name"]
        
        if "relationship_manager" in st.session_state.email_data:
            quote_data["relationship_manager"] = st.session_state.email_data["relationship_manager"]
        
        if "broker_fee" in st.session_state.email_data and st.session_state.email_data["broker_fee"]:
            quote_data["brokerage_fees"] = str(st.session_state.email_data["broker_fee"]).replace("%", "")
    
    # If we have tob_data, try to extract a date (future enhancement)
    # This would require searching the TOB for a date field that might be policy start date
    
    return quote_data

# Helper function to get benefit details data
def get_benefit_details_data():
    """
    Return the BENEFIT_DETAILS_DATA from TOB data
    """
    if st.session_state.tob_data:
        # Use the TOB data directly, it should already be in the required format
        return st.session_state.tob_data
    else:
        return None
st.header("Submit All Data")
if st.button("Submit All Information", type="primary"):
    if not (email_content or census_file or trade_license or benefits_table or st.session_state.email_data):
        st.error("Please provide at least one input before submitting")
    else:
        submissions = []
        
        # Generate combined JSON data
        st.session_state.quote_data = generate_quote_data()
        st.session_state.benefit_details_data = get_benefit_details_data()
        
        # Mark submission as complete
        st.session_state.submission_complete = True
        
        if email_content:
            submissions.append("Email Content")
        
        if census_file:
            submissions.append(f"Census file: {census_file.name}")
            if st.session_state.standardized_df is not None:
                submissions.append("Standardized census data")
            if st.session_state.analysis_results is not None:
                submissions.append("Census analysis results")
        
        if trade_license:
            submissions.append(f"Trade license: {trade_license.name}")
            if st.session_state.company_data is not None:
                submissions.append("Company information")
        
        if benefits_table:
            submissions.append(f"Table of benefits: {benefits_table.name}")
            if st.session_state.tob_data is not None:
                submissions.append("Extracted benefits data")
                
        if st.session_state.email_data is not None:
            submissions.append("Email data")
        
        if st.session_state.quote_data:
            submissions.append("Quote data")
        
        if st.session_state.benefit_details_data:
            submissions.append("Benefit details data")
        
        st.success(f"The following have been submitted: {', '.join(submissions)}")
        
        # Run automation if we have the required data
        if st.session_state.standardized_df is not None and st.session_state.quote_data and st.session_state.benefit_details_data:
            st.session_state.automation_running = True
            
            # Create temporary directory to store the census file
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save census data to a temporary Excel file
                census_file_path = os.path.join(temp_dir, "census_data.xls")
                with pd.ExcelWriter(census_file_path, engine='openpyxl') as writer:
                    st.session_state.standardized_df.to_excel(writer, index=False)
                
                with st.spinner("Running automation process to generate quote. This may take several minutes..."):
                    try:
                        # Start the automation process and get the result
                        result = main(
                            st.session_state.quote_data,
                            st.session_state.benefit_details_data,
                            census_file_path
                        )
                        if result and result.get('success'):
                            pdf_path = result.get('pdf_path')
                            if pdf_path and os.path.exists(pdf_path):
                                st.session_state.pdf_path = pdf_path
                                st.session_state.automation_complete = True
                                st.success(f"Automation completed successfully! PDF has been generated.")
                                
                                # Automatically trigger the download
                                with open(pdf_path, "rb") as pdf_file:
                                    pdf_bytes = pdf_file.read()
                                    st.download_button(
                                        label="Download Generated PDF",
                                        data=pdf_bytes,
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf",
                                        key="auto_download"
                                    )
                            else:
                                st.warning(f"Automation completed but no valid PDF was found. Message: {result.get('message')}")
                        else:
                            st.error(f"Automation failed: {result.get('message', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error during automation: {str(e)}")
                    finally:
                        st.session_state.automation_running = False
        
        # Set active tab to Combined Data
        st.session_state.active_tab = 6  # Index of the Combined Data tab
        
        st.balloons()
