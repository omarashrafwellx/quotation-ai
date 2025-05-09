import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from matplotlib import pyplot as plt

def plot_gender_distribution(male_count, female_count):
    """
    Create a pie chart showing gender distribution.
    
    Args:
        male_count (int): Number of males
        female_count (int): Number of females
        
    Returns:
        str: Base64 encoded image
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['Male', 'Female']
    sizes = [male_count, female_count]
    colors = ['#5DA5DA', '#FAA43A']
    
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    plt.title('Gender Distribution')
    
    # Save the figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    
    # Encode the image to base64
    img_str = base64.b64encode(buf.read()).decode()
    
    plt.close(fig)
    
    return img_str

def plot_age_distribution(df, age_column=None, dob_column=None):
    """
    Create a histogram showing age distribution.
    
    Args:
        df (pd.DataFrame): DataFrame with census data
        age_column (str, optional): Name of the age column
        dob_column (str, optional): Name of the date of birth column
        
    Returns:
        str: Base64 encoded image
    """
    age_values = None
    
    # Try to find age data
    if age_column is not None and age_column in df.columns:
        age_values = pd.to_numeric(df[age_column], errors='coerce')
    elif dob_column is not None and dob_column in df.columns:
        try:
            # Convert date of birth to age
            dob = pd.to_datetime(df[dob_column], errors='coerce')
            now = pd.Timestamp.now()
            age_values = (now - dob).dt.days / 365.25
        except:
            pass
    
    # If no age data found, check common column names
    if age_values is None:
        for col in df.columns:
            col_str = str(col).lower()
            if 'age' in col_str:
                age_values = pd.to_numeric(df[col], errors='coerce')
                break
    
    # If still no age data found, return None
    if age_values is None or age_values.isna().all():
        return None
    
    # Filter out NaN and unreasonable ages
    age_values = age_values[~age_values.isna() & (age_values > 0) & (age_values < 120)]
    
    if len(age_values) == 0:
        return None
    
    # Create histogram
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Define age groups
    bins = [0, 18, 30, 45, 65, 120]
    labels = ['<18', '18-30', '31-45', '46-65', '>65']
    
    # Count number of people in each age group
    hist, bin_edges = np.histogram(age_values, bins=bins)
    
    # Plot the histogram
    ax.bar(labels, hist, color='#5DA5DA', alpha=0.7)
    
    # Add labels and title
    ax.set_xlabel('Age Group')
    ax.set_ylabel('Count')
    ax.set_title('Age Distribution')
    
    # Add count labels on top of the bars
    for i, count in enumerate(hist):
        ax.text(i, count + 0.1, str(count), ha='center')
    
    # Save the figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    
    # Encode the image to base64
    img_str = base64.b64encode(buf.read()).decode()
    
    plt.close(fig)
    
    return img_str

def plot_relation_distribution(principal_count, dependent_count):
    """
    Create a pie chart showing relation distribution.
    
    Args:
        principal_count (int): Number of principals
        dependent_count (int): Number of dependents
        
    Returns:
        str: Base64 encoded image
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['Principal', 'Dependent']
    sizes = [principal_count, dependent_count]
    colors = ['#5DA5DA', '#60BD68']
    
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    plt.title('Relation Distribution')
    
    # Save the figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    
    # Encode the image to base64
    img_str = base64.b64encode(buf.read()).decode()
    
    plt.close(fig)
    
    return img_str

def display_image(img_str):
    """
    Display a base64 encoded image in Streamlit.
    
    Args:
        img_str (str): Base64 encoded image
    """
    html = f'<img src="data:image/png;base64,{img_str}" style="width:100%">'
    st.markdown(html, unsafe_allow_html=True)