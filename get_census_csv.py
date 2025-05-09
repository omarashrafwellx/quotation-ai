import pandas as pd
import os
import datetime
import re
import numpy as np

def find_columns(df, column_patterns):
    found_columns = {}
    
    for col_type, pattern in column_patterns.items():
        found_column = None
        
        # If pattern is a list (keywords), search for any match
        if isinstance(pattern, list):
            for column in df.columns:
                if isinstance(column, str):
                    column_lower = column.lower()
                    if any(keyword in column_lower for keyword in pattern):
                        found_column = column
                        break
        # If pattern is a regex pattern
        elif isinstance(pattern, re.Pattern):
            for column in df.columns:
                if isinstance(column, str) and pattern.search(str(column)):
                    if col_type == 'date_columns':
                        if 'date_columns' not in found_columns:
                            found_columns['date_columns'] = []
                        found_columns['date_columns'].append(column)
                    elif col_type == 'name_columns':
                        if 'name_columns' not in found_columns:
                            found_columns['name_columns'] = []
                        found_columns['name_columns'].append(column)
                    else:
                        found_column = column
                        break
        
        # Store the found column if not a date or name (dates and names are handled above)
        if found_column and col_type not in ['date_columns', 'name_columns']:
            found_columns[col_type] = found_column
            
    return found_columns

def find_dataframe_with_columns(file_path, column_patterns):
    file_extension = os.path.splitext(file_path)[1].lower()
    df = None
    found_columns = {}
    header_row = None

    if file_extension in ['.csv', '.xlsx', '.xls', '.xlsm']:
        if file_extension == '.csv':
            raw_df = pd.read_csv(file_path, header=None, dtype=str)
        elif file_extension == '.xls':
            raw_df = pd.read_excel(file_path, header=None, dtype=str, engine="xlrd")
        else:
            raw_df = pd.read_excel(file_path, header=None, dtype=str, engine="openpyxl")
        
        # Search for header row
        for i in range(len(raw_df)):
            row = raw_df.iloc[i]
            matches = 0
            for col in row:
                if isinstance(col, str):
                    col_lower = col.lower()
                    if any(
                        any(keyword in col_lower for keyword in keywords)
                        for keywords in column_patterns.values() if isinstance(keywords, list)
                    ):
                        matches += 1
                    elif any(
                        isinstance(keywords, re.Pattern) and keywords.search(col)
                        for keywords in column_patterns.values()
                    ):
                        matches += 1
            if matches >= 2:  # Good header guess
                header_row = i
                break

        if header_row is not None:
            if file_extension == '.csv':
                df = pd.read_csv(file_path, header=header_row, dtype=str)
            elif file_extension == '.xls':
                df = pd.read_excel(file_path, header=header_row, dtype=str, engine="xlrd")
            else:
                df = pd.read_excel(file_path, header=header_row, dtype=str, engine="openpyxl")
        else:
            raise ValueError("Could not automatically find a valid header row.")
        
        found_columns = find_columns(df, column_patterns)

    else:
        raise ValueError(f"Unsupported file extension: {file_extension}")
    
    return df, header_row, found_columns



def standardize_relation(value):
    if pd.isna(value):
        return 'Unknown'
    
    value = str(value).lower().strip()
    
    # Handle Employee/Subscriber -> Principal
    if value in ['employee', 'subscriber', 'self', 'owner', 'staff']:
        return 'Principal'
    
    # Handle Son/Daughter -> Child
    if value in ['son', 'daughter']:
        return 'Child'
    
    # Handle Wife/Husband -> Spouse
    if value in ['wife', 'husband', 'partner']:
        return 'Spouse'
    
    # Return original value if no match
    return value.capitalize()  # Capitalize first letter for consistency

def standardize_gender(value):
    if pd.isna(value):
        return 'Unknown'
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'Male'
    elif value in ['female', 'f']:
        return 'Female'
    
    return value.capitalize()  # Return original if not matching, but capitalized

def get_raw_gender(value):
    if pd.isna(value):
        return ''
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'M'
    elif value in ['female', 'f']:
        return 'F'
    
    return value  # Return original if not matching

def standardize_marital_status(value):
    if pd.isna(value):
        return 'unknown'
    
    value = str(value).lower().strip()
    
    if value in ['married', 'marriage', 'spouse', 'm', 'yes', 'y']:
        return 'married'
    elif value in ['single', 'unmarried', 'not married', 'n', 'no']:
        return 'unmarried'
    
    return value  # Return original if not matching, keep lowercase

