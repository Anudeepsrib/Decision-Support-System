"""
Demo Cleanup Script
Removes all demo data and resets to clean state.
"""

import os
import shutil
from pathlib import Path

def cleanup_demo():
    """Remove all demo artifacts"""
    print("🧹 Cleaning up demo data...")
    
    demo_dir = Path(__file__).parent.parent
    project_root = demo_dir.parent
    
    # Files to remove
    to_remove = [
        demo_dir / "arr_dss_demo.db",  # SQLite demo database
        project_root / ".env.demo_backup",
    ]
    
    for path in to_remove:
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            print(f"   Removed: {path}")
    
    print("✅ Demo cleanup complete")
    print("\nTo fully remove demo:")
    print(f"   rm -rf {demo_dir}")

if __name__ == "__main__":
    cleanup_demo()
