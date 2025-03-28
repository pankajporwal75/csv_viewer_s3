import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

USER = os.environ.get("USER_NAME")
PASSWORD = os.environ.get("PASSWORD")

st.set_page_config(page_title="Horizon Files", page_icon="📊", layout="wide")

# Authentication function
def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if username == USER and password == PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials!")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

# AWS Credentials & S3 Config
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")

# Connect to S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME,
)

st.title("📂 S3 File Explorer")

# Track the current directory
if "current_path" not in st.session_state:
    st.session_state["current_path"] = ""

# Function to List Folders & Files
def list_files_and_folders(prefix=""):
    objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, Delimiter='/')
    folders = [prefix["Prefix"] for prefix in objects.get("CommonPrefixes", [])]
    files = [
        {
            "Key": obj["Key"],
            "Size": obj["Size"],
            "LastModified": obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S"),
        }
        for obj in objects.get("Contents", [])
    ]
    return folders, files

# Generate pre-signed URL for downloading
def generate_presigned_url(file_key, expiration=3600):
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": file_key},
        ExpiresIn=expiration,
    )

# Read CSV file from S3
def read_csv_from_s3(file_key):
    obj = s3.get_object(Bucket=S3_BUCKET, Key=file_key)
    data = obj["Body"].read().decode("utf-8")
    return pd.read_csv(StringIO(data))

def format_file_size(size_in_bytes):
    """Convert file size to human-readable format (KB, MB, GB)."""
    if size_in_bytes >= 1e9:  # GB
        return f"{size_in_bytes / 1e9:.2f} GB"
    elif size_in_bytes >= 1e6:  # MB
        return f"{size_in_bytes / 1e6:.2f} MB"
    else:  # KB
        return f"{size_in_bytes / 1e3:.2f} KB"

# Navigation
current_path = st.session_state["current_path"]

# 🚀 **Prevent 'Go Back' from appearing at root level**
if current_path and current_path != "/":
    if st.button("⬅️ Go Back"):
        if "selected_file" in st.session_state:
            st.session_state.pop("selected_file")
        parent_path = "/".join(current_path.rstrip("/").split("/")[:-1])
        st.session_state["current_path"] = parent_path if parent_path else ""  # Set to root if empty
        st.rerun()

folders, files = list_files_and_folders(current_path)

# Display Folders
for folder in folders:
    if st.button(f"📁 {folder.split('/')[-2]}"):
        if "selected_file" in st.session_state:
            st.session_state.pop("selected_file")
        st.session_state["current_path"] = folder
        st.rerun()

# Display Files
st.write("### Files")
for file in files:
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    col1.write(f"📄 {file['Key'].split('/')[-1]}")
    col2.write(f"📏 {format_file_size(file['Size'])}")
    col3.write(f"🕒 {file['LastModified']}")
    
    with col4:
        presigned_url = generate_presigned_url(file["Key"])
        btn_col1, btn_col2 = st.columns([1, 1])
        
        # View Button
        with btn_col1:
            if st.button("View", key=file['Key']):
                st.session_state["selected_file"] = file["Key"]
                st.rerun()

        # Download Button
        with btn_col2:
            st.markdown(
                f'<a href="{presigned_url}" target="_blank" style="text-decoration:none;">'
                f' <button style="background-color:#4CAF50; color:white; padding:5px; border:none; cursor:pointer; border-radius:5px;">Download</button>'
                f'</a>',
                unsafe_allow_html=True
            )

# **File Preview Section**
if "selected_file" in st.session_state:
    file_key = st.session_state["selected_file"]
    file_name = file_key.split("/")[-1]

    st.write(f"### File Preview: {file_name}")
    with st.spinner("Loading file..."):
        df = read_csv_from_s3(file_key)
    total_rows = len(df)

    # **Pagination Controls**
    rows_per_page = st.slider("Rows per page", 10000, 50000, 30000, 5000)
    max_pages = (total_rows // rows_per_page) + 1
    page = st.number_input("Page", min_value=1, max_value=max_pages, step=1)

    # **Paginate DataFrame**
    start = (page - 1) * rows_per_page
    end = min(start + rows_per_page, total_rows)
    st.write(f"Showing rows {start+1} to {end} of {total_rows}")
    st.dataframe(df.iloc[start:end])