def get_raw_marital_status(value):
    if pd.isna(value):
        return ''
    
    value = str(value).lower().strip()
    
    if value in ['married', 'marriage', 'spouse', 'm', 'yes', 'y']:
        return 'Married'
    elif value in ['single', 'unmarried', 'not married', 'n', 'no']:
        return 'Unmarried'
    
    return value.capitalize()  # Return original if not matching, but capitalized

def standardize_date(value):
    if pd.isna(value):
        return value

    value = str(value).strip()

    # Remove time component if present
    value = re.sub(r'\s+\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?', '', value, flags=re.IGNORECASE)

    try:
        # Attempt to parse the date
        date_obj = pd.to_datetime(value, dayfirst=True, errors='coerce')
        if pd.isna(date_obj):
            return value  # Return original if parsing fails

        # Convert to Excel serial number
        excel_start_date = datetime.datetime(1899, 12, 30)
        delta = date_obj - excel_start_date
        serial_number = delta.days + delta.seconds / 86400
        return round(serial_number, 2)  # Rounded to 2 decimal places
    except Exception:
        return value  # Return original if any error occurs

def extract_age(df, dob_column=None, age_column=None, current_date=None):
    if current_date is None:
        current_date = datetime.datetime.now()
    
    if age_column and age_column in df.columns:
        # Try to convert age column to numeric
        return pd.to_numeric(df[age_column], errors='coerce')
    
    elif dob_column and dob_column in df.columns:
        # Calculate age from date of birth
        try:
            # Convert DOB to datetime
            dob = pd.to_datetime(df[dob_column], errors='coerce')
            
            # If many NaT values, try different formats
            if dob.isna().sum() > len(df) / 2:
                # Try European format (DD.MM.YYYY)
                dob = pd.to_datetime(df[dob_column], format='%d.%m.%Y', errors='coerce')
                
                # If still many NaT values, try other common formats
                if dob.isna().sum() > len(df) / 2:
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                        temp_dob = pd.to_datetime(df[dob_column], format=fmt, errors='coerce')
                        if temp_dob.isna().sum() < dob.isna().sum():
                            dob = temp_dob
                            break
            
            # Calculate age in years
            age = ((current_date - dob).dt.days / 365.25).round(1)
            return age
            
        except Exception as e:
            print(f"Error calculating age from date of birth: {e}")
            return pd.Series([np.nan] * len(df))
    
    return pd.Series([np.nan] * len(df))

def combine_names(df, name_columns):
    if not name_columns:
        return pd.Series([''] * len(df))
    
    # Filter out columns that don't exist in the dataframe
    valid_columns = [col for col in name_columns if col in df.columns]
    
    if not valid_columns:
        return pd.Series([''] * len(df))
    
    # Start with the first valid column
    combined_names = df[valid_columns[0]].astype(str).fillna('')
    
    # Add remaining columns with a space in between
    for col in valid_columns[1:]:
        # Only add a space if both values are non-empty
        combined_names = combined_names.str.strip() + ' ' + df[col].astype(str).fillna('').str.strip()
        combined_names = combined_names.str.strip()
    
    # Clean up extra spaces
    combined_names = combined_names.str.replace(r'\s+', ' ', regex=True).str.strip()
    
    return combined_names

def assign_category(df, age_values=None, relation_column=None):
    categories = pd.Series([''] * len(df))
    
    # Implement your category assignment logic here
    # Example logic:
    if age_values is not None and relation_column is not None and relation_column in df.columns:
        for i in range(len(df)):
            age = age_values.iloc[i] if not pd.isna(age_values.iloc[i]) else 0
            relation = str(df[relation_column].iloc[i]).lower() if not pd.isna(df[relation_column].iloc[i]) else ''
            
            if 'principal' in relation or 'employee' in relation:
                if age < 30:
                    categories.iloc[i] = 'A'
                elif age < 50:
                    categories.iloc[i] = 'B'
                else:
                    categories.iloc[i] = 'C'
            elif 'spouse' in relation or 'partner' in relation:
                if age < 30:
                    categories.iloc[i] = 'A'
                elif age < 50:
                    categories.iloc[i] = 'B'
                else:
                    categories.iloc[i] = 'C'
            elif 'child' in relation or 'son' in relation or 'daughter' in relation:
                categories.iloc[i] = 'A'
            else:
                categories.iloc[i] = 'B'  # Default category
    
    return categories

