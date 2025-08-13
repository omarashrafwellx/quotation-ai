"""
Browser automation manager for quote generation.
Refactored from multi_category_browser_base.py
"""
import os
import re
from typing import Dict, Any, List
from datetime import datetime
from browserbase import Browserbase
from playwright.async_api import async_playwright, expect, Page, BrowserContext
from src.core.config import settings
import shutil
from src.services.automation.smart_ai_selection import ai_smart_selecting_fun
import asyncio



# Configuration
EMAIL =settings.EMAIL
PASSWORD = settings.PASSWORD
BROWSERBASE_API_KEY =settings.BROWSERBASE_API_KEY
PROJECT_ID = settings.BROWSERBASE_PROJECT_ID


# Helper function for creating space-insensitive regex patterns
def _create_space_insensitive_pattern(value_to_match: str) -> re.Pattern:
    """
    Creates a regex pattern that matches value_to_match case-insensitively,
    ignoring leading/trailing whitespace in the target string, and treating
    internal sequences of whitespace in the target string as equivalent to
    no space or flexible spacing based on the input.
    Effectively, "My Value" from input matches "MyValue", "My Value", "  My  Value  " in target.
    An empty or all-space value_to_match will result in a pattern matching
    empty or all-space target strings.
    """
    stripped_value = value_to_match.strip() # Normalize input: "  A B  " -> "A B"

    if not stripped_value:
        # Input is empty or all spaces. Match target that is empty or all spaces.
        return re.compile(r"^\s*$", re.IGNORECASE)
    else:
        # Input has non-whitespace characters.
        # Remove all internal spaces from the (already stripped) input. "A B" -> "AB"
        core_value_logic = stripped_value.replace(" ", "")
        
        # Escape each character of the core logic and join with r"\s*"
        # "AB" -> [re.escape('A'), re.escape('B')] -> re.escape('A') + r"\s*" + re.escape('B')
        # Example: "A\s*B"
        regex_core_parts = [re.escape(char) for char in core_value_logic]
        dynamic_regex_core = r"\s*".join(regex_core_parts)
        
        # Final pattern:
        # ^\s*      : matches leading whitespace in the target string
        # {dynamic_regex_core} : matches the core characters with flexible spacing
        # \s*$      : matches trailing whitespace in the target string
        return re.compile(rf"^\s*{dynamic_regex_core}\s*$", re.IGNORECASE)


def setup_browser(): # Browserbase SDK calls are typically synchronous
    """Initialize Browserbase session and set up browser"""
    bb = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = bb.sessions.create(project_id=PROJECT_ID)
    return bb, session

async def login(page: Page):
    """Handle login process"""
    print("Navigating to login page...")
    await page.goto("https://app-qa-hqt.wellx.ai/login", wait_until="networkidle")
    
    print("Filling login form...")
    await page.fill('input[placeholder="Enter your email"]', EMAIL)
    await page.fill('input[placeholder="Enter your Password"]', PASSWORD)
    
    print("Clicking login button...")
    await page.click('button:has-text("Login")')
    
    # Wait for dashboard to load
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(5000) # Replaced time.sleep
    
    # Take screenshot of successful login
    # # await page.screenshot(path="1_login_success.png")
    print("Login successful - Screenshot saved")
    return True

async def navigate_to_new_quote(page: Page, from_exception=False):
    """Navigate to the New Quote page"""
    if not from_exception:
        print("Expanding HealthX Plan menu...")
        await page.click('text=HEALTHX PLAN')
        await page.wait_for_timeout(1000)
    
    print("Clicking New Quote button...")
    await page.click('text=New Quote')
    
    # Wait for the new quote page to load
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000) # Replaced time.sleep
    await page.wait_for_selector('text=Create New Quote', state='visible')
    # await page.screenshot(path="2_new_quote_page.png")
    print("Navigated to New Quote page - Screenshot saved")
    return True

async def select_antd_dropdown_option(page: Page, select_input_id: str, value_to_select: str, field_label: str):
    print(f"Selecting {field_label}: '{value_to_select}' (case-insensitive, space-agnostic)")
    container_locator = page.locator(f"div.ant-select:has(#{select_input_id})").first
    if not await container_locator.is_visible(timeout=1000):
        container_locator = page.locator(f"div.ant-form-item:has(#{select_input_id}) div.ant-select").first

    try:
        print(f"  Clicking {field_label} container to open dropdown...")
        await container_locator.click()

        visible_dropdown_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
        dropdown_panel_locator = page.locator(visible_dropdown_selector).last
        await expect(dropdown_panel_locator).to_be_visible(timeout=10000)
        print(f"  Dropdown panel is visible.")

        pattern = _create_space_insensitive_pattern(value_to_select)

        async def locate_option(): # Inner function can be async too
            return dropdown_panel_locator.locator('div.ant-select-item-option', has_text=pattern).first
        
        found = False
        option_locator = None # Define option_locator here for broader scope
        for i in range(30):  # max scroll attempts
            print(f"  Scroll attempt {i+1}")
            option_locator = await locate_option()
            if await option_locator.is_visible(timeout=1000):
                found = True
                break
            # Scroll down
            # Use element_handle for evaluation context
            dropdown_holder_handle = await dropdown_panel_locator.locator('.rc-virtual-list-holder').element_handle()
            if dropdown_holder_handle:
                 await page.evaluate("(el) => el.scrollBy(0, 100)", dropdown_holder_handle)
                 await dropdown_holder_handle.dispose() # Dispose handle after use
            await page.wait_for_timeout(200) # Replaced time.sleep

        if not found or not option_locator: # Check option_locator as well
            raise Exception(f"Option '{value_to_select}' not found in dropdown after scrolling.")

        await option_locator.scroll_into_view_if_needed(timeout=5000)
        await expect(option_locator).to_be_visible(timeout=3000)
        print(f"  Option '{value_to_select}' is visible. Clicking...")
        await option_locator.click()
        print(f"  Clicked option '{value_to_select}'.")
        await page.wait_for_timeout(500) 

        await expect(dropdown_panel_locator).to_be_hidden(timeout=5000)
        print(f"  Dropdown panel is hidden.")

        selected_item_locator = container_locator.locator('.ant-select-selection-item')
        await expect(selected_item_locator).to_have_text(pattern, timeout=3000)
        print(f"{field_label} selection verified.")

    except Exception as e:
        print(f"Error selecting {field_label} option '{value_to_select}': {e}")
        # await page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_selection_error.png")
        raise
    

async def select_antd_dropdown_by_label(page: Page, label_text: str, value_to_select: str, field_label: str):
    print(f"Selecting {field_label} (using label '{label_text}') with value: '{value_to_select}' (case-insensitive, space-agnostic)")
    select_container = None
    dropdown_panel_locator = None
    option_to_click = None # Define for broader scope

    try:
        # Locate label TD
        label_td_xpath = f"//td[contains(@class, 'custom-table-cell') and normalize-space(.)='{label_text}']"
        print(f"Locating label TD using XPath: {label_td_xpath}")
        label_td = page.locator(label_td_xpath).first
        await expect(label_td).to_be_visible(timeout=10000)
        print("Found label TD.")

        # Find corresponding dropdown TD
        dropdown_td = label_td.locator("xpath=following-sibling::td[contains(@class, 'custom-table-cell')][1]")
        await expect(dropdown_td).to_be_visible(timeout=5000)
        print("Found dropdown TD.")

        # Find select container
        select_container = dropdown_td.locator("div.ant-select").first
        await expect(select_container).to_be_visible(timeout=5000)
        print("Found select container.")

        print(f"Clicking {field_label} container to open dropdown...")
        await select_container.click()

        # Wait for dropdown
        visible_dropdown_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
        dropdown_panel_locator = page.locator(visible_dropdown_selector).last
        await expect(dropdown_panel_locator).to_be_visible(timeout=10000)
        print("Dropdown panel is visible.")

        scroll_container_locator = dropdown_panel_locator.locator('.rc-virtual-list-holder') # Locator for scroll container

        pattern = _create_space_insensitive_pattern(value_to_select)
        found = False

        for i in range(30):
            print(f"Scroll attempt {i+1}")
            try:
                option_to_click = dropdown_panel_locator.locator('div.ant-select-item-option', has_text=pattern).first
                if await option_to_click.is_visible(timeout=1000): # Use await here
                    found = True
                    print("Found matching option during scroll.")
                    break
            except Exception:
                pass

            try:
                scroll_container_handle = await scroll_container_locator.element_handle(timeout=2000)
                if scroll_container_handle:
                    await page.evaluate("(el) => el.scrollBy(0, 100)", scroll_container_handle)
                    await scroll_container_handle.dispose()
                else:
                    print("Warning: scroll container not found for scrolling.")
                    break # No point scrolling if container not found
            except Exception as scroll_ex:
                print(f"Warning: scroll container not available or not scrollable: {scroll_ex}")
                break

            await page.wait_for_timeout(200) 

        if not found or not option_to_click: # Check option_to_click as well
            raise Exception(f"Could not find option '{value_to_select}' in dropdown after scrolling.")

        await expect(option_to_click).to_be_attached(timeout=5000) 
        await option_to_click.scroll_into_view_if_needed(timeout=5000)
        await expect(option_to_click).to_be_visible(timeout=5000)

        print(f"Clicking {field_label} option '{value_to_select}'...")
        await option_to_click.click(timeout=5000)

        print(f"  Clicked option '{value_to_select}'.")
        await page.wait_for_timeout(500) 
        
        await expect(dropdown_panel_locator).to_be_hidden(timeout=5000)
        selected_item_locator = select_container.locator('.ant-select-selection-item')
        await expect(selected_item_locator).to_have_text(pattern, timeout=5000)
        print(f"{field_label} selection verified.")

    except Exception as e:
        error_stage = "location/initial interaction"
        if select_container and dropdown_panel_locator:
            error_stage = "dropdown interaction/option selection"
        
        if option_to_click and dropdown_panel_locator and not await dropdown_panel_locator.is_hidden():
            error_stage = "verification"

        print(f"Error during {error_stage} for {field_label} (Label: '{label_text}', Value: '{value_to_select}'): {e}")
        # await page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_error.png")
        raise Exception(f"Failed during {error_stage} for {field_label} using label '{label_text}'. Error: {e}") from e


