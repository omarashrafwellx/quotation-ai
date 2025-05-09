from browserbase import Browserbase
from playwright.sync_api import sync_playwright,expect, Page, BrowserContext
import time
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
EMAIL =os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
BROWSERBASE_API_KEY=os.getenv("BROWSERBASE_API_KEY")
PROJECT_ID=os.getenv("PROJECT_ID")
# CENSUS_FILE_PATH = "files/excel/MemberCensusDataTemplate_standardized.xls"

# Form data
# QUOTE_DATA = {
#     "client_name": "A valid organization that exists here",
#    "policy_start_date": "2025-04-08",
#     "broker_name": "al raha",
#     "relationship_manager": "Sabina",
#     "adjustments_discount": "10",
#     "discount_comment": "Special corporate discount",
#     "brokerage_fees": "10.50",
#     "healthx": "9.50",
#     "tpa": "7",
#     "insurer": "7"
# }

# BENEFIT_DETAILS_DATA = {
#     "additional_loading": "15", # Example value
#     "nas_network": "Dubai RN 4.5", # As seen in HTML, 'RN' might be a valid option
#     "annual_medical": "AED 150,000", # Example valid option
#     "ip_room_type": "Private", # As seen in HTML
#     "copayment_ip_daycase": "0%", # Example valid option (e.g., Nil, 10%, 20%)
#     "deductible_consultation": "AED 50", # As seen in HTML
#     "territorial_cover": "UAE only", # As seen in HTML
#     "diagnostic_op_copay": "AED 10", # Example valid option
#     "pharmacy_copay": "10 %", # Example valid option (e.g., 0 %, 10%, 20%)
#     "pharmacy_limit": "Upto AML", # As seen in HTML
#     "medication_type": "Branded", # Example valid option (e.g., Generic, Branded)
#     "pec": "150000", # Example (e.g. MHD, Covered after 6m, Fully Covered)
#     "maternity_limit": "7500", # Example value
#     "maternity_copay": "0% copayment. Routine Benefits", # Example value
#     "dental_limit": "2000", # Example value
#     "dental_copay": "30% copayment. Routine Benefits", # Example value
#     "optical_limit": "500", # Example value
#     "optical_copay": "30% copayment. Routine Benefits", # Example value
#     "repatriation": "5,000", # Example value
#     "nursing_at_home": "1,000", # Example value
#     "op_psychiatric_limit": "1,000", # Example value
#     "op_psychiatric_copay": "0% of Co-Pay", # Example value
#     "alternative_medicine_limit": "1,000", # Example value
#     "alternative_medicine_copay": "0% of Co-Pay", # Example value
#     "routine_health_checkup": "1000", # Example value
#     "physiotherapy_limit": "6 Sessions", # Example value
#     "physiotherapy_copay": "0% of Co-Pay", # Example value (or copay %)
# }
def setup_browser():
    """Initialize Browserbase session and set up browser"""
    bb = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = bb.sessions.create(project_id=PROJECT_ID)
    return bb, session

def login(page):
    """Handle login process"""
    print("Navigating to login page...")
    page.goto("https://app-qa-hqt.wellx.ai/login", wait_until="networkidle")
    
    print("Filling login form...")
    page.fill('input[placeholder="Enter your email"]', EMAIL)
    page.fill('input[placeholder="Enter your Password"]', PASSWORD)
    
    print("Clicking login button...")
    page.click('button:has-text("Login")')
    
    # Wait for dashboard to load
    page.wait_for_load_state("networkidle")
    time.sleep(5)
    
    # Take screenshot of successful login
    # page.screenshot(path="1_login_success.png")
    # print("Login successful")
    return True



def navigate_to_new_quote(page, from_exception=False):
    """Navigate to the New Quote page"""
    if not from_exception:
        print("Expanding HealthX Plan menu...")
        page.click('text=HEALTHX PLAN')
        page.wait_for_timeout(1000)
    
    print("Clicking New Quote button...")
    page.click('text=New Quote')
    
    # Wait for the new quote page to load
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    page.wait_for_selector('text=Create New Quote', state='visible')
    # page.screenshot(path="2_new_quote_page.png")
    print("Navigated to New Quote page")
    return True

def select_antd_dropdown_option(page: Page, select_input_id: str, value_to_select: str, field_label: str):
    print(f"Selecting {field_label}: '{value_to_select}' (case-insensitive)")
    container_locator = page.locator(f"div.ant-select:has(#{select_input_id})").first
    if not container_locator.is_visible(timeout=1000):
        container_locator = page.locator(f"div.ant-form-item:has(#{select_input_id}) div.ant-select").first

    try:
        print(f"  Clicking {field_label} container to open dropdown...")
        container_locator.click()

        visible_dropdown_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
        dropdown_panel_locator = page.locator(visible_dropdown_selector).last
        expect(dropdown_panel_locator).to_be_visible(timeout=10000)
        print(f"  Dropdown panel is visible.")

        pattern = re.compile(f'^{re.escape(value_to_select)}$', re.IGNORECASE)

        def locate_option():
            return dropdown_panel_locator.locator('div.ant-select-item-option', has_text=pattern).first

        found = False
        for i in range(30):  # max scroll attempts
            print(f"  Scroll attempt {i+1}")
            option_locator = locate_option()
            if option_locator.is_visible(timeout=1000):
                found = True
                break
            # Scroll down
            page.evaluate("(el) => el.scrollBy(0, 100)", dropdown_panel_locator.locator('.rc-virtual-list-holder').element_handle())
            time.sleep(0.2)

        if not found:
            raise Exception(f"Option '{value_to_select}' not found in dropdown after scrolling.")

        option_locator.scroll_into_view_if_needed()
        expect(option_locator).to_be_visible(timeout=3000)
        option_locator.click()
        expect(dropdown_panel_locator).to_be_hidden(timeout=5000)

        selected_item_locator = container_locator.locator('.ant-select-selection-item')
        expect(selected_item_locator).to_have_text(pattern, timeout=3000)
        print(f"{field_label} selection verified.")

    except Exception as e:
        print(f"Error selecting {field_label} option '{value_to_select}': {e}")
        # page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_selection_error.png")
        raise
    