def standardize_and_rename_columns(file_path, output_file=None):
    # Define column patterns to search for
    column_patterns = {
        'relation_column': re.compile(r'relation|relationship|dependent|role|type', re.IGNORECASE),
        'gender_column': re.compile(r'gender|sex|male\/female', re.IGNORECASE),
        'age_column': re.compile(r'^age$|^ages$|old', re.IGNORECASE),
        'dob_column': re.compile(r'birth|dob|born|birthday|date of birth', re.IGNORECASE),
        'marital_column': re.compile(r'marital|married|marriage|spouse|maritarial|status', re.IGNORECASE),
        'name_columns': re.compile(r'name|first|last|fname|lname|surname', re.IGNORECASE),
        'date_columns': re.compile(r'date', re.IGNORECASE),
        'category_column': re.compile(r'category|class|tier', re.IGNORECASE)
    }
    
    # Find dataframe and columns
    df, header_row, found_columns = find_dataframe_with_columns(file_path, column_patterns)
    
    print(found_columns)
    # Extract found columns
    relation_column = found_columns.get('relation_column')
    gender_column = found_columns.get('gender_column')
    age_column = found_columns.get('age_column')
    dob_column = found_columns.get('dob_column')
    marital_column = found_columns.get('marital_column')
    name_columns = found_columns.get('name_columns', [])
    date_columns = found_columns.get('date_columns', [])
    
    # Create a new DataFrame with the fixed column names
    standardized_df = pd.DataFrame()
    
    # 1. Extract and standardize age
    age_values = extract_age(df, dob_column, age_column)
    standardized_df['age'] = age_values
    
    # 2. Standardize date of birth
    if dob_column and dob_column in df.columns:
        standardized_df['dob'] = df[dob_column].apply(standardize_date)
    else:
        standardized_df['dob'] = ''
    
    # 3. Combine names
    standardized_df['name'] = combine_names(df, name_columns)
    
    # 4. Standardize gender
    if gender_column and gender_column in df.columns:
        standardized_df['gender'] = df[gender_column].apply(standardize_gender)
        standardized_df['rawGender'] = df[gender_column].apply(get_raw_gender)
    else:
        standardized_df['gender'] = 'Unknown'
        standardized_df['rawGender'] = ''
    
    # 5. Use existing category or assign if not found
    category_column = found_columns.get('category_column')
    if category_column and category_column in df.columns:
        standardized_df['category'] = df[category_column]
    else:
        # Fill all entries with "A"
        standardized_df['category'] = pd.Series(['A'] * len(df))
    # if category_column and category_column in df.columns:
    #     standardized_df['category'] = df[category_column]
    # else:
    #     standardized_df['category'] = assign_category(df, age_values, relation_column)
    
    # 6. Set fixed relation value
    standardized_df['relation'] = 'primary'  # As requested, this is fixed
    
    # 7. Standardize relation type
    if relation_column and relation_column in df.columns:
        standardized_df['relationType'] = df[relation_column].apply(standardize_relation)
    else:
        standardized_df['relationType'] = 'Unknown'
    
    # 8. Standardize marital status
    if marital_column and marital_column in df.columns:
        standardized_df['marital_status'] = df[marital_column].apply(standardize_marital_status)
        standardized_df['rawMarital_status'] = df[marital_column].apply(get_raw_marital_status)
    else:
        standardized_df['marital_status'] = 'Unknown'
        standardized_df['rawMarital_status'] = ''
    
    # Determine output file path if not provided
    if output_file is None:
        base_name, ext = os.path.splitext(file_path)
        output_file = f"{base_name}_standardized.xlsx"
    
    # Save the standardized data
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        standardized_df.to_excel(writer, index=False, sheet_name='Standardized')
    
    return standardized_df, output_file

