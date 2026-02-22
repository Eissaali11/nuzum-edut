#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NUZUM - GitHub Upload Script
سكريبت رفع نزوم على جيتهاب
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Colors for output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def run_command(cmd, shell=False):
    """Run a command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    project_path = "D:\\nuzm"
    git_path = "C:\\Program Files (x86)\\Git\\bin\\git.exe"
    
    # Change to project directory
    os.chdir(project_path)
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
    print(f"{Colors.CYAN}NUZUM - Git Setup and Upload{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}\n")
    
    # Step 1: Check Git
    print(f"{Colors.GREEN}Step 1: Checking Git...{Colors.RESET}")
    code, out, err = run_command([git_path, "--version"])
    if code == 0:
        print(f"  ✓ {out.strip()}")
    else:
        print(f"  ✗ Git not found: {err}")
        return False
    
    # Step 2: Configure Git
    print(f"\n{Colors.GREEN}Step 2: Configuring Git...{Colors.RESET}")
    run_command([git_path, "config", "--global", "user.name", "NUZUM System"])
    run_command([git_path, "config", "--global", "user.email", "admin@nuzum.local"])
    print("  ✓ Git configured")
    
    # Step 3: Initialize repository
    print(f"\n{Colors.GREEN}Step 3: Initializing repository...{Colors.RESET}")
    git_path_exists = Path(".git").exists()
    if not git_path_exists:
        code, out, err = run_command([git_path, "init"])
        print("  ✓ Repository initialized")
    else:
        print("  ✓ Repository already exists")
    
    # Step 4: Add files
    print(f"\n{Colors.GREEN}Step 4: Adding files...{Colors.RESET}")
    code, out, err = run_command([git_path, "add", "."])
    print("  ✓ Files staged")
    
    # Step 5: Check status
    print(f"\n{Colors.GREEN}Step 5: Checking status...{Colors.RESET}")
    code, out, err = run_command([git_path, "status", "--short"])
    file_lines = [l for l in out.split('\n') if l.strip()]
    print(f"  ✓ Total files: {len(file_lines)}")
    
    # Step 6: Commit
    print(f"\n{Colors.GREEN}Step 6: Creating commit...{Colors.RESET}")
    commit_msg = "Initial commit: NUZUM Attendance System - Production Ready"
    code, out, err = run_command([git_path, "commit", "-m", commit_msg])
    if code == 0:
        print("  ✓ Commit successful")
    else:
        print(f"  ⚠ Commit: {err[:100] if err else out[:100]}")
    
    # Step 7: Display log
    print(f"\n{Colors.GREEN}Step 7: Commit history:{Colors.RESET}")
    code, out, err = run_command([git_path, "log", "--oneline", "-3"])
    for line in out.strip().split('\n')[:3]:
        if line.strip():
            print(f"  {line}")
    
    # Final message
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Repository Ready!{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}\n")
    
    print(f"{Colors.YELLOW}Next Steps:{Colors.RESET}")
    print(f"1. Go to: {Colors.CYAN}https://github.com/new{Colors.RESET}")
    print(f"2. Create repository: {Colors.CYAN}NUZUM{Colors.RESET}")
    print(f"3. Copy the HTTPS URL")
    print(f"4. Run these commands:\n")
    print(f"   {Colors.CYAN}git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git{Colors.RESET}")
    print(f"   {Colors.CYAN}git branch -M main{Colors.RESET}")
    print(f"   {Colors.CYAN}git push -u origin main{Colors.RESET}\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)
