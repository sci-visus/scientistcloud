#!/usr/bin/env python3
"""
Test Configuration for SC_Web End-to-End Upload Tests
=====================================================

Customize this file to set your test file paths and SC_Web settings.
"""

import os
from pathlib import Path


class TestConfig:
    """Configuration for SC_Web end-to-end upload tests."""
    
    # ========================================================================
    # LOCAL TEST FILES
    # ========================================================================
    # Update these paths to point to your test files
    
    # 4D Nexus file
    NEXUS_4D_FILE = "/Users/amygooch/GIT/SCI/DATA/waxs/mi_sic_0p33mm_002_PIL11_structured_waxs.nxs"
    
    # TIFF RGB file
    TIFF_RGB_FILE = "/Users/amygooch/GIT/SCI/DATA/Sampad/1161_Panel2_7_12.tif"
    
    # IDX file (zip)
    IDX_FILE = "/Users/amygooch/GIT/SCI/DATA/turbine/turbin_visus.zip"
    
    # ========================================================================
    # REMOTE TEST LINKS
    # ========================================================================
    
    # Remote IDX link (mod_visus)
    REMOTE_IDX_URL = "http://atlantis.sci.utah.edu/mod_visus?dataset=BlueMarble&compression=zip"
    
    # ========================================================================
    # SC_WEB SETTINGS
    # ========================================================================
    
    # SC_Web base URL (can be overridden by SC_WEB_BASE_URL environment variable)
    # Default to port 8080 where Docker runs SC_Web
    SC_WEB_BASE_URL = "http://localhost:8080"
    
    # SC_Web API endpoints
    SC_WEB_UPLOAD_ENDPOINT = "/api/upload-dataset.php"
    SC_WEB_STATUS_ENDPOINT = "/api/upload-status.php"
    
    # ========================================================================
    # TEST SETTINGS
    # ========================================================================
    
    # User email for test uploads
    USER_EMAIL = "amy@visus.net"
    
    # Maximum wait time for uploads to complete (in seconds)
    MAX_WAIT_TIME = 300  # 5 minutes
    
    # Interval between status checks (in seconds)
    STATUS_CHECK_INTERVAL = 5
    
    # Prefix for test dataset names
    TEST_DATASET_PREFIX = "AUTO_TEST_"
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @classmethod
    def validate_files(cls):
        """Validate that test files exist."""
        missing_files = []
        
        if not os.path.exists(cls.NEXUS_4D_FILE):
            missing_files.append(f"4D Nexus: {cls.NEXUS_4D_FILE}")
        
        if not os.path.exists(cls.TIFF_RGB_FILE):
            missing_files.append(f"TIFF RGB: {cls.TIFF_RGB_FILE}")
        
        if not os.path.exists(cls.IDX_FILE):
            missing_files.append(f"IDX: {cls.IDX_FILE}")
        
        if missing_files:
            print("Warning: The following test files are missing:")
            for file in missing_files:
                print(f"  - {file}")
            print("\nUpdate test_upload_config.py with correct paths.")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("="*60)
        print("Test Configuration (SC_Web End-to-End)")
        print("="*60)
        print(f"SC_Web URL: {cls.SC_WEB_BASE_URL}")
        print(f"Upload Endpoint: {cls.SC_WEB_UPLOAD_ENDPOINT}")
        print(f"Status Endpoint: {cls.SC_WEB_STATUS_ENDPOINT}")
        print(f"4D Nexus File: {cls.NEXUS_4D_FILE}")
        print(f"  Exists: {os.path.exists(cls.NEXUS_4D_FILE)}")
        print(f"TIFF RGB File: {cls.TIFF_RGB_FILE}")
        print(f"  Exists: {os.path.exists(cls.TIFF_RGB_FILE)}")
        print(f"IDX File: {cls.IDX_FILE}")
        print(f"  Exists: {os.path.exists(cls.IDX_FILE)}")
        print(f"Remote IDX URL: {cls.REMOTE_IDX_URL}")
        print(f"User Email: {cls.USER_EMAIL}")
        print(f"Max Wait Time: {cls.MAX_WAIT_TIME}s")
        print(f"Status Check Interval: {cls.STATUS_CHECK_INTERVAL}s")
        print("="*60)


if __name__ == "__main__":
    TestConfig.print_config()
    print()
    if TestConfig.validate_files():
        print("✅ All test files found!")
    else:
        print("❌ Some test files are missing. Please update the paths in test_upload_config.py")