def select_antd_dropdown_by_label(page: Page, label_text: str, value_to_select: str, field_label: str):
    print(f"Selecting {field_label} (using label '{label_text}') with value: '{value_to_select}'")
    select_container = None
    dropdown_panel_locator = None

    try:
        # Locate label TD
        label_td_xpath = f"//td[contains(@class, 'custom-table-cell') and normalize-space(.)='{label_text}']"
        print(f"Locating label TD using XPath: {label_td_xpath}")
        label_td = page.locator(label_td_xpath).first
        expect(label_td).to_be_visible(timeout=10000)
        print("Found label TD.")

        # Find corresponding dropdown TD
        dropdown_td = label_td.locator("xpath=following-sibling::td[contains(@class, 'custom-table-cell')][1]")
        expect(dropdown_td).to_be_visible(timeout=5000)
        print("Found dropdown TD.")

        # Find select container
        select_container = dropdown_td.locator("div.ant-select").first
        expect(select_container).to_be_visible(timeout=5000)
        print("Found select container.")

        print(f"Clicking {field_label} container to open dropdown...")
        select_container.click()

        # Wait for dropdown
        visible_dropdown_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
        dropdown_panel_locator = page.locator(visible_dropdown_selector).last
        expect(dropdown_panel_locator).to_be_visible(timeout=10000)
        print("Dropdown panel is visible.")

        scrollable_panel = dropdown_panel_locator.locator('.rc-virtual-list-holder-inner')
        scroll_container = dropdown_panel_locator.locator('.rc-virtual-list-holder')

        # Compile match pattern
        pattern = re.compile(f'^{re.escape(value_to_select)}$', re.IGNORECASE)

        # Try scrolling and locating the desired option
        option_to_click = None
        found = False

        for i in range(30):
            print(f"Scroll attempt {i+1}")
            try:
                option_to_click = dropdown_panel_locator.locator('div.ant-select-item-option', has_text=pattern).first
                if option_to_click.is_visible(timeout=1000):
                    found = True
                    print("Found matching option during scroll.")
                    break
            except Exception:
                pass  # Not visible yet

            # Scroll the dropdown manually
            try:
                page.evaluate(
                    "(el) => el.scrollBy(0, 100)",
                    scroll_container.element_handle(timeout=2000)
                )
            except Exception:
                print("Warning: scroll container not available or not scrollable.")
                break

            time.sleep(0.2)

        if not found:
            raise Exception(f"Could not find option '{value_to_select}' in dropdown after scrolling.")

        # Final steps: click and verify
        expect(option_to_click).to_be_attached(timeout=5000)
        option_to_click.scroll_into_view_if_needed(timeout=5000)
        expect(option_to_click).to_be_visible(timeout=5000)

        print(f"Clicking {field_label} option '{value_to_select}'...")
        option_to_click.click(timeout=5000)

        expect(dropdown_panel_locator).to_be_hidden(timeout=5000)
        selected_item_locator = select_container.locator('.ant-select-selection-item')
        expect(selected_item_locator).to_have_text(pattern, timeout=5000)
        print(f"{field_label} selection verified.")

    except Exception as e:
        error_stage = "location/initial interaction"
        if select_container and dropdown_panel_locator:
            error_stage = "dropdown interaction/option selection"
        if option_to_click and not dropdown_panel_locator.is_hidden():
            error_stage = "verification"

        print(f"Error during {error_stage} for {field_label} (Label: '{label_text}', Value: '{value_to_select}'): {e}")
        # page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_error.png")
        raise Exception(f"Failed during {error_stage} for {field_label} using label '{label_text}'. Error: {e}") from e


def fill_input_by_label_or_placeholder(page: Page, value_to_fill: str, field_label: str, placeholder: str = None, label_text: str = None, input_type: str = "input"):
    print(f"Attempting to fill '{field_label}'...")

    selectors_to_try = []
    if placeholder:
        selectors_to_try.append(f'{input_type}[placeholder="{placeholder}"]')

    if label_text:
        selectors_to_try.append(f'//label[normalize-space()="{label_text}"]/ancestor::div[contains(@class, "ant-form-item")]//{input_type}')

    if not selectors_to_try:
        raise ValueError(f"Must provide at least placeholder or label_text for '{field_label}'")

    locator_found_and_filled = False
    for i, selector in enumerate(selectors_to_try):
        print(f"  Trying selector type {i+1} for '{field_label}': {selector}")
        try:
            field_locator = page.locator(selector)

            expect(field_locator).to_be_visible(timeout=5000)
            expect(field_locator).to_be_enabled(timeout=5000)

            field_locator.fill(value_to_fill)
            print(f"  Successfully filled '{field_label}' using selector type {i+1}.")
            locator_found_and_filled = True
            return

        except Exception as e:
            print(f"  Selector type {i+1} failed for '{field_label}': {type(e).__name__}")

    if not locator_found_and_filled:
        error_msg = f"Failed to find or fill '{field_label}' using provided placeholder or label selectors."
        print(error_msg)
        # page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_fill_error.png")
        raise Exception(error_msg)
    
    
