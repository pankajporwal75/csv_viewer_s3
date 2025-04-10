import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

# Load credentials
USER = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")

# Streamlit setup
st.set_page_config(page_title="Horizon Files", page_icon="📊", layout="wide")

# --- Authentication ---
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

# --- AWS S3 Setup ---
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME,
)

@st.cache_resource
def list_buckets():
    return [b["Name"] for b in s3.list_buckets()["Buckets"]]

# --- Sidebar: Bucket selection ---
bucket_options = list_buckets()
selected_bucket = st.sidebar.selectbox("Select Bucket", bucket_options)

# Reset state on bucket change
if selected_bucket != st.session_state.get("selected_bucket"):
    st.session_state["selected_bucket"] = selected_bucket
    st.session_state["current_path"] = ""
    if "selected_file" in st.session_state:
        del st.session_state["selected_file"]
    st.rerun()

S3_BUCKET = selected_bucket

# Initialize current_path from session
if "current_path" not in st.session_state:
    st.session_state["current_path"] = ""

# Navigation buttons
nav_col1, nav_col2 = st.columns([1, 1])

with nav_col1:
    if st.session_state["current_path"] and st.session_state["current_path"] != "/":
        if st.button("🏠 Home"):
            st.session_state["current_path"] = ""
            st.session_state.pop("selected_file", None)
            st.rerun()
        if st.button("⬅️ Go Back"):
            parent_path = "/".join(st.session_state["current_path"].rstrip("/").split("/")[:-1])
            if parent_path:
                parent_path += "/"
            st.session_state["current_path"] = parent_path
            st.session_state.pop("selected_file", None)
            st.rerun()
    

# Now set current_path AFTER any navigation
current_path = st.session_state["current_path"]

# --- List folders and files ---
def list_files_and_folders(bucket, prefix=""):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
    folders = [p["Prefix"] for p in response.get("CommonPrefixes", [])]
    files = [
        {
            "Key": obj["Key"],
            "Size": obj["Size"],
            "LastModified": obj["LastModified"],
        }
        for obj in response.get("Contents", [])
        if not obj["Key"].endswith("/")  # Exclude folder keys
    ]
    return folders, files

folders, files = list_files_and_folders(S3_BUCKET, current_path)

# --- Folder Display ---
for folder in folders:
    folder_name = folder.rstrip("/").split("/")[-1]
    if st.button(f"📁 {folder_name}"):
        st.session_state["current_path"] = folder
        st.session_state.pop("selected_file", None)
        st.rerun()

# --- File Sorting ---
st.markdown("### Files")

def generate_presigned_url(key, expires=3600):
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires
    )

def format_file_size(bytes):
    if bytes >= 1e9: return f"{bytes / 1e9:.2f} GB"
    if bytes >= 1e6: return f"{bytes / 1e6:.2f} MB"
    return f"{bytes / 1e3:.2f} KB"

# File tools: Search + Sort
tools_col1, tools_col2, tools_col3 = st.columns([3, 2, 1])

with tools_col1:
    search_query = st.text_input("🔍 Search files", placeholder="Enter filename...")

with tools_col2:
    sort_by = st.selectbox("Sort by", ["Name", "Size", "LastModified"], index=0)

with tools_col3:
    descending = st.checkbox("Desc", value=False)

# Apply search filter
if search_query:
    files = [f for f in files if search_query.lower() in f["Key"].lower()]

# Apply sorting
files.sort(
    key=lambda x: x["Key"] if sort_by == "Name" else x[sort_by],
    reverse=descending,
)

# Initialize previous values for comparison
prev_search = st.session_state.get("prev_search", "")
prev_sort = st.session_state.get("prev_sort", "LastModified")
prev_desc = st.session_state.get("prev_desc", True)

# Detect if search or sort changed
search_changed = search_query != prev_search
sort_changed = sort_by != prev_sort or descending != prev_desc

# Only clear preview if list context changed and user is NOT trying to view a file
if (
    "selected_file" in st.session_state and 
    (search_changed or sort_changed) and 
    not any(st.session_state.get(k) for k in [f"__button_clicked__{file['Key']}" for file in files])
):
    st.session_state.pop("selected_file", None)

# Store current values
st.session_state["prev_search"] = search_query
st.session_state["prev_sort"] = sort_by
st.session_state["prev_desc"] = descending


# --- File Listing ---
for file in files:
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    col1.write(f"📄 {file['Key'].split('/')[-1]}")
    col2.write(format_file_size(file["Size"]))
    col3.write(file["LastModified"].strftime("%Y-%m-%d %H:%M:%S"))

    presigned_url = generate_presigned_url(file["Key"])
    with col4:
        view_btn, download_btn = st.columns(2)
        with view_btn:
            if st.button("View", key=file["Key"]):
                st.session_state["selected_file"] = file["Key"]
                st.rerun()
        with download_btn:
            st.markdown(
                f'<a href="{presigned_url}" target="_blank">'
                f'<button style="background-color:#4CAF50; color:white; padding:5px; border:none; border-radius:5px;">Download</button>'
                f'</a>',
                unsafe_allow_html=True
            )
# --- Preview Selected File (Small Preview Only) ---
MAX_PREVIEW_SIZE = 50_000_000
if "selected_file" in st.session_state:
    file_key = st.session_state["selected_file"]
    file_name = file_key.split("/")[-1]
    file_ext = file_name.split(".")[-1].lower()

    # Get the file metadata to check size
    obj_meta = s3.head_object(Bucket=S3_BUCKET, Key=file_key)
    file_size = obj_meta["ContentLength"]

    st.write(f"### File Preview: {file_name}")

    if file_size > MAX_PREVIEW_SIZE:
        st.warning("⚠️ This file is too large to preview in the browser. Please download it instead.")
    else:
        with st.spinner("Loading CSV..."):
            obj = s3.get_object(Bucket=S3_BUCKET, Key=file_key)
            content = obj["Body"].read().decode("utf-8")
            lines = content.splitlines()

            total_rows = len(lines) - 1  # minus header
            rows_per_page = st.slider("Rows per page", 10000, 50000, 30000, 10000)
            max_pages = (total_rows // rows_per_page) + 1
            page = st.number_input("Page", min_value=1, max_value=max_pages, step=1)

            start = (page - 1) * rows_per_page + 1  # skip header on first page
            end = start + rows_per_page

            paginated_lines = [lines[0]] + lines[start:end]  # include header
            df = pd.read_csv(StringIO("\n".join(paginated_lines)), engine="pyarrow")

            st.write(f"Showing rows {start} to {min(end, total_rows)} of {total_rows}")
            st.dataframe(df, use_container_width=True)