"""Portable entry point; replaces a Colab-only export with the verified workflow."""
import sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p / 'analyze.py').is_file())
sys.path.insert(0,str(ROOT))
from analyze import main
if __name__=='__main__':main()
