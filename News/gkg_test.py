import requests
import pandas as pd
import zipfile
import io
from datetime import datetime, timezone
import re

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

df = get_latest_gkg()

def extract_title(extras):
    match = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', str(extras))
    return match.group(1) if match else None

df["title"] = df[26].apply(extract_title)
df["tone"] = df[15].apply(lambda x: float(str(x).split(",")[0]) if pd.notna(x) else None)
df["themes"] = df[7]
df["url"] = df[4]
df["persons"] = df[11]
df["timestamp"] = pd.to_datetime(df[1], format="%Y%m%d%H%M%S")

clean_df = df[["timestamp", "title", "tone", "themes", "persons", "url"]].dropna(subset=["title"])
print(clean_df.head(10))