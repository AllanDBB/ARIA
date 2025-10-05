"""Download MEDA sample data for testing ARIA pipeline.

This script helps you download a small sample of NASA Perseverance MEDA data
for testing the ARIA SDK. It can download via Kaggle API or provide instructions
for manual download.

Usage:
    python scripts/download_meda.py --sols 100-110 --output data/meda
    python scripts/download_meda.py --manual  # Shows manual download instructions
"""

import argparse
import sys
from pathlib import Path


def show_manual_instructions():
    """Show instructions for manual download."""
    print("=" * 70)
    print("MEDA Data - Manual Download Instructions")
    print("=" * 70)
    print()
    print("📦 Dataset: Mars 2020 Perseverance MEDA Rover Data (Derived)")
    print("   Size: ~18 GB (full dataset)")
    print()
    print("Option 1: Download from Kaggle (Recommended)")
    print("-" * 70)
    print("1. Visit: https://www.kaggle.com/datasets/lolajackson/mars-2020-perseverance-meda-rover-data-derived")
    print("2. Click 'Download' button (requires free Kaggle account)")
    print("3. Extract the ZIP file")
    print("4. Copy MARS_MEDA_DATA/DERIVED/ folder to:")
    print("   → data/meda/")
    print()
    print("Expected structure after extraction:")
    print("   data/meda/")
    print("     ├── DER_PS/           # Pressure sensor")
    print("     ├── DER_TIRS/         # Temperature")
    print("     ├── DER_RHS/          # Humidity")
    print("     ├── DER_WS/           # Wind")
    print("     └── DER_Ancillary/    # Context data")
    print()
    print("Option 2: Download from NASA PDS")
    print("-" * 70)
    print("1. Visit: https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/")
    print("2. Download specific data products:")
    print("   - data_derived_env/ (contains all derived data)")
    print("3. Extract to data/meda/")
    print()
    print("Option 3: Download Sample Data (Quick Start)")
    print("-" * 70)
    print("For a quick test, you can create synthetic data:")
    print()
    print("  python scripts/create_sample_meda.py --sol 100 --output data/meda")
    print()
    print("This creates a small synthetic dataset for Sol 100 (~1 MB)")
    print()
    print("=" * 70)
    print()
    print("After downloading, test with:")
    print("  python -m aria_sdk.examples.meda_demo --sol 100")
    print()


def check_kaggle_api():
    """Check if Kaggle API is available."""
    try:
        import kaggle
        return True
    except ImportError:
        return False


def download_with_kaggle(output_dir: Path):
    """Download dataset using Kaggle API."""
    try:
        import kaggle
    except ImportError:
        print("❌ Kaggle API not installed.")
        print()
        print("Install with:")
        print("  pip install kaggle")
        print()
        print("Then configure API credentials:")
        print("1. Go to https://www.kaggle.com/settings")
        print("2. Scroll to 'API' section")
        print("3. Click 'Create New API Token'")
        print("4. Save kaggle.json to:")
        print("   Windows: C:\\Users\\<username>\\.kaggle\\kaggle.json")
        print("   Linux/Mac: ~/.kaggle/kaggle.json")
        print()
        return False
    
    print("📥 Downloading MEDA dataset from Kaggle...")
    print(f"   Dataset: lolajackson/mars-2020-perseverance-meda-rover-data-derived")
    print(f"   Output: {output_dir.absolute()}")
    print()
    print("⚠️  This is a large download (~18 GB). This may take a while...")
    print()
    
    try:
        # Download dataset
        kaggle.api.dataset_download_files(
            "lolajackson/mars-2020-perseverance-meda-rover-data-derived",
            path=output_dir,
            unzip=True
        )
        
        print("✅ Download complete!")
        print()
        print("Next, move the DERIVED folder contents:")
        print(f"  From: {output_dir / 'MARS_MEDA_DATA' / 'DERIVED'}")
        print(f"  To:   {output_dir}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print()
        print("Try manual download instead (see --manual)")
        return False


def create_synthetic_sample(output_dir: Path, sol: int = 100):
    """Create a small synthetic MEDA dataset for testing."""
    import csv
    from datetime import datetime, timedelta, timezone
    import random
    
    print(f"🔨 Creating synthetic MEDA data for Sol {sol}...")
    print(f"   Output: {output_dir.absolute()}")
    print()
    
    # Create directories
    pressure_dir = output_dir / "DER_PS"
    pressure_dir.mkdir(parents=True, exist_ok=True)
    
    # Create synthetic pressure data
    csv_file = pressure_dir / f"SOL_{sol:04d}_{sol:04d}_DER_PS.csv"
    
    base_time = datetime(2021, 6, 9, 0, 0, 0, tzinfo=timezone.utc)
    base_pressure = 730.0  # Typical Mars pressure in Pa
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['SOL', 'LMST', 'UTC', 'PRESSURE', 'QUALITY_FLAG'])
        writer.writeheader()
        
        # Generate 1 sample per second for 1 Martian sol (88775 seconds ≈ 24.6 hours)
        for i in range(1000):  # Just 1000 samples for quick demo
            timestamp = base_time + timedelta(seconds=i)
            
            # Simulate daily pressure cycle (sinusoidal)
            pressure = base_pressure + 10 * (i / 1000.0) * (1 - i / 1000.0)
            pressure += random.gauss(0, 0.5)  # Add noise
            
            # LMST format
            hours = (i // 3600) % 24
            minutes = (i // 60) % 60
            seconds = i % 60
            lmst = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            writer.writerow({
                'SOL': sol,
                'LMST': lmst,
                'UTC': timestamp.isoformat().replace('+00:00', 'Z'),
                'PRESSURE': f"{pressure:.2f}",
                'QUALITY_FLAG': 1
            })
    
    print(f"✅ Created synthetic data: {csv_file}")
    print(f"   Samples: 1,000 pressure readings")
    print()
    print("Test with:")
    print(f"  python -m aria_sdk.examples.meda_demo --sol {sol} --data-dir {output_dir.absolute()}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download MEDA data for ARIA testing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/meda"),
        help="Output directory (default: data/meda)"
    )
    
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Show manual download instructions"
    )
    
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="Download using Kaggle API"
    )
    
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Create synthetic sample data for quick testing"
    )
    
    parser.add_argument(
        "--sol",
        type=int,
        default=100,
        help="Sol number for synthetic data (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Show manual instructions
    if args.manual:
        show_manual_instructions()
        return
    
    # Create synthetic sample
    if args.synthetic:
        create_synthetic_sample(args.output, sol=args.sol)
        return
    
    # Download with Kaggle API
    if args.kaggle:
        if not check_kaggle_api():
            print("❌ Kaggle API not available")
            print("   Install with: pip install kaggle")
            print("   Or use --manual for manual download instructions")
            sys.exit(1)
        
        download_with_kaggle(args.output)
        return
    
    # Default: show instructions
    print("MEDA Data Download Tool")
    print()
    print("Choose a download method:")
    print("  --manual     Show manual download instructions")
    print("  --kaggle     Download using Kaggle API (~18 GB)")
    print("  --synthetic  Create synthetic sample data (~1 MB, quick)")
    print()
    print("Example:")
    print("  python scripts/download_meda.py --synthetic --sol 100")
    print()


if __name__ == "__main__":
    main()
