import pandas as pd
import os
import datetime
import re
import numpy as np

def find_columns(df, column_patterns):
    """
    Find columns in DataFrame based on patterns.
    
    Args:
        df (pd.DataFrame): DataFrame to search in
        column_patterns (dict): Dictionary with key as column type and value as regex pattern or list of keywords
        
    Returns:
        dict: Dictionary with column types as keys and found column names as values
    """
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
                    found_column = column
                    break
        
        # Store the found column
        if found_column:
            found_columns[col_type] = found_column
            
    return found_columns

def find_dataframe_with_columns(file_path, column_patterns):
    """
    Tries to find the best DataFrame from a file that contains the specified columns.
    
    Args:
        file_path (str): Path to the CSV or Excel file
        column_patterns (dict): Dictionary with column types as keys and patterns as values
        
    Returns:
        tuple: (DataFrame, header_row, found_columns)
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    df = None
    header_row = 0
    found_columns = {}
    
    if file_extension == '.csv':
        # Try with different header positions
        for i in range(5):  # Try first 5 rows as potential headers
            try:
                temp_df = pd.read_csv(file_path, header=i)
                # Look for all columns using patterns
                temp_found = find_columns(temp_df, column_patterns)
                
                # If we found any of the columns we're looking for, use this dataframe
                if temp_found:
                    df = temp_df
                    header_row = i
                    found_columns = temp_found
                    break
                # If we haven't found a dataframe yet, use this one as a fallback
                elif df is None:
                    df = temp_df
                    header_row = i
            except Exception:
                continue
        
        # If no dataframe found, try with no header
        if df is None:
            df = pd.read_csv(file_path, header=None)
            
    elif file_extension in ['.xlsx', '.xls',".xlsm"]:
        for i in range(5): 
            try:
                temp_df = pd.read_excel(file_path, header=i)
                temp_found = find_columns(temp_df, column_patterns)

                if temp_found:
                    df = temp_df
                    header_row = i
                    found_columns = temp_found
                    break
                # If we haven't found a dataframe yet, use this one as a fallback
                elif df is None:
                    df = temp_df
                    header_row = i
            except Exception:
                continue
        
        # If still no success, try reading all sheets
        if df is None:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                for i in range(5):
                    try:
                        temp_df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
                        
                        # First check if this looks like valid data
                        if len(temp_df.columns) > 1:
                            # Look for all columns using patterns
                            temp_found = find_columns(temp_df, column_patterns)
                            
                            # If we found any of the columns we're looking for, use this dataframe
                            if temp_found:
                                df = temp_df
                                header_row = i
                                found_columns = temp_found
                                break
                            # If we haven't found a dataframe yet, use this one as a fallback
                            elif df is None:
                                df = temp_df
                                header_row = i
                    except Exception:
                        continue
                if df is not None:
                    break
    
    if df is None:
        raise ValueError(f"Could not read {file_path} with any header configuration.")
        
    # If we found a dataframe but haven't found all columns, search again
    if df is not None and len(found_columns) < len(column_patterns):
        found_columns = find_columns(df, column_patterns)
    
    return df, header_row, found_columns

def extract_age(df, age_column, date_column=None, current_date=None):
    """
    Extracts age from either direct age column or calculates from date of birth.
    
    Args:
        df (pd.DataFrame): DataFrame with census data
        age_column (str): Column containing age values
        date_column (str, optional): Column containing date of birth
        current_date (datetime, optional): Date to calculate age against
        
    Returns:
        pd.Series: Series containing age values
    """
    if age_column and age_column in df.columns:
        # Try to convert age column to numeric
        return pd.to_numeric(df[age_column], errors='coerce')
    
    elif date_column and date_column in df.columns:
        # Calculate age from date of birth
        if current_date is None:
            current_date = datetime.datetime.now()
            
        try:
            # Handle different date formats
            # First try standard parsing
            dob = pd.to_datetime(df[date_column], errors='coerce')
            
            # If many NaT values, try European format (DD.MM.YYYY)
            if dob.isna().sum() > len(df) / 2:
                dob = pd.to_datetime(df[date_column], format='%d.%m.%Y', errors='coerce')
            
            # Calculate age
            age = (current_date - dob).dt.days / 365.25
            return age
        except Exception as e:
            print(f"Error calculating age from date of birth: {e}")
            return pd.Series([np.nan] * len(df))
    
    return pd.Series([np.nan] * len(df))

def analyze_census(file_path):
    """
    Analyzes a census CSV or Excel file and calculates statistics.
    
    Args:
        file_path (str): Path to the census data file
        
    Returns:
        dict: Dictionary containing census statistics
    """
    # Define column patterns to search for
    column_patterns = {
        'relation_column': re.compile(r'relation|relationship|dependent|role|type', re.IGNORECASE),
        'gender_column': re.compile(r'gender|sex|male\/female', re.IGNORECASE),
        'age_column': re.compile(r'^age$|^ages$|old', re.IGNORECASE),
        'dob_column': re.compile(r'birth|dob|born|birthday', re.IGNORECASE),
        'marital_column': re.compile(r'marital|married|marriage|spouse|maritarial', re.IGNORECASE)
    }
    
    # Find dataframe and columns
    df, _, found_columns = find_dataframe_with_columns(file_path, column_patterns)
    
    print(found_columns)
    # Extract found columns
    relation_column = found_columns.get('relation_column')
    gender_column = found_columns.get('gender_column')
    age_column = found_columns.get('age_column')
    dob_column = found_columns.get('dob_column')
    marital_column = found_columns.get('marital_column')
    
    # Census count (total records)
    census_count = len(df)
    
    # Extract/calculate age
    age_values = extract_age(df, age_column, dob_column)
    
    # Calculate statistics
    # 1. Over 64 years
    over_64_count = sum(age_values > 64)
    pct_elderly = round((over_64_count / census_count) * 100, 1) if census_count > 0 else 0
    
    # 2. Gender breakdown
    gender_stats = {'M': 0, 'F': 0}
    gender_pct = {'M': 0, 'F': 0}
    
    if gender_column:
        # Standardize gender values for counting
        gender_values = df[gender_column].apply(lambda x: 
            'M' if pd.notna(x) and str(x).lower().strip() in ['male', 'm'] else
            'F' if pd.notna(x) and str(x).lower().strip() in ['female', 'f'] else
            str(x)
        )
        
        # Count gender values
        gender_counts = gender_values.value_counts()
        gender_stats['M'] = gender_counts.get('M', 0)
        gender_stats['F'] = gender_counts.get('F', 0)
        
        # Calculate percentages
        gender_pct['M'] = round((gender_stats['M'] / census_count) * 100, 1) if census_count > 0 else 0
        gender_pct['F'] = round((gender_stats['F'] / census_count) * 100, 1) if census_count > 0 else 0
    
    # 3. Married F (<45 y.o.)
    married_f_under_45 = 0
    pct_married_f_under_45 = 0
    
    if gender_column and marital_column:
        # Find married females under 45
        married_f_mask = (
            (gender_values == 'F') & 
            (df[marital_column].apply(lambda x: 
                pd.notna(x) and str(x).lower().strip() in ['married', 'spouse', 'yes', 'y', 'm']
            )) &
            (age_values < 45)
        )
        married_f_under_45 = sum(married_f_mask)
        pct_married_f_under_45 = round((married_f_under_45 / gender_stats['F']) * 100, 1) if gender_stats['F'] > 0 else 0
    
    # 4. Average Adult Age
    adult_mask = age_values >= 18
    avg_adult_age = round(age_values[adult_mask].mean(), 1) if sum(adult_mask) > 0 else 0
    
    # 5. Principal/Dependents counts
    principal_count = 0
    dependent_count = 0
    
    if relation_column:
        # Standardize relation values for counting
        relation_values = df[relation_column].apply(lambda x: 
            'Principal' if pd.notna(x) and str(x).lower().strip() in ['employee',"EMPLOYEE", 'subscriber', 'self', 'owner', 'staff', 'principal'] else
            'Dependent' if pd.notna(x) and str(x).lower().strip() in ['dependent', 'spouse', 'child', 'son', 'daughter', 'partner', 'wife', 'husband'] else
            str(x)
        )
        
        # Count relation values
        principal_count = sum(relation_values == 'Principal')
        dependent_count = sum(relation_values == 'Dependent')
    
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

def create_excel_analysis_report(file_path, output_path=None):
    """
    Analyzes a census file and creates an Excel report with the statistics.
    
    Args:
        file_path (str): Path to the census data file
        output_path (str, optional): Path to save the Excel report
        
    Returns:
        str: Path to the saved Excel report
    """
    # Generate analysis results
    results = analyze_census(file_path)
    
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
    
    # Determine output path
    if output_path is None:
        base_name, ext = os.path.splitext(file_path)
        output_path = f"{base_name}_analysis.xlsx"
    
    # Save to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        report_df.to_excel(writer, index=False, sheet_name='Census Analysis')
        
        # Get the workbook and sheet
        workbook = writer.book
        worksheet = writer.sheets['Census Analysis']
        
        # Apply basic formatting
        for col in ['A', 'B', 'C']:
            worksheet.column_dimensions[col].width = 20
    
    return output_path

def main():
    input_path="MemberCensusDataTemplate.xls"
    output_path="MemberCensusDataTemplate_stats.xlsx"
    try:
        
        # Create report
        output_path = create_excel_analysis_report(input_path, output_path)
        
        print(f"File processed: {input_path}")
        print(f"Analysis report saved to: {output_path}")
        
        # # Display a summary of the analysis
        # results = analyze_census(input_path)
        
        # print("\nCensus Analysis Summary:")
        # print(f"- Total census count: {results['census_count']}")
        # print(f"- Gender distribution: {results['male_count']} males ({results['male_pct']}%), "
        #       f"{results['female_count']} females ({results['female_pct']}%)")
        # print(f"- Elderly (over 64): {results['over_64_count']} ({results['pct_elderly']}%)")
        # print(f"- Average adult age: {results['avg_adult_age']}")
        # print(f"- Relation distribution: {results['principal_count']} principals ({results['principal_pct']}%), "
        #       f"{results['dependent_count']} dependents ({results['dependent_pct']}%)")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()