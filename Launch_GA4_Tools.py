#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌊 GA4 Data Analyst Tools Suite - Python Launcher
Double-click this file to launch the GUI~ 💙✨
"""

import os
import sys
import subprocess

def main():
    """Launch the GA4 Tools GUI"""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Change to the script directory
        os.chdir(script_dir)
        
        # Launch the main GUI
        subprocess.run([sys.executable, "main.py"], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error launching GUI: {e}")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