def fill_input_by_id(page: Page, input_id: str, value_to_fill: str, field_label: str):
    print(f"Entering {field_label} value...")
    input_selector = f"#{input_id}"
    try:
        input_element = page.locator(input_selector)

        expect(input_element).to_be_visible(timeout=5000)
        expect(input_element).to_be_enabled(timeout=5000)

        input_element.fill(value_to_fill)
        print(f" {field_label} value '{value_to_fill}' entered successfully.")

    except Exception as e:
        print(f"Error filling {field_label} input with ID '{input_id}': {e}")
        # page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_fill_error.png")
        raise Exception(f"Failed to fill required field '{field_label}' with ID '{input_id}'. Error: {e}") from e
    
def fill_date_field(input_selector, target_date_str, page, field_label):
    """
    Selects a date using the Ant Design date picker.
    Now expects target_date_str in 'YYYY-MM-DD' format.
    Verifies the input field value matches the expected *display* format (likely DD-Mon-YYYY).
    """
    try:
        print(f"Selecting {field_label}...")
        # --- CHANGE PARSING FORMAT HERE ---
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: Invalid date format provided for {field_label}. Expected YYYY-MM-DD, got: {target_date_str}")
            raise
        # --- END CHANGE ---

        target_day = str(target_date.day)
        target_month_abbr = target_date.strftime("%b") # Still need Abbreviation for picker navigation
        target_year = str(target_date.year)
        target_date_title = target_date.strftime("%Y-%m-%d") # Title attribute uses ISO format
        # Determine the expected display format (assuming DD-Mon-YYYY based on warning)
        expected_display_value = target_date.strftime("%d-%b-%Y") # e.g., "08-Apr-2025"

        print(f"Target Date (parsed): {target_date_title}")
        print(f"Expected Display Value in Input: {expected_display_value}")

        # 2. Open Picker and Wait for Panel
        date_input = page.locator(input_selector)
        date_input.click()
        picker_panel = page.locator('.ant-picker-panel').first
        expect(picker_panel).to_be_visible(timeout=10000)

        # 3. Navigate Year if Needed (Logic remains the same)
        current_year_btn = picker_panel.locator('.ant-picker-year-btn')
        if current_year_btn.text_content() != target_year:
            print(f"  Navigating to year {target_year}...")
            current_year_btn.click()
            year_panel = picker_panel.locator('.ant-picker-year-panel')
            expect(year_panel).to_be_visible(timeout=5000) # Increased timeout slightly
            year_panel.locator('.ant-picker-cell-inner', has_text=target_year).click()
            expect(year_panel).to_be_hidden(timeout=5000) # Wait for transition back

        # 4. Navigate Month if Needed (Logic remains the same)
        current_month_btn = picker_panel.locator('.ant-picker-month-btn')
        if current_month_btn.text_content() != target_month_abbr:
            print(f"  Navigating to month {target_month_abbr}...")
            current_month_btn.click()
            month_panel = picker_panel.locator('.ant-picker-month-panel')
            expect(month_panel).to_be_visible(timeout=5000) # Increased timeout slightly
            month_panel.locator('.ant-picker-cell-inner', has_text=target_month_abbr).click()
            expect(month_panel).to_be_hidden(timeout=5000) # Wait for transition back

        # 5. Select Day using Title Attribute (Logic remains the same)
        print(f"  Selecting day {target_day} (title='{target_date_title}')...")
        day_cell_inner_div = picker_panel.locator(f'td[title="{target_date_title}"] div.ant-picker-cell-inner')
        day_cell_inner_div.click(timeout=5000)
        print(f"  Clicked day {target_day}.")
        expect(picker_panel).to_be_hidden(timeout=5000) # Wait for picker to close

        # Verify that the input field now displays the date in the expected *display* format
        print(f"  Verifying input field displays: '{expected_display_value}'")
        expect(date_input).to_have_value(expected_display_value, timeout=5000)

        print(f"{field_label} selection verified: input shows '{expected_display_value}'")
        # page.screenshot(path="after_date_selection.png")

    except Exception as e:
        print(f"Error selecting {field_label} '{target_date_str}': {e}")
        # page.screenshot(path="date_selection_error.png")
        raise Exception(f"Failed to select {field_label}. Error: {e}") from e
    
def create_new_organization(page: Page, client_name: str):
    print(f"Client '{client_name}' not found. Creating new organization...")

    # Go to Organisation
    page.click("text=Organisation")
    page.wait_for_selector("text=Groups", timeout=10000)

    # Click New Org
    page.click("button:has-text('New org')")
    page.wait_for_selector("text=Create New org", timeout=5000)

    # Fill Name and select 'No' for Blacklist
    fill_input_by_label_or_placeholder(
        page=page,
        value_to_fill=client_name,
        field_label="Organisation Name",
        label_text="Name"
    )
    page.click("label:has-text('No')")  # Choose 'No' for Blacklist

    # Save
    click_button_by_selector(page, "button:has-text('Save')", "Save Organisation")
    page.wait_for_timeout(3000)

    print(f"New organisation '{client_name}' created successfully.")