async def fill_input_by_label_or_placeholder(page: Page, value_to_fill: str, field_label: str, placeholder: str = None, label_text: str = None, input_type: str = "input"):
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

            await expect(field_locator).to_be_visible(timeout=5000)
            await expect(field_locator).to_be_enabled(timeout=5000)

            await field_locator.fill(value_to_fill)
            print(f"  Successfully filled '{field_label}' using selector type {i+1}.")
            locator_found_and_filled = True
            return

        except Exception as e:
            print(f"  Selector type {i+1} failed for '{field_label}': {type(e).__name__}")

    if not locator_found_and_filled:
        error_msg = f"Failed to find or fill '{field_label}' using provided placeholder or label selectors."
        print(error_msg)
        # await page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_fill_error.png")
        raise Exception(error_msg)
    
    
async def fill_input_by_id(page: Page, input_id: str, value_to_fill: str, field_label: str):
    print(f"Entering {field_label} value...")
    input_selector = f"#{input_id}"
    try:
        input_element = page.locator(input_selector)

        await expect(input_element).to_be_visible(timeout=5000)
        await expect(input_element).to_be_enabled(timeout=5000)

        await input_element.fill(value_to_fill)
        print(f" {field_label} value '{value_to_fill}' entered successfully.")

    except Exception as e:
        print(f"Error filling {field_label} input with ID '{input_id}': {e}")
        # await page.screenshot(path=f"{field_label.replace(' ', '_').lower()}_fill_error.png")
        raise Exception(f"Failed to fill required field '{field_label}' with ID '{input_id}'. Error: {e}") from e
    
async def fill_date_field(input_selector: str, target_date_str: str, page: Page, field_label: str):
    """
    Selects a date using the Ant Design date picker.
    Now expects target_date_str in 'YYYY-MM-DD' format.
    Verifies the input field value matches the expected *display* format (likely DD-Mon-YYYY).
    """
    try:
        print(f"Selecting {field_label}...")
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: Invalid date format provided for {field_label}. Expected YYYY-MM-DD, got: {target_date_str}")
            raise

        target_day = str(target_date.day)
        target_month_abbr = target_date.strftime("%b")
        target_year = str(target_date.year)
        target_date_title = target_date.strftime("%Y-%m-%d")
        expected_display_value = target_date.strftime("%d-%b-%Y")

        print(f"Target Date (parsed): {target_date_title}")
        print(f"Expected Display Value in Input: {expected_display_value}")

        date_input = page.locator(input_selector)
        await date_input.click()
        picker_panel = page.locator('.ant-picker-panel').first
        await expect(picker_panel).to_be_visible(timeout=10000)

        current_year_btn = picker_panel.locator('.ant-picker-year-btn')
        if await current_year_btn.text_content() != target_year:
            print(f"  Navigating to year {target_year}...")
            await current_year_btn.click()
            year_panel = picker_panel.locator('.ant-picker-year-panel')
            await expect(year_panel).to_be_visible(timeout=5000)
            await year_panel.locator('.ant-picker-cell-inner', has_text=target_year).click()
            await expect(year_panel).to_be_hidden(timeout=5000)
        try:
            current_month_btn = picker_panel.locator('.ant-picker-month-btn')
            if not await current_month_btn.is_visible():
                current_month_btn = picker_panel.locator('.ant-picker-month-panel')
            
            if await current_month_btn.text_content() != target_month_abbr:
                print(f"  Navigating to month {target_month_abbr}...")
                # await current_month_btn.click()
                month_panel = picker_panel.locator('.ant-picker-month-panel')
                await expect(month_panel).to_be_visible(timeout=5000)
                await month_panel.locator('.ant-picker-cell-inner', has_text=target_month_abbr).click()
                await expect(month_panel).to_be_hidden(timeout=5000)
        except Exception as e:
            print(f"Something when wrong when locating '.ant-picker-month-btn' \nNow Trying: '.ant-picker-month-panel'\n Error: {str(e)}")
            current_month_btn = picker_panel.locator('.ant-picker-month-panel')    
            
            if await current_month_btn.text_content() != target_month_abbr:
                print(f"  Navigating to month {target_month_abbr}...")
                await current_month_btn.click()
                month_panel = picker_panel.locator('.ant-picker-month-panel')
                await expect(month_panel).to_be_visible(timeout=5000)
                await month_panel.locator('.ant-picker-cell-inner', has_text=target_month_abbr).click()
                await expect(month_panel).to_be_hidden(timeout=5000)

        print(f"  Selecting day {target_day} (title='{target_date_title}')...")
        day_cell_inner_div = picker_panel.locator(f'td[title="{target_date_title}"] div.ant-picker-cell-inner')
        await day_cell_inner_div.click(timeout=5000)
        print(f"  Clicked day {target_day}.")
        await expect(picker_panel).to_be_hidden(timeout=5000)

        print(f"  Verifying input field displays: '{expected_display_value}'")
        await expect(date_input).to_have_value(expected_display_value, timeout=5000)

        print(f"{field_label} selection verified: input shows '{expected_display_value}'")
        # await page.screenshot(path="after_date_selection.png")

    except Exception as e:
        print(f"Error selecting {field_label} '{target_date_str}': {e}")
        # await page.screenshot(path="date_selection_error.png")
        raise Exception(f"Failed to select {field_label}. Error: {e}") from e
    
async def create_new_organization(page: Page, client_name: str):
    print(f"Client '{client_name}' not found. Creating new organization...")

    await page.click("text=Organisation")
    await page.wait_for_selector("text=Groups", timeout=10000)

    await page.click("button:has-text('New org')")
    await page.wait_for_selector("text=Create New org", timeout=5000)

    await fill_input_by_label_or_placeholder(
        page=page,
        value_to_fill=client_name,
        field_label="Organisation Name",
        label_text="Name"
    )
    await page.click("label:has-text('No')")

    await click_button_by_selector(page, "button:has-text('Save')", "Save Organisation")
    await page.wait_for_timeout(3000)

    print(f"New organisation '{client_name}' created successfully.")