def analyze_census(df):
    # Census count (total records)
    census_count = len(df)
    
    # Extract age values
    age_values = df['age']
    
    # Calculate statistics
    # 1. Over 64 years
    over_64_count = sum(age_values > 64)
    pct_elderly = round((over_64_count / census_count) * 100, 1) if census_count > 0 else 0
    
    # 2. Gender breakdown
    gender_stats = {'M': 0, 'F': 0}
    gender_pct = {'M': 0, 'F': 0}
    
    # Count gender values
    gender_stats['M'] = sum(df['rawGender'] == 'M')
    gender_stats['F'] = sum(df['rawGender'] == 'F')
    
    # Calculate percentages
    gender_pct['M'] = round((gender_stats['M'] / census_count) * 100, 1) if census_count > 0 else 0
    gender_pct['F'] = round((gender_stats['F'] / census_count) * 100, 1) if census_count > 0 else 0
    
    # 3. Married F (<45 y.o.)
    married_f_mask = (df['rawGender'] == 'F') & (df['marital_status'] == 'Married') & (df['age'] < 45)
    married_f_under_45 = sum(married_f_mask)
    pct_married_f_under_45 = round((married_f_under_45 / gender_stats['F']) * 100, 1) if gender_stats['F'] > 0 else 0
    
    # 4. Average Adult Age
    adult_mask = age_values >= 18
    avg_adult_age = round(age_values[adult_mask].mean(), 1) if sum(adult_mask) > 0 else 0
    
    # 5. Principal/Dependents counts
    principal_count = sum(df['relationType'] == 'Principal')
    dependent_count = sum((df['relationType'] != 'Principal') & (df['relationType'] != 'Unknown'))
    
    # Calculate percentages
    pct_principal = round((principal_count / census_count) * 100, 1) if census_count > 0 else 0
    pct_dependent = round((dependent_count / census_count) * 100, 1) if census_count > 0 else 0
    
    # Compile results
    analysis_results = {
        'census_count': census_count,
        'over_64_count': over_64_count,
        'pct_elderly': pct_elderly,
        'male_count': gender_stats['M'],
        'male_pct': gender_pct['M'],
        'female_count': gender_stats['F'],
        'female_pct': gender_pct['F'],
        'married_f_under_45': married_f_under_45,
        'pct_married_f_under_45': pct_married_f_under_45,
        'avg_adult_age': avg_adult_age,
        'principal_count': principal_count,
        'principal_pct': pct_principal,
        'dependent_count': dependent_count,
        'dependent_pct': pct_dependent
    }
    
    return analysis_results

def create_excel_analysis_report(df, output_path):
    # Generate analysis results
    results = analyze_census(df)
    
    # Create a DataFrame for the report
    report_data = {
        'Census Analysis': [
            'Census count',
            'Over 64 years',
            '% Elderly',
            '',
            'Census Analysis',
            'Census count',
            'M',
            'F',
            'Married F (<45 y.o.)',
            'Ave. Adult Age',
            '',
            'Principal',
            'Dependents'
        ],
        'Value': [
            results['census_count'],
            results['over_64_count'],
            f"{results['pct_elderly']}%",
            '',
            '',
            results['census_count'],
            results['male_count'],
            results['female_count'],
            results['married_f_under_45'],
            results['avg_adult_age'],
            '',
            results['principal_count'],
            results['dependent_count']
        ],
        'Percentage': [
            '',
            '',
            '',
            '',
            '',
            '',
            f"{results['male_pct']}%",
            f"{results['female_pct']}%",
            f"{results['pct_married_f_under_45']}%",
            '',
            '',
            f"{results['principal_pct']}%",
            f"{results['dependent_pct']}%"
        ]
    }
    
    # Create DataFrame
    report_df = pd.DataFrame(report_data)
    
    # Add stats to the standardized data file
    with pd.ExcelWriter(output_path, engine='openpyxl', mode='a') as writer:
        report_df.to_excel(writer, index=False, sheet_name='Census Analysis')
        
        # Get the workbook and sheet
        workbook = writer.book
        worksheet = writer.sheets['Census Analysis']
        
        # Apply basic formatting
        for col in ['A', 'B', 'C']:
            worksheet.column_dimensions[col].width = 20
    
    return output_path

def main():
    # Define input and output file paths
    input_file = "files/excel/MemberCensusDataTemplate.xls"
    output_file = "census.xls"
    
    try:
        # Step 1: Standardize and rename columns
        print(f"Processing file: {input_file}")
        standardized_df, output_path = standardize_and_rename_columns(input_file, output_file)
        
        # Step 2: Add statistics to the same Excel file
        create_excel_analysis_report(standardized_df, output_path)
        
        print(f"\nSuccessfully standardized data and calculated statistics")
        print(f"Output saved to: {output_path}")
        
        # Display a summary of the changes
        print("\nSummary of standardized data:")
        print(f"- Total records: {len(standardized_df)}")
        print(f"- Standardized columns: {', '.join(standardized_df.columns)}")
        
        # Display the first few rows of the standardized data
        print("\nSample of standardized data:")
        print(standardized_df.head(3))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()