def fill_quote_form(page, QUOTE_DATA):
    """Fill in all fields in the quote form"""
    try:
        print("Filling quote form...")
        
        # Debug by taking screenshot before starting
        # page.screenshot(path="before_filling_form.png")
        
        # Let's list all input elements to understand the structure better
        print("Analyzing form structure...")
        
        
        # select_antd_dropdown_option(
        #     page=page,
        #     select_input_id="validateOnly_Organization_Name",
        #     value_to_select=QUOTE_DATA["client_name"],
        #     field_label="Client Name"
        # )
        
        try:
            select_antd_dropdown_option(
                page=page,
                select_input_id="validateOnly_Organization_Name",
                value_to_select=QUOTE_DATA["client_name"],
                field_label="Client Name"
            )
        except Exception as e:
            print(f"Client '{QUOTE_DATA['client_name']}' not found in dropdown. Initiating fallback flow.")
            
            # Create new organization
            create_new_organization(page, QUOTE_DATA["client_name"])

            # Return to New Quote
            navigate_to_new_quote(page, from_exception=True)

            # Try again after adding
            select_antd_dropdown_option(
                page=page,
                select_input_id="validateOnly_Organization_Name",
                value_to_select=QUOTE_DATA["client_name"],
                field_label="Client Name"
            )
                        
     
        fill_date_field(
            input_selector="#validateOnly_insurance_date",
            target_date_str=QUOTE_DATA["policy_start_date"],
            page=page,
            field_label="Policy Start Date"
            )

        select_antd_dropdown_option(
            page=page,
            select_input_id="validateOnly_Broker_Name",
            value_to_select=QUOTE_DATA["broker_name"],
            field_label="Broker Name"
        )
        select_antd_dropdown_option(
            page=page,
            select_input_id="validateOnly_acccount_manager",
            value_to_select=QUOTE_DATA["relationship_manager"],
            field_label="Relationship Manager"
        )
        
        # page.screenshot(path="3_form_filled_top.png")
                
        
        fill_input_by_label_or_placeholder(
            page=page,
            value_to_fill=QUOTE_DATA["adjustments_discount"],
            field_label="Adjustments Discount",
            placeholder="Enter adjustments discount",
            label_text="Adjustments Discount",
            input_type="input"
        )
        
        fill_input_by_label_or_placeholder(
            page=page,
            value_to_fill=QUOTE_DATA["discount_comment"],
            field_label="Adjustments Discount Comment",
            placeholder="Enter additional loading comment",
            label_text="Adjustments Discount Comment",
            input_type="textarea"
        )
        
        fill_input_by_id(
            page=page,
            input_id="validateOnly_brokerage_fee",
            value_to_fill=QUOTE_DATA["brokerage_fees"],
            field_label="Brokerage Fees"
        )

        # --- HealthX ---
        fill_input_by_id(
            page=page,
            input_id="validateOnly_HealthX",
            value_to_fill=QUOTE_DATA["healthx"],
            field_label="HealthX"
        )

        # --- TPA ---
        fill_input_by_id(
            page=page,
            input_id="validateOnly_TPA",
            value_to_fill=QUOTE_DATA["tpa"],
            field_label="TPA"
        )

        # --- Insurer ---
        fill_input_by_id(
            page=page,
            input_id="validateOnly_Insurer",
            value_to_fill=QUOTE_DATA["insurer"],
            field_label="Insurer"
        )
      
        # page.screenshot(path="4_form_filled_bottom.png")
        print("Form filled")
        return True
        
    except Exception as e:
        print(f"Error filling quote form: {e}")
        # page.screenshot(path="form_fill_error.png")
        # print("Error screenshot saved")
        return False


def click_button_by_selector(page: Page, selector: str, button_label: str, timeout: int = 10000):
    print(f"Attempting to click '{button_label}' using selector: {selector}")
    try:
        button_locator = page.locator(selector)
        
        print(f"  Waiting for '{button_label}' to be visible...")
        expect(button_locator).to_be_visible(timeout=timeout)
        print(f"  Waiting for '{button_label}' to be enabled...")
        expect(button_locator).to_be_enabled(timeout=timeout)

        print(f"  Clicking '{button_label}'...")
        button_locator.click(timeout=timeout)
        print(f"Successfully clicked '{button_label}'.")

    except Exception as e:
        # Construct a filename friendly name from the label
        safe_label = re.sub(r'[^\w\-]+', '_', button_label.lower())
        # screenshot_filename = f"error_clicking_{safe_label}.png"
        error_msg = f"Error clicking '{button_label}' with selector '{selector}': {e}"
        print(error_msg)
        # page.screenshot(path=screenshot_filename)
        # print(f"Error screenshot saved as '{screenshot_filename}'")
        raise Exception(error_msg) from e
    
def upload_census_file(page,CENSUS_FILE_PATH):
    """Upload census file to the form"""
    try:
        print("Uploading census file...")
        
        # Check if file exists
        if not os.path.exists(CENSUS_FILE_PATH):
            print(f"Error: Census file not found at {CENSUS_FILE_PATH}")
            return False
        
        # Click on upload button
        upload_button = page.locator('button:has-text("Upload Census")').first
        upload_button.click()
        page.wait_for_timeout(1000)
        
        # Set the file input - looking for the file input that appears after clicking upload button
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(CENSUS_FILE_PATH)
        
        # Wait for upload to complete - checking for some indication of completion
        page.wait_for_timeout(5000)  
        
        # Take screenshot after file upload
        # page.screenshot(path="5_file_uploaded.png")
        print("Census file uploaded")
        return True
        
    except Exception as e:
        print(f"Error uploading census file: {e}")
        # page.screenshot(path="file_upload_error.png")
        # print("Error screenshot saved")
        return False

def add_commas(number):
    try:
        # Ensure it's an integer first
        number = int(number)
        return f"{number:,}"
    except ValueError:
        raise ValueError(f"Invalid number: {number}")
