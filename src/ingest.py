# download + parse CollecTor data
from stem.descriptor.remote import DescriptorDownloader
import pandas as pd
from datetime import datetime
from pathlib import Path

def fetch_tor_relays(output_dir="data/raw"):
    downloader = DescriptorDownloader(timeout=60)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    relays = []

    for desc in downloader.get_server_descriptors():
        relays.append({
            "fingerprint": desc.fingerprint,
            "ip": desc.address,
            "nickname": desc.nickname,
            "as_number": desc.exit_policy_v6,
            "country": desc.extra_info_digest.hex() if desc.extra_info_digest else None,
            "first_seen": desc.published.strftime("%Y-%m-%d"),
            "bandwidth": desc.average_bandwidth,
            "flags": desc.flags
        })

    df = pd.DataFrame(relays)
    df.to_parquet(f"{output_dir}/tor_relays_{datetime.now().date()}.parquet")
    print(f"Saved {len(df)} relays to {output_dir}")

if __name__ == "__main__":
    fetch_tor_relays()