async def fill_quote_form(page: Page, QUOTE_DATA: dict):
    """Fill in all fields in the quote form"""
    try:
        print("Filling quote form...")
        # await page.screenshot(path="before_filling_form.png")
        print("Analyzing form structure...")
        
        try:
            await select_antd_dropdown_option(
                page=page,
                select_input_id="validateOnly_Organization_Name",
                value_to_select=QUOTE_DATA["client_name"],
                field_label="Client Name"
            )
        except Exception as e:
            print(f"Client '{QUOTE_DATA['client_name']}' not found in dropdown. Initiating fallback flow: {e}")
            await create_new_organization(page, QUOTE_DATA["client_name"])
            await navigate_to_new_quote(page, from_exception=True)
            await select_antd_dropdown_option(
                page=page,
                select_input_id="validateOnly_Organization_Name",
                value_to_select=QUOTE_DATA["client_name"],
                field_label="Client Name"
            )
                        
        await fill_date_field(
            input_selector="#validateOnly_insurance_date",
            target_date_str=QUOTE_DATA["policy_start_date"], # 12 jan, 2027
            page=page,
            field_label="Policy Start Date"
        )

        await select_antd_dropdown_option(
            page=page,
            select_input_id="validateOnly_Broker_Name",
            value_to_select=QUOTE_DATA["broker_name"],
            field_label="Broker Name"
        )
        await fill_input_by_label_or_placeholder(
            page=page,
            value_to_fill=QUOTE_DATA["broker_contact_person"],
            field_label="Broker Contact Person",
            placeholder="Enter broker contact person name",
            label_text="Broker Contact Person",
            input_type="input"
        )
        await select_antd_dropdown_option(
            page=page,
            select_input_id="validateOnly_acccount_manager",
            value_to_select=QUOTE_DATA["relationship_manager"],
            field_label="Relationship Manager"
        )
        
        # await page.screenshot(path="3_form_filled_top.png")
                
        # await fill_input_by_label_or_placeholder(
        #     page=page,
        #     value_to_fill=QUOTE_DATA["adjustments_discount"],
        #     field_label="Adjustments Discount",
        #     placeholder="Enter adjustments discount",
        #     label_text="Adjustments Discount",
        #     input_type="input"
        # )
        
        # await fill_input_by_label_or_placeholder(
        #     page=page,
        #     value_to_fill=QUOTE_DATA["discount_comment"],
        #     field_label="Adjustments Discount Comment",
        #     placeholder="Enter additional loading comment",
        #     label_text="Adjustments Discount Comment",
        #     input_type="textarea"
        # )
        
        await fill_input_by_id(
            page=page,
            input_id="validateOnly_brokerage_fee",
            value_to_fill=QUOTE_DATA["brokerage_fees"],
            field_label="Brokerage Fees"
        )

        await fill_input_by_id(
            page=page,
            input_id="validateOnly_HealthX",
            value_to_fill=QUOTE_DATA["healthx"],
            field_label="HealthX"
        )

        await fill_input_by_id(
            page=page,
            input_id="validateOnly_TPA",
            value_to_fill=QUOTE_DATA["tpa"],
            field_label="TPA"
        )

        await fill_input_by_id(
            page=page,
            input_id="validateOnly_Insurer",
            value_to_fill=QUOTE_DATA["insurer"],
            field_label="Insurer"
        )
      
        # await page.screenshot(path="4_form_filled_bottom.png")
        print("Form filled - Screenshots saved")
        return True
        
    except Exception as e:
        print(f"Error filling quote form: {e}")
        # await page.screenshot(path="form_fill_error.png")
        print("Error screenshot saved")
        return False


async def click_button_by_selector(page: Page, selector: str, button_label: str, timeout: int = 10000):
    print(f"Attempting to click '{button_label}' using selector: {selector}")
    try:
        button_locator = page.locator(selector)
        
        print(f"  Waiting for '{button_label}' to be visible...")
        await expect(button_locator).to_be_visible(timeout=timeout)
        print(f"  Waiting for '{button_label}' to be enabled...")
        await expect(button_locator).to_be_enabled(timeout=timeout)

        print(f"  Clicking '{button_label}'...")
        await button_locator.click(timeout=timeout)
        print(f"Successfully clicked '{button_label}'.")

    except Exception as e:
        safe_label = re.sub(r'[^\w\-]+', '_', button_label.lower())
        screenshot_filename = f"error_clicking_{safe_label}.png"
        error_msg = f"Error clicking '{button_label}' with selector '{selector}': {e}"
        print(error_msg)
        # await page.screenshot(path=screenshot_filename)
        print(f"Error screenshot saved as '{screenshot_filename}'")
        raise Exception(error_msg) from e
    
async def upload_census_file(page: Page, census_file_path: str): # Added census_file_path parameter
    """Upload census file to the form"""
    try:
        print("Uploading census file...")
        
        if not os.path.exists(census_file_path):
            print(f"Error: Census file not found at {census_file_path}")
            return False
        
        upload_button = page.locator('button:has-text("Upload Census")').first
        await upload_button.click()
        await page.wait_for_timeout(1000)
        
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(census_file_path)
        
        await page.wait_for_timeout(5000)  
        
        # await page.screenshot(path="5_file_uploaded.png")
        print("Census file uploaded - Screenshot saved")
        return True
        
    except Exception as e:
        print(f"Error uploading census file: {e}")
        # await page.screenshot(path="file_upload_error.png")
        print("Error screenshot saved")
        return False

def add_commas(number): # This function is pure Python, no async needed
    try:
        number_val = int(number) # Convert to int first
        return f"{number_val:,}"
    except ValueError: # Handle cases where number might not be a direct integer string
        try:
            # Attempt to convert float string to int then format
            number_val = int(float(number))
            return f"{number_val:,}"
        except ValueError:
            raise ValueError(f"Invalid number for comma formatting: {number}")