def fill_benefit_details(page: Page, BENEFIT_DETAILS_DATA):
    print(BENEFIT_DETAILS_DATA)
    """Fills the benefit details table that appears after census confirmation."""
    print("Starting to fill benefit details table...")
    try:
        # --- 1. Additional Loading (Input) ---
        fill_input_by_id(
            page=page,
            input_id="Category-A_Category-A-summary-additionalLoading",
            value_to_fill=BENEFIT_DETAILS_DATA["additional_loading"],
            field_label="Additional Loading"
        )

        # --- 2. NAS Network (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="NAS Network:",
            value_to_select=BENEFIT_DETAILS_DATA["nas_network"],
            field_label="NAS Network"
        )

        # --- 3. Plan (Dropdown - Skip, as it's disabled in provided HTML) ---
        print("Skipping 'Plan' dropdown as it appears disabled.")

        # --- 4. Annual Medical (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Annual Medical:",
            value_to_select=BENEFIT_DETAILS_DATA["annual_medical"],
            field_label="Annual Medical"
        )

        # --- 5. IP Room Type (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="IP Room Type:",
            value_to_select=BENEFIT_DETAILS_DATA["ip_room_type"],
            field_label="IP Room Type"
        )

        # --- 6. Copayment on all IP and Day-Case... (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Copayment on all IP and Day-Case Benefits subject to cap of 500 AED per encounter:",
            value_to_select=BENEFIT_DETAILS_DATA["copayment_ip_daycase"],
            field_label="Copayment IP/Day-Case"
        )

        # --- 7. Deductible for Consultation (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Deductible for Consultation:",
            value_to_select=BENEFIT_DETAILS_DATA["deductible_consultation"],
            field_label="Deductible for Consultation"
        )

        # --- 8. Territorial cover (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Territorial cover:",
            value_to_select=BENEFIT_DETAILS_DATA["territorial_cover"],
            field_label="Territorial Cover"
        )

        # --- 9. Diagnostic Investigation OP Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Diagnostic Investigation OP Copay:",
            value_to_select=BENEFIT_DETAILS_DATA["diagnostic_op_copay"],
            field_label="Diagnostic Investigation OP Copay"
        )

        # --- 10. Pharmacy Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Pharmacy Copay:",
            value_to_select=BENEFIT_DETAILS_DATA["pharmacy_copay"],
            field_label="Pharmacy Copay"
        )

        # --- 11. Pharmacy Limit (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Pharmacy Limit:",
            value_to_select=BENEFIT_DETAILS_DATA["pharmacy_limit"],
            field_label="Pharmacy Limit"
        )

        # --- 12. Medication Type (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Medication Type:",
            value_to_select=BENEFIT_DETAILS_DATA["medication_type"],
            field_label="Medication Type"
        )

        # --- 13. PEC (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="PEC:",
            value_to_select=BENEFIT_DETAILS_DATA["pec"],
            field_label="PEC"
        )

        try:
            # --- Maternity Limit (Dropdown) ---
            select_antd_dropdown_by_label(
                page=page,
                label_text="Maternity Limit:",
                value_to_select=BENEFIT_DETAILS_DATA["maternity_limit"],
                field_label="Maternity Limit"
            )
        except:
            comma_number=add_commas(BENEFIT_DETAILS_DATA["maternity_limit"])
            select_antd_dropdown_by_label(
                page=page,
                label_text="Maternity Limit:",
                value_to_select=comma_number,
                field_label="Maternity Limit"
            )

        # --- Maternity Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Maternity Copay:",
            value_to_select=BENEFIT_DETAILS_DATA["maternity_copay"],
            field_label="Maternity Copay"
        )
        try:
            # --- Dental Limit (Dropdown) ---
            select_antd_dropdown_by_label(
                page=page,
                label_text="Dental Limit:",
                value_to_select=BENEFIT_DETAILS_DATA["dental_limit"],
                field_label="Dental Limit"
            )
        except:
            comma_number=add_commas(BENEFIT_DETAILS_DATA["dental_limit"])
            select_antd_dropdown_by_label(
                page=page,
                label_text="Dental Limit:",
                value_to_select=comma_number,
                field_label="Dental Limit"
            )

        # --- Dental Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Dental Copay:",
            value_to_select=BENEFIT_DETAILS_DATA["dental_copay"],
            field_label="Dental Copay"
        )

        # --- Optical Limit (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Optical Limit:",
            value_to_select=BENEFIT_DETAILS_DATA["optical_limit"],
            field_label="Optical Limit"
        )

        # --- Optical Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Optical Copay:",
            value_to_select=BENEFIT_DETAILS_DATA["optical_copay"],
            field_label="Optical Copay"
        )

        
        # --- Repatriation (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Repatriation of Mortal Remains to the Country of Domicile:", # Exact label text
            value_to_select=BENEFIT_DETAILS_DATA["repatriation"],
            field_label="Repatriation Limit"
        )
            
        # --- Nursing at home (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Nursing at home by a registered nurse (following an immediate Inpatient treatment):",
            value_to_select=BENEFIT_DETAILS_DATA["nursing_at_home"],
            field_label="Nursing at Home Limit"
        )
        
        # --- OP Psychiatric Limit (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="OP Psychiatric Benefits Limit:",
            value_to_select=BENEFIT_DETAILS_DATA["op_psychiatric_limit"],
            field_label="OP Psychiatric Limit"
        )

        # --- OP Psychiatric Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="OP Psychiatric Benefits copay:",
            value_to_select=BENEFIT_DETAILS_DATA["op_psychiatric_copay"],
            field_label="OP Psychiatric Copay"
        )

        # --- Alternative Medicine Limit (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Alternative Medicine Limit:",
            value_to_select=BENEFIT_DETAILS_DATA["alternative_medicine_limit"],
            field_label="Alternative Medicine Limit"
        )

        # --- Alternative Medicine Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Alternative Medicine copay:",
            value_to_select=BENEFIT_DETAILS_DATA["alternative_medicine_copay"],
            field_label="Alternative Medicine Copay"
        )

        try:
        # --- Routine Health Check-up (Dropdown) ---
            select_antd_dropdown_by_label(
                page=page,
                label_text="Routine Health Check-up:",
                value_to_select=BENEFIT_DETAILS_DATA["routine_health_checkup"],
                field_label="Routine Health Check-up"
            )
        except:
            comma_number=add_commas(BENEFIT_DETAILS_DATA["routine_health_checkup"])
            # --- Routine Health Check-up (Dropdown) ---
            select_antd_dropdown_by_label(
                page=page,
                label_text="Routine Health Check-up:",
                value_to_select=comma_number,
                field_label="Routine Health Check-up"
            )
            

        # --- Physiotherapy Limit (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Physiotherapy Limit:",
            value_to_select=BENEFIT_DETAILS_DATA["physiotherapy_limit"],
            field_label="Physiotherapy Limit"
        )

        # --- Physiotherapy Copay (Dropdown) ---
        select_antd_dropdown_by_label(
            page=page,
            label_text="Physiotherapy copay:",
            value_to_select=BENEFIT_DETAILS_DATA["physiotherapy_copay"],
            field_label="Physiotherapy Copay"
        )


        print("Benefit details table filled successfully.")
        # page.screenshot(path="10_benefit_details_filled.png")
        return True

    except Exception as e:
        print(f"Error filling benefit details table: {e}")
        # page.screenshot(path="error_filling_benefit_details.png")
        # Re-raise the exception to stop the script if benefits are critical
        raise Exception(f"Failed to fill benefit details. Error: {e}") from e

