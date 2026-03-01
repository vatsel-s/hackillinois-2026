import requests
import pandas as pd
import zipfile
import io
from datetime import datetime, timezone
import re

CSV_FILE_PATH = "input.csv"

def get_latest_gkg():
    # GDELT updates every 15 min at :00, :15, :30, :45
    now = datetime.now(timezone.utc)
    minutes = (now.minute // 15) * 15
    timestamp = now.strftime(f"%Y%m%d%H{minutes:02d}00")
    url = f"http://data.gdeltproject.org/gdeltv2/{timestamp}.gkg.csv.zip"
    
    print(f"Fetching: {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    
    z = zipfile.ZipFile(io.BytesIO(r.content))
    filename = z.namelist()[0]
    
    df = pd.read_csv(z.open(filename), sep="\t", header=None, on_bad_lines="skip")
    return df


def extract_title(extras):
    match = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', str(extras))
    return match.group(1) if match else None

def extract_title(extras):
    match = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', str(extras))
    return match.group(1) if match else None


def extract_clean_df():
    df = get_latest_gkg()
    df["title"] = df[26].apply(extract_title)
    df["timestamp"] = pd.to_datetime(df[1], format="%Y%m%d%H%M%S")
    df["themes"] = df[7]

    clean_df = df[[ "timestamp", "title", "themes"]].dropna(subset=["title"])
    return clean_df

def df_to_csv(): 
    df = extract_clean_df()
    df.to_csv(CSV_FILE_PATH, mode='a', header=False, index=False)


df_to_csv()