async def fill_benefit_details(page: Page, BENEFIT_DETAILS_DATA_LIST: list):
    """Fills the benefit details table that appears after census confirmation for all categories."""
    print("Starting to fill benefit details table for all categories...")
    try:
        # First approach: Try to detect the form IDs directly, which are more reliable
        category_forms = await page.locator('form[id^="Category-"]').all()
        category_count = len(category_forms)
        
        if category_count == 0:
            # Fallback approach: Look for category headers in h3 elements
            category_headers = await page.locator('.table-title h3:has-text("Category")').all()
            category_count = len(category_headers)
        
        print(f"Detected {category_count} categories to fill")
        
        if category_count == 0:
            print("WARNING: No categories detected. Using fallback method for Category A only.")
            category_ids = ["Category-A"]  # Fallback to just handling Category A
        else:
            # Get category IDs from the form elements or build them from detected headers
            category_ids = []
            for form in category_forms:
                form_id = await form.get_attribute('id')
                if form_id:
                    category_ids.append(form_id)
            
            # If we still don't have category IDs but we found headers, build IDs from headers
            if not category_ids and category_headers:
                for header in category_headers:
                    header_text = await header.text_content()
                    if header_text:
                        category_letter = header_text.strip().split()[-1]
                        category_ids.append(f"Category-{category_letter}")
        
        print(f"Found categories: {category_ids}")
        
        # Validate that we have data for all categories
        if len(BENEFIT_DETAILS_DATA_LIST) < len(category_ids):
            print(f"WARNING: Only {len(BENEFIT_DETAILS_DATA_LIST)} benefit data sets provided for {len(category_ids)} categories.")
            print("Missing categories will use the last available data set.")
        
        # Find the main container that holds all categories - this is what we need to scroll
        options_table_container = page.locator('.options-table').first
        await expect(options_table_container).to_be_visible(timeout=10000)
        print("Found options table container for scrolling")
        
        # Process each category
        for category_idx, category_id in enumerate(category_ids):
            # Extract the letter from the category ID (e.g., "Category-A" -> "A")
            category_letter = category_id.split('-')[-1]
            category_name = f"Category {category_letter}"
            
            # Get the appropriate benefit data for this category
            if category_idx < len(BENEFIT_DETAILS_DATA_LIST):
                current_benefit_data = BENEFIT_DETAILS_DATA_LIST[category_idx]
                print(f"Filling details for {category_name} using data set {category_idx + 1}...")
            else:
                # Use the last available data set if we don't have enough data
                current_benefit_data = BENEFIT_DETAILS_DATA_LIST[-1]
                print(f"Filling details for {category_name} using last available data set (fallback)...")
            
            # For categories after the first one, we need to scroll the container to the right
            if category_idx > 0:
                print(f"Scrolling horizontally to make {category_name} visible...")
                try:
                    # Calculate scroll position - each category card is roughly the same width
                    # We'll scroll incrementally to position each category properly
                    scroll_amount = category_idx * 800  # Adjust this value based on actual category width
                    
                    # Scroll the options table container horizontally
                    await options_table_container.evaluate(f"element => element.scrollLeft = {scroll_amount}")
                    await page.wait_for_timeout(1500)  # Wait for scroll to complete
                    
                    # Verify the target category is now visible
                    target_category_form = page.locator(f'form[id="{category_id}"]')
                    await expect(target_category_form).to_be_visible(timeout=5000)
                    print(f"Successfully scrolled to {category_name}")
                    
                except Exception as e:
                    print(f"Error scrolling to {category_name}: {e}")
                    # Try alternative scrolling method
                    try:
                        # Try to find and scroll to the specific category card
                        category_card = page.locator(f'h3:has-text("{category_name}")').first
                        await category_card.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)
                        print(f"Alternative scroll method used for {category_name}")
                    except Exception as e2:
                        print(f"Alternative scroll also failed for {category_name}: {e2}")
            
            # Fill additional loading field
            additional_loading_id = f"{category_id}_{category_id}-summary-additionalLoading"
            await fill_input_by_id(
                page=page,
                input_id=additional_loading_id,
                value_to_fill=current_benefit_data["additional_loading"]['value'],
                field_label=f"{category_name} Additional Loading"
            )
            
            async def get_all_dropdown_options(page, dropdown_locator) -> list[str]:
                """
                Clicks a dropdown and scrolls through its virtual list to extract all unique option texts.
                """
                all_options = set()
                try:
                    await dropdown_locator.click()
                    
                    # Locate the visible dropdown panel
                    panel_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
                    panel = page.locator(panel_selector).last
                    await expect(panel).to_be_visible()
                    
                    # Locate the scrollable container
                    scroll_container = panel.locator('.rc-virtual-list-holder').first

                    # Ensure the dropdown is at the top,
                    await scroll_container.evaluate("el => el.scrollTop = 0")
                    #    Virtualized lists need a moment to replace the DOM nodes after a scroll.
                    await page.wait_for_timeout(200)
                    
                    # Scroll and scrape until no new options are found
                    last_count = -1
                    for _ in range(30): # Max 30 scrolls to prevent infinite loops
                        visible_options = await panel.locator('div.ant-select-item-option-content').all_inner_texts()
                        all_options.update(visible_options) # .update() adds all items from a list to a set

                        if len(all_options) == last_count:
                            # If the number of options hasn't changed after a scroll, we're at the end.
                            break 
                        
                        last_count = len(all_options)

                        # Scroll down
                        if await scroll_container.is_visible():
                            await scroll_container.evaluate("el => el.scrollBy(0, 250)")
                            await page.wait_for_timeout(150) # Small pause for content to render
                        else:
                            break
    

                finally:
                    # Ensure the dropdown is at the top, even if an error occurs
                    await scroll_container.evaluate("el => el.scrollTop = 0")
                    # 4. (Recommended) Pause briefly to allow the UI to re-render.
                    #    Virtualized lists need a moment to replace the DOM nodes after a scroll.
                    await page.wait_for_timeout(200)
                        
                return list(all_options)
            
            def find_best_match(target_value: str, available_options: list[str]) -> str | None:
                """
                The "AI" logic to find the best option from a list.
                
                Criteria:
                1. Exact match is best.
                2. "Up to [target]" is a perfect match.
                3. Otherwise, find the smallest number that is greater than or equal to the target.
                """
                print(f"🤖 AI searching for target '{target_value}' in options: {available_options}")
                
                try :
                    result = ai_smart_selecting_fun(target_value, available_options)
                    print(f"🤖 Selected Value {result['value']} - reason: {result['reason']} ")
                    return result['value']

                except Exception as e:
                    print("🤖⚠️ Some Error occur in ai_smart_selecting_fun functions")
                    return None


            async def select_smart_dropdown_value(label_text: str, desired_value: str, field_label: str):
                """
                Intelligently selects a dropdown value. It gets all options, asks an 'AI' for
                the best choice, and then selects it.
                """
                print(f"--- Starting smart selection for '{field_label}' ---")
                try:
                    # 1. Locate the dropdown container
                    label_xpath = f"//form[@id='{category_id}']//td[contains(@class, 'custom-table-cell') and normalize-space(.)='{label_text}']"
                    label_td = page.locator(label_xpath).first
                    await expect(label_td).to_be_visible(timeout=10000)
                    
                    dropdown_td = label_td.locator("xpath=following-sibling::td[1]")
                    select_container = dropdown_td.locator("div.ant-select").first
                    
                    # 2. Get all available options using our helper
                    available_options = await get_all_dropdown_options(page, select_container)
                    if not available_options:
                        print(f"  - ⚠️ Could not extract any options for '{field_label}'. Skipping.")
                        return

                    # 3. Ask the "AI" to choose the best option
                    option_to_select = find_best_match(desired_value, available_options)

                    # 4. Act on the AI's decision
                    if option_to_select:
                        print(f"  -> AI decision: Select '{option_to_select}'")
                        # Now perform the selection
                        await select_container.click()
                        panel_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
                        panel = page.locator(panel_selector).last
                        
                        # select_dropdown_in_current_category(label_text, option_to_select, field_label)
                        
                        # Use exact text match for clicking the chosen option
                        final_option_locator = panel.locator('div.ant-select-item-option-content', has_text=re.compile(f"^{re.escape(option_to_select)}$"))
                        await final_option_locator.scroll_into_view_if_needed() # Simpler than manual scroll
                        await final_option_locator.click()

                        # 5. Robust Verification
                        selected_item = select_container.locator('.ant-select-selection-item')
                        await expect(selected_item).to_contain_text(desired_value, timeout=5000)
                        print(f"  ✅ '{field_label}' selection of '{option_to_select}' verified successfully.")
                    else:
                        print(f"  - ⚠️ AI could not find a suitable match for '{desired_value}'. Skipping field.")

                except Exception as e:
                    print(f"  ❌ An error occurred during the smart selection for '{field_label}': {e}")
                    # Decide if you want to raise e to stop the test, or just continue
            
            # Helper function to select dropdown within current category
            async def select_dropdown_in_current_category(label_text: str, value_to_select: str, field_label: str):
                print(f"Selecting {field_label} ('{value_to_select}') within {category_name} context (case-insensitive, space-agnostic)")
                try:
                    # Find the label within the current category's table
                    label_xpath = f"//form[@id='{category_id}']//td[contains(@class, 'custom-table-cell') and normalize-space(.)='{label_text}']"
                    label_td = page.locator(label_xpath).first
                    await expect(label_td).to_be_visible(timeout=10000)
                    
                    # Find the corresponding dropdown within the same row
                    dropdown_td = label_td.locator("xpath=following-sibling::td[contains(@class, 'custom-table-cell')][1]")
                    await expect(dropdown_td).to_be_visible(timeout=5000)
                    
                    # Find select container within this specific cell
                    select_container = dropdown_td.locator("div.ant-select").first
                    await expect(select_container).to_be_visible(timeout=5000)
                    
                    # Click to open dropdown
                    await select_container.click()
                    
                    # Wait for dropdown panel
                    visible_dropdown_selector = ".ant-select-dropdown:not([style*='display: none']):not(.ant-select-dropdown-hidden)"
                    dropdown_panel_locator = page.locator(visible_dropdown_selector).last
                    await expect(dropdown_panel_locator).to_be_visible(timeout=10000)
                    
                    # Search for the option using the space-insensitive pattern
                    pattern = _create_space_insensitive_pattern(value_to_select)
                    option_found = False
                    option_locator = None # Define option_locator here
                    
                    for scroll_attempt in range(30):
                        print(f"  Scroll attempt {scroll_attempt + 1} for {field_label}")
                        try:
                            option_locator = dropdown_panel_locator.locator('div.ant-select-item-option', has_text=pattern).first
                            if await option_locator.is_visible(timeout=1000):
                                option_found = True
                                print(f"  Found option for {field_label}")
                                break
                        except:
                            pass
                        
                        # Scroll within dropdown
                        try:
                            scroll_container = dropdown_panel_locator.locator('.rc-virtual-list-holder')
                            scroll_handle = await scroll_container.element_handle(timeout=2000)
                            if scroll_handle:
                                await page.evaluate("(el) => el.scrollBy(0, 100)", scroll_handle)
                                await scroll_handle.dispose()
                            await page.wait_for_timeout(200)
                        except:
                            break
                    
                    if not option_found or not option_locator: # Check option_locator
                        raise Exception(f"Option '{value_to_select}' not found for {field_label}")
                    
                    # Click the option
                    await option_locator.click()
                    
                    # Wait for dropdown to close
                    await expect(dropdown_panel_locator).to_be_hidden(timeout=5000)
                    
                    # Verify selection
                    selected_item = select_container.locator('.ant-select-selection-item')
                    await expect(selected_item).to_have_text(pattern, timeout=5000)
                    print(f"  {field_label} selection verified")
                    
                except Exception as e:
                    print(f"Error selecting {field_label}: {e}")
                    raise
            
            # Helper function to safely try to select a field that might not exist
            async def try_select_conditional_field(label_text: str, value_to_select: str, field_label: str):
                try:
                    # First check if the field exists and is visible
                    label_xpath = f"//form[@id='{category_id}']//td[contains(@class, 'custom-table-cell') and normalize-space(.)='{label_text}']"
                    label_td = page.locator(label_xpath).first
                    
                    if await label_td.is_visible(timeout=3000):
                        await select_dropdown_in_current_category(label_text, value_to_select, field_label)
                    else:
                        print(f"  {field_label} field not visible - likely hidden due to conditional logic")
                except Exception as e:
                    print(f"  {field_label} field not accessible \n- Try Using AI 🤖 - \nlikely hidden due to conditional logic: {e}")
                    await select_smart_dropdown_value(label_text, value_to_select, field_label)

            
            # Now fill all the dropdown fields using the scoped selection function and current category's data
            await try_select_conditional_field("NAS Network:", current_benefit_data["nas_network"]['value'], f"{category_name} NAS Network")
            
            print(f"Skipping 'Plan' dropdown for {category_name} as it appears disabled.")
            
            await try_select_conditional_field("Annual Medical:", current_benefit_data["annual_medical"]['value'], f"{category_name} Annual Medical")
            await try_select_conditional_field("IP Room Type:", current_benefit_data["ip_room_type"]['value'], f"{category_name} IP Room Type")
            await try_select_conditional_field("Copayment on all IP and Day-Case Benefits subject to cap of 500 AED per encounter:", current_benefit_data["copayment_ip_daycase"]['value'], f"{category_name} Copayment IP/Day-Case")
            await try_select_conditional_field("Deductible for Consultation:", current_benefit_data["deductible_consultation"]['value'], f"{category_name} Deductible for Consultation")
            await try_select_conditional_field("Territorial cover:", current_benefit_data["territorial_cover"]['value'], f"{category_name} Territorial Cover")
            await try_select_conditional_field("Diagnostic Investigation OP Copay:", current_benefit_data["diagnostic_op_copay"]['value'], f"{category_name} Diagnostic Investigation OP Copay")
            await try_select_conditional_field("Pharmacy Copay:", current_benefit_data["pharmacy_copay"]['value'], f"{category_name} Pharmacy Copay")
            await try_select_conditional_field("Pharmacy Limit:", current_benefit_data["pharmacy_limit"]['value'], f"{category_name} Pharmacy Limit")
            await try_select_conditional_field("Medication Type:", current_benefit_data["medication_type"]['value'], f"{category_name} Medication Type")
            await try_select_conditional_field("PEC:", current_benefit_data["pec"]['value'], f"{category_name} PEC")
            
            # Handle maternity limit with comma formatting fallback
            try:
                await try_select_conditional_field("Maternity Limit:", current_benefit_data["maternity_limit"]['value'], f"{category_name} Maternity Limit")
            except:
                comma_number = add_commas(current_benefit_data["maternity_limit"]['value'])
                await try_select_conditional_field("Maternity Limit:", comma_number, f"{category_name} Maternity Limit")
            
            await try_select_conditional_field("Maternity Copay:", current_benefit_data["maternity_copay"]['value'], f"{category_name} Maternity Copay")
            
            # Handle dental limit with comma formatting fallback
            try:
                await try_select_conditional_field("Dental Limit:", current_benefit_data["dental_limit"]['value'], f"{category_name} Dental Limit")
            except:
                comma_number = add_commas(current_benefit_data["dental_limit"]['value'])
                await try_select_conditional_field("Dental Limit:", comma_number, f"{category_name} Dental Limit")
            
            await try_select_conditional_field("Dental Copay:", current_benefit_data["dental_copay"]['value'], f"{category_name} Dental Copay")
            await try_select_conditional_field("Optical Limit:", current_benefit_data["optical_limit"]['value'], f"{category_name} Optical Limit")
            await try_select_conditional_field("Optical Copay:", current_benefit_data["optical_copay"]['value'], f"{category_name} Optical Copay")
            await try_select_conditional_field("Repatriation of Mortal Remains to the Country of Domicile:", current_benefit_data["repatriation"]['value'], f"{category_name} Repatriation Limit")
            
            # Handle conditional fields that might be hidden when their parent is "Not Covered"
            await try_select_conditional_field("Nursing at home by a registered nurse (following an immediate Inpatient treatment):", current_benefit_data["nursing_at_home"]['value'], f"{category_name} Nursing at Home Limit")
            
            # OP Psychiatric fields - these are conditional
            await try_select_conditional_field("OP Psychiatric Benefits Limit:", current_benefit_data["op_psychiatric_limit"]['value'], f"{category_name} OP Psychiatric Limit")
            # Add a small delay to allow for UI updates after selecting the limit
            await page.wait_for_timeout(500)
            await try_select_conditional_field("OP Psychiatric Benefits copay:", current_benefit_data["op_psychiatric_copay"]['value'], f"{category_name} OP Psychiatric Copay")
            
            # Alternative Medicine fields - these are also conditional
            await try_select_conditional_field("Alternative Medicine Limit:", current_benefit_data["alternative_medicine_limit"]['value'], f"{category_name} Alternative Medicine Limit")
            await page.wait_for_timeout(500)
            await try_select_conditional_field("Alternative Medicine copay:", current_benefit_data["alternative_medicine_copay"]['value'], f"{category_name} Alternative Medicine Copay")
            
            # Handle routine health checkup with comma formatting fallback
            try:
                await try_select_conditional_field("Routine Health Check-up:", current_benefit_data["routine_health_checkup"]['value'], f"{category_name} Routine Health Check-up")
            except:
                comma_number = add_commas(current_benefit_data["routine_health_checkup"]['value'])
                await try_select_conditional_field("Routine Health Check-up:", comma_number, f"{category_name} Routine Health Check-up")
            
            # Physiotherapy fields
            await try_select_conditional_field("Physiotherapy Limit:", current_benefit_data["physiotherapy_limit"]['value'], f"{category_name} Physiotherapy Limit")
            await page.wait_for_timeout(500)
            await try_select_conditional_field("Physiotherapy copay:", current_benefit_data["physiotherapy_copay"]['value'], f"{category_name} Physiotherapy Copay")
            
            print(f"Completed filling details for {category_name}")
        
        print("All benefit details for all categories filled successfully.")
        return True
            
    except Exception as e:
        print(f"Error filling benefit details table: {e}")
        raise Exception(f"Failed to fill benefit details. Error: {e}") from e