def get_page_css(page: Page) -> str:
    """
    Extracts linked and inline CSS from the page.
    Handles potential errors during fetching linked CSS.
    """
    print("    Extracting CSS links...")
    css_links = page.eval_on_selector_all(
        'link[rel="stylesheet"]',
        '''(links) =>
            links.map((link) => link.href)'''
    )

    print("    Extracting inline CSS styles...")
    inline_styles = page.eval_on_selector_all(
        'style',
        '''(styles) =>
            styles.map((style) => style.textContent || '')'''
    )

    embedded_css = ""

    # Add inline styles first
    for style_content in inline_styles:
        embedded_css += f"<style>\n{style_content}\n</style>\n"
    print(f"    Found {len(inline_styles)} inline <style> blocks.")

    # Fetch and embed linked CSS
    print(f"    Fetching content from {len(css_links)} linked stylesheets...")
    fetched_css_count = 0
    for i, href in enumerate(css_links):
        if not href: # Skip empty hrefs
            print(f"      Skipping empty link href (index {i}).")
            continue
        print(f"      Fetching: {href[:100]}{'...' if len(href)>100 else ''}")
        try:
            # Use page.request within the browser context for better compatibility
            response = page.request.get(href)
            if response.ok:
                css_content = response.text()
                # Basic check to avoid embedding massive non-CSS files by mistake
                if css_content and ('{' in css_content or '}' in css_content): # Simple heuristic
                    embedded_css += f"<style>\n/* From: {href} */\n{css_content}\n</style>\n"
                    fetched_css_count += 1
                    print(f"        Successfully fetched and embedded (length: {len(css_content)}).")
                else:
                    print(f"        Skipping embedding - response doesn't look like CSS or is empty.")
            else:
                print(f"        Failed to fetch: Status {response.status} {response.status_text}")
        except Exception as fetch_err:
            print(f"        Error fetching CSS from {href}: {fetch_err}")

    print(f"    Successfully fetched and embedded {fetched_css_count} linked stylesheets.")
    return embedded_css


