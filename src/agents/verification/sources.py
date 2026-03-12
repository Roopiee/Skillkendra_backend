import csv
from urllib.parse import urlparse
from typing import List, Dict, Set, Optional
import os

# Platform-specific URL patterns
URL_PATTERNS = {
    "coursera": [
        "https://www.coursera.org/verify/{cert_id}",
        "https://www.coursera.org/account/accomplishments/certificate/{cert_id}",
    ],
    "udemy": [
        "https://www.udemy.com/certificate/{cert_id}",
        "https://ude.my/{cert_id}",
    ],
    "edx": [
        "https://credentials.edx.org/credentials/{cert_id}",
    ],
    "linkedin": [
        "https://www.linkedin.com/learning/certificates/{cert_id}",
    ],
    "google": [
        "https://skillshop.exceedlms.com/student/award/{cert_id}",
    ],
    "ibm": [
        "https://www.credly.com/badges/{cert_id}",
        "https://www.credly.com/organizations/ibm/badges/{cert_id}",
    ],
    "microsoft": [
        "https://learn.microsoft.com/en-us/users/{cert_id}/transcript",
    ],
    "credly": [
        "https://www.credly.com/badges/{cert_id}",
    ]
}

from pathlib import Path

class TrustedSourceRegistry:
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.csv_path = str(base_dir / "data" / "trusted_sources.csv")
        else:
            self.csv_path = csv_path
            
        self.org_map: Dict[str, str] = {}
        self.trusted_domains: Set[str] = set()
        self._load_sources()

    def _load_sources(self):
        """Loads trusted organizations and domains from CSV"""
        # Default trusted domains
        self.trusted_domains = {
            "ude.my", "udemy.com", "coursera.org", "edx.org",
            "credentials.edx.org", "linkedin.com", "google.com",
            "skillshop.exceedlms.com", "credly.com"
        }

        if not os.path.exists(self.csv_path):
            print(f"[INFO] Trusted sources CSV not found, using defaults")
            return

        try:
            with open(self.csv_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
                
                for row in reader:
                    org = row.get("Organization Name", "").strip()
                    url = row.get("Verification URL", "").strip()
                    
                    if url:
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                        
                        domain = urlparse(url).netloc.lower().replace("www.", "")
                        self.trusted_domains.add(domain)
                        
                        if org:
                            self.org_map[org.lower()] = url
        except Exception as e:
            print(f"[WARNING] Could not load trusted sources CSV: {e}")

    def is_trusted(self, url: str) -> bool:
        """Checks if a URL belongs to a trusted domain"""
        try:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            return domain in self.trusted_domains or any(
                domain.endswith(f".{trusted}") for trusted in self.trusted_domains
            )
        except:
            return False

    def generate_urls(self, url: Optional[str], cert_id: Optional[str], org_name: Optional[str]) -> List[str]:
        """Generates a list of potential verification URLs"""
        urls = []
        if url:
            urls.append(url)
        
        if org_name and cert_id:
            org_lower = org_name.lower()
            
            # 1. CSV Lookup
            if org_lower in self.org_map:
                base = self.org_map[org_lower]
                urls.append(f"{base}/{cert_id}" if not base.endswith('/') else f"{base}{cert_id}")
            
            # 2. Pattern Matching
            for platform, patterns in URL_PATTERNS.items():
                if platform in org_lower:
                    urls.extend([p.format(cert_id=cert_id) for p in patterns])
                    break
        
        # Deduplicate
        return list(dict.fromkeys(urls))
