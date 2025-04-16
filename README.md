# Configuration of Streamlit Python Application

## Python and Streamlit Installation

Step 1: Install PIP

Python is installed by default in the system check with following commands 

```bash
  python3 -V
```

## Step 1: Install PIP

```bash
  sudo apt install -y python3-pip
```

## Step 2: Install Packages

To install the required packages, run command: 

```bash
  pip install streamlit boto3 pandas python-dotenv
```

## Step 3: Setup Environment Variables

ENV File: Create a .env file in the project root directory

Variables: Provide following environment variables.

```bash
  USER_NAME=YOUR USERNAME
  PASSWORD=YOUR PASSWORD FOR AUTHENTICATION

  AWS_ACCESS_KEY=BUCKET ACCESS KEY
  AWS_SECRET_KEY=BUCKET SECRET KEY
  REGION_NAME=BUCKET REGION
```

## Step 4: Run Your Streamlit Application

Run the Streamlit app: In your terminal, navigate to the directory containing your application file and run it using streamlit

```bash
 streamlit run streamlit_app.py
```
Access your app: Streamlit will provide a URL in the terminal. You can access your application by navigating to this URL in your web browser.