def generate_tob_preview_pdf(page: Page, context: BrowserContext, output_dir: str = ".", filename_prefix: str = "tob_preview"):
    """
    Clicks 'Preview', extracts HTML & CSS, saves HTML, generates PDF.

    Args:
        page: The main Playwright Page object.
        context: The Playwright BrowserContext object.
        output_dir: Directory for output files.
        filename_prefix: Prefix for filenames.

    Returns:
        str: Path to the generated PDF file if successful, otherwise None.
    """
    print("Generating TOB Preview PDF and HTML...")
    pdf_page = None
    slider_html_raw = None
    full_html_for_pdf = None
    pdf_save_path = None
    slider_content_element = None # Define here for finally block

    try:
        # 1. Click Preview button
        print("  Locating and clicking 'Preview' button...")
        preview_button_selector = 'button:has-text("Preview")'
        preview_button = page.locator(preview_button_selector).first
        expect(preview_button).to_be_visible(timeout=10000)
        expect(preview_button).to_be_enabled(timeout=10000)
        preview_button.click()
        print("  'Preview' button clicked.")

        # 2. Wait for the slider/drawer to be visible and stable
        print("  Waiting for TOB Preview slider/drawer to appear...")
        slider_content_selector = ".ant-drawer.ant-drawer-open .ant-drawer-content-wrapper"
        slider_content_element = page.locator(slider_content_selector).first
        expect(slider_content_element).to_be_visible(timeout=15000)
        expect(page.locator(f"{slider_content_selector} :text('TOB Preview')")).to_be_visible(timeout=5000)
        print("  TOB Preview slider is visible.")
        page.wait_for_timeout(1500) # Wait for final rendering

        # 3. Extract the HTML of the slider content
        print("  Extracting HTML content from the slider...")
        slider_html_raw = slider_content_element.evaluate("element => element.outerHTML")
        if not slider_html_raw:
            raise Exception("Failed to extract HTML from the slider content element.")
        print(f"  Extracted raw HTML (length: {len(slider_html_raw)} characters).")

        # --- ADDED: Extract CSS from the *main page* ---
        print("  Extracting CSS from main page...")
        page_css = get_page_css(page)
        # --- END CSS EXTRACTION ---

        # --- Combine CSS and HTML ---
        print("  Combining extracted CSS and HTML for PDF generation...")
        # Basic HTML structure to wrap the content and styles
        full_html_for_pdf = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TOB Preview</title>
            {page_css}
            <style>
               /* Add any overrides or print-specific styles here if needed */
               body {{ margin: 0; padding: 0; background-color: #ffffff; }} /* Ensure clean body */
               .ant-drawer-content-wrapper {{
                   /* Override drawer positioning for standalone rendering */
                   position: relative !important;
                   width: 100% !important;
                   max-width: 1000px; /* Maintain original max width */
                   margin: 0 auto; /* Center it */
                   box-shadow: none !important; /* Remove shadow */
               }}
                /* Hide the close button in PDF */
               .ant-drawer-close {{ display: none !important; }}
               /* Ensure page breaks work correctly if content is long */
               .pagebreak {{ page-break-before: always; }}

            </style>
        </head>
        <body>
            {slider_html_raw}
        </body>
        </html>
        """
        # --- END COMBINATION ---

        # --- Create the output directory if it doesn't exist ---
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prefix = re.sub(r'[^\w\-]+', '_', filename_prefix)

        # 4. Generate PDF using a new page
        print("  Preparing to generate PDF in isolation...")
        pdf_page = context.new_page()
        print("    Setting combined content in temporary page...")
        # Load the full HTML with embedded CSS
        pdf_page.set_content(full_html_for_pdf, wait_until='networkidle')
        print("    Content set. Generating PDF...")

        pdf_filename = f"{safe_prefix}_{timestamp}.pdf"
        pdf_save_path = os.path.join(output_dir, pdf_filename)

        pdf_page.pdf(
            path=pdf_save_path,
            print_background=True,
            format='A4',
            margin={'top': '20px', 'bottom': '20px', 'left': '20px', 'right': '20px'},
        )
        print(f"    PDF generated successfully: {pdf_save_path}")

        # 5. Close the temporary page
        pdf_page.close()
        print("  Temporary PDF generation page closed.")

        # 6. Optional: Close the slider on the original page
        try:
            close_button_selector = ".ant-drawer.ant-drawer-open .ant-drawer-close"
            close_button = page.locator(close_button_selector)
            if close_button.is_visible(timeout=1000):
                print("  Closing the TOB Preview slider on the main page...")
                close_button.click()
                expect(slider_content_element).to_be_hidden(timeout=5000)
                print("  Slider closed.")
            else:
                print("  Could not find standard close button, slider might remain open.")
        except Exception as close_err:
            print(f"  Warning: Could not automatically close the slider: {close_err}")

        print(f"TOB Preview PDF and HTML generation complete.")
        return pdf_save_path

    except Exception as e:
        print(f"Error during TOB Preview generation: {e}")
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # error_screenshot_path = os.path.join(output_dir, f"error_{filename_prefix}_{timestamp}.png")
        # try:
        #     page.screenshot(path=error_screenshot_path)
        #     print(f"Error screenshot saved to {error_screenshot_path}")
        # except Exception as screen_err:
        #     print(f"Could not take error screenshot: {screen_err}")

        return None

    finally:
        # Ensure the temporary page is closed
        if pdf_page and not pdf_page.is_closed():
            try:
                pdf_page.close()
                print("  Ensured temporary PDF page is closed.")
            except Exception as close_err:
                print(f"  Error closing lingering temporary page: {close_err}")


def save_quote_and_download_pdf(page: Page,context, timeout: int = 60000):
    print("Attempting to finalize quote and save PDF...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"quote_summary_{timestamp}.pdf"
    pdf_save_path = os.path.join(os.getcwd(), pdf_filename)
    print(f"  PDF will be saved as: {pdf_save_path}")

    try:
        generate_tob_preview_pdf(page, context)
        return True   
    except Exception as e:
        print(f"Error during final save and PDF download: {e}")
        # page.screenshot(path="error_saving_quote_pdf.png")
        raise Exception(f"Failed to save quote and download PDF. Error: {e}") from e
    

def main(QUOTE_DATA, BENEFIT_DETAILS_DATA, CENSUS_FILE_PATH):
    """Main function to run the entire process
    
    Args:
        QUOTE_DATA: Dictionary with quote data
        BENEFIT_DETAILS_DATA: Dictionary with benefit details data
        CENSUS_FILE_PATH: Path to the census Excel file
        
    Returns:
        dict: Dictionary with status information:
            - success (bool): Whether the automation was successful
            - pdf_path (str): Path to the generated PDF, if any
            - message (str): Status message
    """
    bb, session = None, None
    pdf_path = None
    
    try:
        bb, session = setup_browser()

        with sync_playwright() as p:
            # browser = p.chromium.connect_over_cdp(session.connect_url) # For Browserbase
            browser = p.chromium.launch(
            headless=True,  # Set to True for production
            # args=[
            # '--disable-print-preview']
            ) # For local debugging

            context = browser.new_context()
            page = context.new_page()

            page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
            page.set_default_timeout(60000)

            if login(page):
                page.wait_for_timeout(2000)
                if navigate_to_new_quote(page):
                    page.wait_for_timeout(2000)
                    if fill_quote_form(page, QUOTE_DATA):
                        page.wait_for_timeout(1000)
                        if upload_census_file(page, CENSUS_FILE_PATH):
                            print("Census file uploaded, proceeding...")

                            # --- CLICK OK ON THE FIRST (MAPPING) MODAL ---
                            mapping_modal_selector = '.ant-modal-wrap:not([style*="display: none"]) .ant-modal-content:has-text("mapped CSV data")'
                            ok_button_in_mapping_modal_selector = f"{mapping_modal_selector} .ant-modal-footer button:has-text('OK')"
                            print(f"Waiting for Mapping Confirmation modal ({mapping_modal_selector}) to be visible...")
                            expect(page.locator(mapping_modal_selector)).to_be_visible(timeout=15000)
                            print(f"Clicking OK button in Mapping modal using selector: {ok_button_in_mapping_modal_selector}")
                            click_button_by_selector(page, ok_button_in_mapping_modal_selector, "Mapping Confirmation OK", 15000)
                            print("Mapping confirmed.")
                            # page.screenshot(path="7_mapping_confirmed.png")

                            # --- WAIT FOR FIRST MODAL TO CLOSE & SECOND MODAL TO APPEAR ---
                            print("Waiting for Mapping modal to close...")
                            expect(page.locator(mapping_modal_selector)).to_be_hidden(timeout=10000)
                            print("Waiting for 'Census list' modal to appear...")
                            census_list_modal_header_selector = '.ant-modal-header:has-text("Census list")'
                            census_list_modal_content_selector = '.ant-modal-wrap:not([style*="display: none"]) .ant-modal-content'
                            visible_census_list_modal_selector = f"{census_list_modal_content_selector}:has({census_list_modal_header_selector})"
                            expect(page.locator(visible_census_list_modal_selector)).to_be_visible(timeout=20000)
                            print("'Census list' modal is visible.")
                            # page.screenshot(path="8_census_list_modal_visible.png")

                            # --- CLICK OK ON THE SECOND (CENSUS LIST) MODAL ---
                            print("Attempting to click OK on the 'Census list' modal...")
                            ok_button_in_census_modal_selector = f"{visible_census_list_modal_selector} .ant-modal-footer button:has-text('OK')"
                            print(f"Using specific selector for Census List OK: {ok_button_in_census_modal_selector}")
                            click_button_by_selector(page, ok_button_in_census_modal_selector, "Census List Confirmation OK", 15000)
                            print("Clicked OK on 'Census list' modal.")

                            # --- WAIT FOR SECOND MODAL TO CLOSE ---
                            print("Waiting for 'Census list' modal to close...")
                            expect(page.locator(visible_census_list_modal_selector)).to_be_hidden(timeout=10000)
                            print("'Census list' modal closed.")
                            # page.screenshot(path="9_census_list_modal_closed.png")

                            # --- WAIT and FILL BENEFIT DETAILS ---
                            print("Waiting 3 seconds before filling benefit details...")
                            page.wait_for_timeout(3000) # User requested wait

                            # Call the new function to fill the benefit details table
                            if fill_benefit_details(page, BENEFIT_DETAILS_DATA):
                                print("Benefit details successfully filled.")

                                # --- SAVE QUOTE AND DOWNLOAD PDF ---
                                print("Waiting slightly before final save...")
                                page.wait_for_timeout(2000) # Allow UI to potentially update after last fill

                                # Modified to capture the PDF path
                                pdf_path = generate_tob_preview_pdf(page, context)
                                if pdf_path:
                                    print(f"Quote saved and PDF downloaded successfully! Path: {pdf_path}")
                                    # page.screenshot(path="11_quote_saved_pdf_downloaded.png") # Final success screenshot
                                else:
                                    print("Failed to save the PDF after clicking save.")
                                    # page.screenshot(path="11_pdf_save_failed.png")
                                    return {
                                        "success": False,
                                        "pdf_path": None,
                                        "message": "Failed to generate PDF"
                                    }
                            else:
                                # This case should ideally be handled by exceptions within fill_benefit_details
                                print("Benefit details filling failed (should have raised exception).")
                                return {
                                    "success": False,
                                    "pdf_path": None,
                                    "message": "Failed to fill benefit details"
                                }

                            print("Process steps completed successfully!")
                            # page.screenshot(path="11_process_completed.png") # Final state screenshot (updated number)
                            
                            # Successful completion
                            return {
                                "success": True,
                                "pdf_path": pdf_path,
                                "message": "Process completed successfully"
                            }

            print("Closing browser resources...")
            context.close()
            browser.close()
            
            # If we get here without returning, something didn't complete
            return {
                "success": False,
                "pdf_path": pdf_path,
                "message": "Process did not complete all steps"
            }

    except Exception as e:
        print(f"AN ERROR OCCURRED DURING EXECUTION: {e}")
        if 'page' in locals() and page and not page.is_closed():
            try:
                # page.screenshot(path="final_error_screenshot.png")
                print("Final error screenshot saved as 'final_error_screenshot.png'")
            except Exception as screen_err:
                print(f"Could not take final error screenshot: {screen_err}")
        
        # Return error information
        return {
            "success": False,
            "pdf_path": pdf_path,
            "message": f"Error during execution: {str(e)}"
        }
    
    finally:
        if session and bb:
            try:
                print(f"Releasing Browserbase session {session.id}...")
                bb.sessions.update(session.id, status="REQUEST_RELEASE", project_id=PROJECT_ID)
                print(f"Browserbase session {session.id} released successfully.")
            except Exception as release_error:
                print(f"Error releasing Browserbase session: {release_error}")
        else:
            print("Skipping Browserbase session release (session/bb object not available).")


if __name__ == "__main__":
    main()
