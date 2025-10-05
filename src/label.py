 # create Benign / Suspicious / Unknown labels
import pandas as pd

def label_ips(feature_file="data/features/tor_features.parquet"):
    df = pd.read_parquet(feature_file)

    def classify(row):
        if row.get("abuse_score", 0) > 80 or "malicious" in str(row.get("greynoise_data", "")):
            return "Suspicious"
        elif row.get("abuse_score", 0) < 10:
            return "Benign"
        else:
            return "Unknown"

    df["label"] = df.apply(classify, axis=1)
    df.to_parquet("data/labeled/labeled_features.parquet")
    print("Labeled data saved!")