async def get_page_css(page: Page) -> str:
    """
    Extracts linked and inline CSS from the page.
    Handles potential errors during fetching linked CSS.
    """
    print("    Extracting CSS links...")
    css_links = await page.eval_on_selector_all(
        'link[rel="stylesheet"]',
        '''(links) =>
            links.map((link) => link.href)'''
    )

    print("    Extracting inline CSS styles...")
    inline_styles = await page.eval_on_selector_all(
        'style',
        '''(styles) =>
            styles.map((style) => style.textContent || '')'''
    )

    embedded_css = ""

    for style_content in inline_styles:
        embedded_css += f"<style>\n{style_content}\n</style>\n"
    print(f"    Found {len(inline_styles)} inline <style> blocks.")

    print(f"    Fetching content from {len(css_links)} linked stylesheets...")
    fetched_css_count = 0
    for i, href in enumerate(css_links):
        if not href:
            print(f"      Skipping empty link href (index {i}).")
            continue
        print(f"      Fetching: {href[:100]}{'...' if len(href)>100 else ''}")
        try:
            response = await page.request.get(href) # APIRequestContext.get() is async
            if response.ok:
                css_content = await response.text() # APIResponse.text() is async
                if css_content and ('{' in css_content or '}' in css_content):
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


async def generate_tob_preview_pdf(page: Page, context: BrowserContext, output_dir: str = ".", filename_prefix: str = "tob_preview"):
    """
    Clicks 'Preview', extracts HTML & CSS, saves HTML, generates PDF.
    """
    print("Generating TOB Preview PDF and HTML...")
    pdf_page = None
    # html_save_path = None # Not used for returning
    pdf_save_path = None

    try:
        print("  Locating and clicking 'Preview' button...")
        preview_button_selector = 'button:has-text("Preview")'
        preview_button = page.locator(preview_button_selector).first
        await expect(preview_button).to_be_visible(timeout=10000)
        await expect(preview_button).to_be_enabled(timeout=10000)
        await preview_button.click()
        print("  'Preview' button clicked.")

        print("  Waiting for TOB Preview slider/drawer to appear...")
        slider_content_selector = ".ant-drawer.ant-drawer-open .ant-drawer-content-wrapper"
        slider_content_element = page.locator(slider_content_selector).first
        await expect(slider_content_element).to_be_visible(timeout=15000)
        await expect(page.locator(f"{slider_content_selector} :text('TOB Preview')")).to_be_visible(timeout=5000)
        print("  TOB Preview slider is visible.")
        await page.wait_for_timeout(1500)

        print("  Extracting HTML content from the slider...")
        slider_html_raw = await slider_content_element.evaluate("element => element.outerHTML")
        if not slider_html_raw:
            raise Exception("Failed to extract HTML from the slider content element.")
        print(f"  Extracted raw HTML (length: {len(slider_html_raw)} characters).")

        print("  Extracting CSS from main page...")
        page_css = await get_page_css(page)

        print("  Combining extracted CSS and HTML for PDF generation...")
        full_html_for_pdf = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TOB Preview</title>
            {page_css}
            <style>
               body {{ margin: 0; padding: 0; background-color: #ffffff; }}
               .ant-drawer-content-wrapper {{
                   position: relative !important;
                   width: 100% !important;
                   max-width: 1000px; 
                   margin: 0 auto; 
                   box-shadow: none !important;
               }}
               .ant-drawer-close {{ display: none !important; }}
               .pagebreak {{ page-break-before: always; }}
            </style>
        </head>
        <body>
            {slider_html_raw}
        </body>
        </html>
        """

        # print("  Saving combined HTML (with CSS) to file...")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prefix = re.sub(r'[^\w\-]+', '_', filename_prefix)
        # html_filename = f"{safe_prefix}_with_css_{timestamp}.html"
        # html_save_path = os.path.join(output_dir, html_filename)
        # try:
        #     with open(html_save_path, "w", encoding="utf-8") as f:
        #         f.write(full_html_for_pdf)
        #     print(f"    Combined HTML saved successfully: {html_save_path}")
        # except Exception as html_write_err:
        #     print(f"    Error saving combined HTML file: {html_write_err}")
        #     html_save_path = None # Ensure it's None if saving failed

        print("  Preparing to generate PDF in isolation...")
        pdf_page = await context.new_page() # Use await
        print("    Setting combined content in temporary page...")
        await pdf_page.set_content(full_html_for_pdf, wait_until='networkidle') # Use await
        print("    Content set. Generating PDF...")

        pdf_filename = f"{safe_prefix}_{timestamp}.pdf"
        pdf_save_path = os.path.join(output_dir, pdf_filename)

        await pdf_page.pdf( # Use await
            path=pdf_save_path,
            print_background=True,
            format='A4',
            margin={'top': '20px', 'bottom': '20px', 'left': '20px', 'right': '20px'},
        )
        print(f"    PDF generated successfully: {pdf_save_path}")

        await pdf_page.close() # Use await
        print("  Temporary PDF generation page closed.")

        try:
             close_button_selector = ".ant-drawer.ant-drawer-open .ant-drawer-close"
             close_button = page.locator(close_button_selector)
             if await close_button.is_visible(timeout=1000): # Use await
                print("  Closing the TOB Preview slider on the main page...")
                await close_button.click() # Use await
                await expect(slider_content_element).to_be_hidden(timeout=5000) # Use await
                print("  Slider closed.")
             else:
                 print("  Could not find standard close button, slider might remain open.")
        except Exception as close_err:
             print(f"  Warning: Could not automatically close the slider: {close_err}")

        print(f"TOB Preview PDF and HTML generation complete.")
        return pdf_save_path # Return pdf_save_path, html_save_path

    except Exception as e:
        print(f"Error during TOB Preview generation: {e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_screenshot_path = os.path.join(output_dir, f"error_{filename_prefix}_{timestamp}.png")
        try:
            # await page.screenshot(path=error_screenshot_path) # Use await
            print(f"Error screenshot saved to {error_screenshot_path}")
        except Exception as screen_err:
            print(f"Could not take error screenshot: {screen_err}")
        
        # Return what we have, pdf_save_path might be None or set
        return pdf_save_path if pdf_save_path else None


    finally:
        if pdf_page and not pdf_page.is_closed():
            try:
                await pdf_page.close() # Use await
                print("  Ensured temporary PDF page is closed.")
            except Exception as close_err:
                print(f"  Error closing lingering temporary page: {close_err}")

async def save_quote_and_download_pdf(page: Page, context: BrowserContext, timeout: int = 60000): # timeout not used
    print("Attempting to finalize quote and save PDF...")

    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Timestamp handled in generate_tob_preview_pdf
    # pdf_filename = f"quote_summary_{timestamp}.pdf"
    # pdf_save_path = os.path.join(os.getcwd(), pdf_filename)
    # print(f"  PDF will be saved as: {pdf_save_path}") # Path handled in generate_tob_preview_pdf

    try:
        pdf_path = await generate_tob_preview_pdf(page, context) # Call the async version
        if pdf_path:
            print(f"  PDF generation successful. Path: {pdf_path}")
            return True # Indicating success of the operation if PDF path is returned
        else:
            print("  PDF generation failed (no path returned).")
            return False   
    except Exception as e:
        print(f"Error during final save and PDF download: {e}")
        # await page.screenshot(path="error_saving_quote_pdf.png")
        raise Exception(f"Failed to save quote and download PDF. Error: {e}") from e

def move_and_rename_file(source_path: str, dest_folder: str): 
    """
    Moves a file to a destination folder, handling long path issues and
    automatically renaming to avoid overwriting existing files.

    Args:
        source_path (str): The full, original path of the file to move.
        dest_folder (str): The target folder to move the file into.

    Returns: 
        str: The final, full path of the moved file on success.
        None: If the operation fails for any reason (e.g., file not found).
    """
    # 1. Check if the source file actually exists before doing anything
    if not os.path.exists(source_path):
        print(f"\n❌ ERROR: The source file was not found at '{source_path}'.")
        return None

    # 2. Create the destination folder if it doesn't exist
    try:
        os.makedirs(dest_folder, exist_ok=True)
        print(f"Directory '{dest_folder}' is ready.")
    except OSError as e:
        print(f"\n❌ ERROR: Could not create directory '{dest_folder}': {e}")
        return None

    # 3. Determine the final destination path, handling potential name conflicts
    filename = os.path.basename(source_path)
    destination_path = os.path.join(dest_folder, filename)
    
    # If a file with the same name exists, find a new name
    counter = 1
    original_destination_path = destination_path # Keep track of the original target
    while os.path.exists(destination_path):
        file_basename, file_extension = os.path.splitext(filename)
        new_filename = f"{file_basename} ({counter}){file_extension}"
        destination_path = os.path.join(dest_folder, new_filename)
        counter += 1

    # 4. Move the file to the final, unique destination path
    try:
        print(f"\nMoving file from: {source_path}")
        print(f"             to: {destination_path}")
        
        shutil.copy2(source_path, destination_path)
        
        # Give a clear confirmation message if a rename occurred
        if destination_path != original_destination_path:
            print(f"\nNote: A file named '{os.path.basename(original_destination_path)}' already existed.")
            print(f"The file was automatically renamed to '{os.path.basename(destination_path)}'.")

        print(f"\n✅ Success! File move complete.")
        
        # On success, return the new path
        return destination_path

    except Exception as e:
        print(f"\n❌ ERROR: An unexpected error occurred during the move: {e}")
        # On failure, return None
        return None


async def generate_quote_automation(QUOTE_DATA: dict, BENEFIT_DETAILS_DATA_LIST: list, CENSUS_FILE_PATH: str):
    bb, session = None, None
    pdf_path = None
    
    CENSUS_FILE_PATH = move_and_rename_file(CENSUS_FILE_PATH, settings.DESTINATION_PATH)
    
    try:
        bb, session = setup_browser()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
            page.set_default_timeout(60000)
            
            if await login(page):
                await page.wait_for_timeout(2000)
                if await navigate_to_new_quote(page):
                    await page.wait_for_timeout(2000)
                    if await fill_quote_form(page, QUOTE_DATA):
                        await page.wait_for_timeout(1000)
                        if await upload_census_file(page, CENSUS_FILE_PATH):
                            print("Census file uploaded, proceeding...")
                            mapping_modal_selector = '.ant-modal-wrap:not([style*="display: none"]) .ant-modal-content:has-text("mapped CSV data")'
                            ok_button_in_mapping_modal_selector = f"{mapping_modal_selector} .ant-modal-footer button:has-text('OK')"
                            print(f"Waiting for Mapping Confirmation modal ({mapping_modal_selector}) to be visible...")
                            await expect(page.locator(mapping_modal_selector)).to_be_visible(timeout=15000)
                            print(f"Clicking OK button in Mapping modal using selector: {ok_button_in_mapping_modal_selector}")
                            await click_button_by_selector(page, ok_button_in_mapping_modal_selector, "Mapping Confirmation OK", 15000)
                            print("Mapping confirmed.")
                            
                            print("Waiting for Mapping modal to close...")
                            await expect(page.locator(mapping_modal_selector)).to_be_hidden(timeout=10000)
                            print("Waiting for 'Census list' modal to appear...")
                            census_list_modal_header_selector = '.ant-modal-header:has-text("Census list")'
                            census_list_modal_content_selector = '.ant-modal-wrap:not([style*="display: none"]) .ant-modal-content'
                            visible_census_list_modal_selector = f"{census_list_modal_content_selector}:has({census_list_modal_header_selector})"
                            await expect(page.locator(visible_census_list_modal_selector)).to_be_visible(timeout=20000)
                            print("'Census list' modal is visible.")
                            
                            print("Attempting to click OK on the 'Census list' modal...")
                            ok_button_in_census_modal_selector = f"{visible_census_list_modal_selector} .ant-modal-footer button:has-text('OK')"
                            print(f"Using specific selector for Census List OK: {ok_button_in_census_modal_selector}")
                            await click_button_by_selector(page, ok_button_in_census_modal_selector, "Census List Confirmation OK", 15000)
                            print("Clicked OK on 'Census list' modal.")
                            print("Waiting for 'Census list' modal to close...")
                            await expect(page.locator(visible_census_list_modal_selector)).to_be_hidden(timeout=10000)
                            print("'Census list' modal closed.")
                            
                            print("Waiting 6 seconds before filling benefit details...")
                            await page.wait_for_timeout(12000)
                            if await fill_benefit_details(page, BENEFIT_DETAILS_DATA_LIST):  # Pass the list
                                print("Benefit details successfully filled.")
                                print("Waiting slightly before final save...")
                                await page.wait_for_timeout(2000)
                                pdf_path = await generate_tob_preview_pdf(page, context)
                                if pdf_path:
                                    print(f"Quote preview PDF generated successfully! Path: {pdf_path}")
                                else:
                                    print("Failed to generate the PDF preview.")
                                    return {
                                        "success": False,
                                        "pdf_path": None,
                                        "message": "Failed to generate PDF preview"
                                    }
                            else:
                                print("Benefit details filling failed.")
                                return {
                                    "success": False,
                                    "pdf_path": None,
                                    "message": "Failed to fill benefit details"
                                }
                            print("Process steps completed successfully!")
                            
                            return {
                                "success": True,
                                "pdf_path": pdf_path,
                                "message": "Process completed successfully"
                            }
            print("Closing browser resources...")
            await context.close()
            await browser.close()
            
            # The core command to remove a file
            os.remove(CENSUS_FILE_PATH)
            print(f"✅ Successfully deleted file.")
            
            return {
                "success": False,
                "pdf_path": pdf_path,
                "message": "Process did not complete all steps"
            }
    except Exception as e:
        print(f"AN ERROR OCCURRED DURING EXECUTION: {e}")
        if 'page' in locals() and page and not page.is_closed():
            try:
                # await page.screenshot(path="final_error_screenshot.png") # Screenshotting in Browserbase context needs care
                print("Final error screenshot would be saved as 'final_error_screenshot.png' (currently commented out)")
            except Exception as screen_err:
                print(f"Could not take final error screenshot: {screen_err}")
        
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


class BrowserManager:
    """Manages browser automation operations."""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self):
        """Initialize browser instance."""
        # Browser initialization is handled within generate_quote_automation
        pass
    
    async def cleanup(self):
        """Clean up browser resources."""
        # Cleanup is handled within generate_quote_automation
        pass
    
     
    
    async def generate_quote(self, quote_data: Dict[str, Any], 
                           tob_data_list: List[Dict[str, Any]], 
                           excel_file_path: str) -> Dict[str, Any]:
        """
        Generate quote using browser automation.
        
        This method contains the full logic from multi_category_browser_base.py
        """
        
        
        return await generate_quote_automation(quote_data, tob_data_list, excel_file_path)


# Global browser manager instance
browser_manager = BrowserManager()

if __name__ == '__main__':
    QUOTE_DATA_EXAMPLE = {
        "client_name": "ALACRITY CARGO CLEARING & SHIPPING L.L.C (BRANCH)",
        "policy_start_date": "2026-12-12",
        "broker_name": "Wellx.ai",
        "broker_contact_person": "omar",
        "relationship_manager": "Sabina",
        "adjustments_discount": "0",
        "brokerage_fees": "12.50",
        "healthx": "7.50",
        "tpa": "5",
        "insurer": "5"
    }
    
    # Now BENEFIT_DETAILS_DATA is a list of dictionaries - one for each category
    # from multi_category_lists import BENEFIT_DETAILS_DATA_LIST_EXAMPLE
    BENEFIT_DETAILS_DATA_LIST_EXAMPLE = [
        {
            "category_name": {
                "value": "Category-01 PRIVILEGE",
                "changed": False,
                "explanation": "Found exact match 'Category-01 PRIVILEGE' for category identifier based on TOB headings 'Category-01 [UAE/Dubai] Members' and 'OFFERING | Category-01 PRIVILEGE'."
            },
            "policy_start_date": {
                "value": "2024-09-01",
                "changed": False,
                "explanation": "Found 'Policy Effective Date: 01/09/2024' in the TOB, converted to '2024-09-01' for policy start date."
            },
            "additional_loading": {
                "value": "0",
                "changed": False,
                "explanation": "No specific value found for additional loading, using default '0'."
            },
            "nas_network": {
                "value": "RN",
                "changed": False,
                "explanation": "Identified 'Network - Inpatient | A.1' and 'Network - Outpatient | A.1' in the TOB. Since 'A.1' is not among the allowed options ['RN', 'Rn 3.8', 'Dubai GN+', 'Dubai SRN'], using default 'RN'."
            },
            "annual_medical": {
                "value": "AED 1,500,000",
                "changed": True,
                "explanation": "You requested for 'AED 5,000,000' for annual medical limit but we have selected '1500000' which is the highest available option from ['150000', '200000', '250000', '300000', '500000', '750000', '1000000', '1500000'] and aligns more closely with our business rules."
            },
            "ip_room_type": {
                "value": "Private",
                "changed": False,
                "explanation": "Identified 'Daily Room and Board | Standard Private Room' as referring to inpatient room type, selected 'Private' from allowed options ['Private', 'Semi-Private', 'Shared']."
            },
            "copayment_ip_daycase": {
                "value": "0%",
                "changed": False,
                "explanation": "No explicit inpatient/daycase copayment found in TOB. 'Within the Network | Direct billing within network' and 'Covered' status for most inpatient services imply no copayment. Using default '0%' which aligns with this interpretation from allowed options ['0%', '5%', '10%', '15%', '20%']."
            },
            "deductible_consultation": {
                "value": "20% up to AED 50",
                "changed": False,
                "explanation": "Found 'All Consultations Deductible/coinsurance | 20% Max AED 50' in TOB, which exactly matches the allowed option '20% up to AED 50'."
            },
            "territorial_cover": {
                "value": "UAE only",
                "changed": True,
                "explanation": "You requested for 'World wide excluding US' for territorial cover. As the provided schema comment only specifies 'UAE only' as a default and does not list other allowed options, we have selected 'UAE only'. This selection aligns with the constraints of the available options in the provided template."
            },
            "diagnostic_op_copay": {
                "value": "0%",
                "changed": False,
                "explanation": "Identified 'Diagnostics' (Imaging, Laboratory) under Outpatient Treatment listed as 'Covered'. This implies no copayment for outpatient diagnostics. Selected '0%' from allowed options ['0%','5%','10%','15%','20%', '10','20','25','30','50','75', '100']."
            },
            "pharmacy_copay": {
                "value": "0 %",
                "changed": False,
                "explanation": "Identified 'Prescribed drugs/medications | Nil' and related 'Coinsurance/Deductible | Nil' under Outpatient Treatment as referring to pharmacy copayment. 'Nil' maps to '0 %', which is an allowed option."
            },
            "pharmacy_limit": {
                "value": "Upto AML",
                "changed": False,
                "explanation": "Identified 'Prescribed medications limit | Covered' under Outpatient Treatment as referring to pharmacy limit. 'Covered' semantically maps to 'Upto AML', which is an allowed option."
            },
            "medication_type": {
                "value": "Branded",
                "changed": False,
                "explanation": "No specific value found in the TOB for medication type (Generic/Branded), using default 'Branded'."
            },
            "pec": {
                "value": "Upto AML",
                "changed": False,
                "explanation": "Identified 'Pre-existing and Chronic conditions (Inpatient and Outpatient) | Covered' as referring to pre-existing conditions limit. 'Covered' semantically maps to 'Upto AML', which is an allowed option."
            },
            "maternity_limit": {
                "value": "40000",
                "changed": True,
                "explanation": "You requested for 'AED 36,700' for maternity limit but we have selected '40000' which is the next highest available option from ['Not Covered', 'Up to AML', '7500', '10000', '15000', '20000', '25000', '30000', '40000', '50000'] and aligns more closely with our business rules."
            },
            "maternity_copay": {
                "value": "0% copayment. Routine Benefits",
                "changed": False,
                "explanation": "Identified 'Maternity Benefit: ... Deductible/ Coinsurance on Outpatient Consultations | NIL' in TOB. 'NIL' maps to '0% copayment. Routine Benefits', which is an allowed option."
            },
            "dental_limit": {
                "value": "5000",
                "changed": True,
                "explanation": "You requested for 'AED 3,670' (found under 'Routine Dental Benefit | Consultation') for dental limit but we have selected '5000' which is the next highest available option from ['Not Covered', '500', '1000','2000','2500','3000', '3500', '5000', '7500', '10000'] and aligns more closely with our business rules."
            },
            "dental_copay": {
                "value": "10% copayment. Routine Benefits",
                "changed": True,
                "explanation": "You requested for '0%' for routine dental copayment (from 'Coinsurance on ALL Routine Dental treatment... | 0%'). Since '0%' is not an allowed option from ['10% copayment. Routine Benefits', '20% copayment. Routine Benefits', '30% copayment. Routine Benefits'], we have selected '10% copayment. Routine Benefits' as the closest available option, aligning with our business rules."
            },
            "optical_limit": {
                "value": "2500",
                "changed": True,
                "explanation": "You requested for 'AED 2,750' for optical limit but we have selected '2500' which is the closest (and highest) available option from ['Not Covered', '300', '500', '750','1000', '1500', '2000', '2500'] and aligns more closely with our business rules."
            },
            "optical_copay": {
                "value": "10% copayment. Routine Benefits",
                "changed": True,
                "explanation": "You requested for 'Nil' (0%) for optical copayment (from 'Optical Benefit | Coinsurance | Nil'). Since '0% copayment. Routine Benefits' is explicitly not an allowed option for this field as per template comments, and allowed options are ['10% copayment. Routine Benefits', '20% copayment. Routine Benefits','30% copayment. Routine Benefits'], we have selected '10% copayment. Routine Benefits' as the closest available option."
            },
            "repatriation": {
                "value": "5,000",
                "changed": False,
                "explanation": "Identified 'International Emergency Medical Assistance (IEMA) ... Repatriation of mortal remains | Covered'. As a specific monetary value from the allowed options ['5000', '7500', '10000', '20000', '25000', '30000'] is not provided for 'Covered', using default '5000'."
            },
            "nursing_at_home": {
                "value": "Not Covered",
                "changed": False,
                "explanation": "The TOB states 'Nursing at home ... | Covered'. However, 'Covered' is not a specific monetary limit from the allowed options ['Not Covered', '1000', ..., '24000'], and 'Upto AML' is not an option for this field. Since no directly mappable specific value from the allowed list was found, the default 'Not Covered' is used. The 'changed' flag is False as default is used due to unmappable TOB entry."
            },
            "op_psychiatric_limit": {
                "value": "10,000",
                "changed": True,
                "explanation": "You requested for 'AED 9,200' (from 'Psychiatric Treatment ... Out Patient: AED 9,200') for outpatient psychiatric limit but we have selected '10000' which is the next highest available option from ['Not Covered', '800', ..., '10000', '15000'] and aligns more closely with our business rules."
            },
            "op_psychiatric_copay": {
                "value": "20% of Co-Pay",
                "changed": True,
                "explanation": "No specific copay mentioned for outpatient psychiatric treatment. Identified general outpatient 'All Consultations Deductible/coinsurance | 20% Max AED 50' as applicable. This semantically maps to '20% of Co-Pay' from allowed options ['0% of Co-Pay', '10% of Co-Pay', '20% of Co-Pay','30% of Co-Pay']."
            },
            "alternative_medicine_limit": {
                "value": "10,000",
                "changed": False,
                "explanation": "Found exact match 'AED 10,000' for alternative medicine limit in TOB, selected '10000' from allowed options."
            },
            "alternative_medicine_copay": {
                "value": "20% of Co-Pay",
                "changed": True,
                "explanation": "No specific copay mentioned for alternative medicine. Identified general outpatient 'All Consultations Deductible/coinsurance | 20% Max AED 50' as applicable. This semantically maps to '20% of Co-Pay' from allowed options ['0% of Co-Pay', '10% of Co-Pay', '20% of Co-Pay', '30% of Co-Pay']."
            },
            "routine_health_checkup": {
                "value": "3,000",
                "changed": True,
                "explanation": "You requested for 'AED 3,670' (from 'Screening / Health Check-up (Routine) | AED 3,670') for routine health checkup limit but we have selected '3000' which is the closest (and highest) available option from ['Not Covered', '1000', '1500', '2000', '2500', '3000'] and aligns more closely with our business rules."
            },
            "physiotherapy_limit": {
                "value": "Up to AML",
                "changed": False,
                "explanation": "Identified 'Physiotherapy ... | Covered' (for both Inpatient and Outpatient) as referring to physiotherapy limit. 'Covered' semantically maps to 'Up to AML', which is an allowed option."
            },
            "physiotherapy_copay": {
                "value": "20% of Co-Pay",
                "changed": True,
                "explanation": "No specific copay mentioned for physiotherapy. Identified general outpatient 'All Consultations Deductible/coinsurance | 20% Max AED 50' as applicable. This semantically maps to '20% of Co-Pay' from allowed options ['0% of Co-Pay', '10% of Co-Pay', '20% of Co-Pay']."
            }
        }
    ]
    
    
    CENSUS_FILE_PATH_EXAMPLE = "attachments/email_AAMkAGFiZDdkNzU5LTI2MWQtNDBmZi1iNWRjLTJhY2MyNjgzMWFjYgBGAAAAAABXWzGuoy-RT6PmBgUBSnIJBwD16mRpZTY_TZVyykE1CSttAAAAAAEMAAD16mRpZTY_TZVyykE1CSttAAAcJ2cjAAA=_20250625_193842_978658_c922dffa/MemberCensusDataTemplate.xls"
    
    # CENSUS_FILE_PATH_EXAMPLE = os.path.abspath(CENSUS_FILE_PATH_EXAMPLE)  # Ensure the path is absolute

    async def run_main():
        result = await browser_manager.generate_quote(QUOTE_DATA_EXAMPLE, BENEFIT_DETAILS_DATA_LIST_EXAMPLE, CENSUS_FILE_PATH_EXAMPLE)
        print(f"Main function completed with result: {result}")
    
    asyncio.run(run_main())