# 🌊 GitHub Branch Workflow Guide — Rafayel's Velvet Lightning Playbook ✨

*Your complete guide to GitHub branches: from cloning repos to importing files between branches*

---

## 📋 Table of Contents

### Part I: Getting Started
- [Prerequisites](#0-prerequisites)
- [Importing the Repo into Cursor](#importing-the-repo-into-cursor-fresh-clone)
- [Cloning a Specific Branch Directly (Avoid Nested Folders)](#-cloning-a-specific-branch-directly-avoid-nested-folders)

### Part II: Creating & Managing Branches
- [Create and Switch to a New Branch](#1-create-and-switch-to-a-new-branch)
- [Stage Your Changes](#2-stage-your-changes)
- [Commit with Context](#3-commit-with-context)
- [Push the Branch to GitHub](#4-push-the-branch-to-github)
- [Verify Everything](#5-verify-everything)
- [Optional Next Moves](#6-optional-next-moves)

### Part III: Importing Files from Branches
- [Quick Methods](#quick-methods)
- [Method 1: Clone Specific Branch](#method-1-clone-specific-branch)
- [Method 2: Fetch & Checkout Branch](#method-2-fetch--checkout-branch)
- [Method 3: Copy Files from Another Branch](#method-3-copy-files-from-another-branch)
- [Method 4: Merge Specific Files](#method-4-merge-specific-files)
- [Method 5: Pull from Remote Branch](#method-5-pull-from-remote-branch)
- [Troubleshooting](#troubleshooting)
- [Pro Tips](#pro-tips)
- [Common Workflows](#common-workflows)
- [Important Notes](#important-notes)
- [Security Reminder](#security-reminder)

---

# Part I: Getting Started 🌊

## 0. Prerequisites

Before diving into the ocean of branches, ensure you have:

- Git is installed and configured (`git --version`).
- You're inside the project root (`Script-Tools`).
- Your working tree has the latest changes you want to preserve (run `git status` to confirm).

---

## Importing the Repo into Cursor (fresh clone)

Pick the style that fits the moment—terminal or Cursor's UI. Either way, you end up in the same beautiful workspace.

### Option A: Terminal first, then open in Cursor

```bash
# 1. Pick a folder where you want the repo
cd "C:\Users\AM - Shift\Documents\Scripts For Modifying\Projects"

# 2. Clone the GitHub repo
git clone https://github.com/afaaubry/Script-Tools.git

# 3. Enter the project
cd Script-Tools

# 4. Launch Cursor pointing at this folder (optional if you open it manually)
cursor .
```

Now Cursor opens the project with the full Git history ready for branching.

### Option B: Clone directly from inside Cursor

1. Open the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **GitHub: Clone Repository**.
3. Paste `https://github.com/afaaubry/Script-Tools.git`.
4. Choose a local folder and wait for the clone to finish.

When Cursor prompts you, open the cloned workspace. Already have it cloned? Just run `git pull` in the built-in terminal to sync before you continue.

---

## ⚡ Cloning a Specific Branch Directly (Avoid Nested Folders)

**Problem:** When you clone a repo, it creates a folder with the repo name. If you're already in a folder with that name, you get nested folders like `Script-Tools/Script-Tools/`. *Dramatic gasp* Not on my watch, Cutie!

**Solution:** Clone a specific branch directly into your current folder or a custom folder name. No nested mess, just clean organization. ✨

### **Method 1: Clone Branch into Current Directory (No Nested Folder)**

**When to use:** You're in an **EMPTY** folder and want the branch files directly here.

> ⚠️ **CRITICAL:** The dot (`.`) method **ONLY works in an EMPTY directory**. If your directory has any files or folders, Git will refuse to clone and show: `fatal: destination path '.' already exists and is not an empty directory.`

```bash
# Navigate to an EMPTY folder where you want the project
cd "C:\Users\PC\Documents\MyNewProject"  # Must be empty!

# Clone the specific branch directly into current directory (no nested folder!)
git clone -b branch-name --single-branch https://github.com/username/repo-name.git .

# The dot (.) at the end means "clone into current directory"
```

**Example:**
```bash
# Create a new empty folder first
mkdir "C:\Users\PC\Documents\MyProject"
cd "C:\Users\PC\Documents\MyProject"

# Now clone feature branch directly here - files go into MyProject, not MyProject/MyProject
git clone -b feature/new-ui --single-branch https://github.com/afaaubry/Script-Tools.git .
```

**❌ What NOT to do (your current situation):**
```bash
# You're in: C:\Users\PC\...\GitHub\ (which already has Script-Tools folder)
# This will FAIL because the directory is not empty!
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git .
# Error: fatal: destination path '.' already exists and is not an empty directory.
```

**✅ Solution for non-empty directories:** Use Method 2 (custom folder name) instead!

### **Method 2: Clone Branch into Custom Folder Name** ⭐ **RECOMMENDED for Non-Empty Directories**

**When to use:** Your current directory already has files/folders, or you want to give the project folder a different name to avoid conflicts.

> 💡 **This is the solution for your error!** When you get `fatal: destination path '.' already exists and is not an empty directory`, use this method instead.

```bash
# Clone branch into a folder with a custom name (works even if directory has other files!)
git clone -b branch-name --single-branch https://github.com/username/repo-name.git custom-folder-name

# Then navigate into it
cd custom-folder-name
```

**Example - Fixing Your Exact Error:**
```bash
# You're in: C:\Users\PC\OneDrive\Documents\WorkScript\GitHub\
# This directory already has Script-Tools folder, so use a custom name!

# Clone feature branch into a folder called "Script-Tools-Feature" (no nested folders!)
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git Script-Tools-Feature

# Now navigate into it
cd Script-Tools-Feature

# Your structure will be:
# GitHub/
#   Script-Tools/          (your existing folder)
#   Script-Tools-Feature/  (new branch clone - clean, no nesting!)
```

**More Examples:**
```bash
# Clone with descriptive branch name in folder
git clone -b feature/new-ui --single-branch https://github.com/afaaubry/Script-Tools.git Script-Tools-UI

# Clone with date suffix
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git Script-Tools-2024-11-06
```

### **Method 3: Clone Branch into Parent Directory (Avoid Nesting)**

**When to use:** You're already in a folder that matches the repo name, and you want to clone the branch files directly into the parent.

```bash
# Navigate to parent directory first
cd ..

# Then clone into a differently named folder or current directory
git clone -b branch-name --single-branch https://github.com/username/repo-name.git branch-folder-name
```

**Example - Fixing Your Current Situation:**
```bash
# You're currently in: C:\Users\PC\...\Script-Tools\Script-Tools\
# And you want to avoid the nested Script-Tools/Script-Tools structure

# Option A: Go to parent and clone into a new folder
cd ..
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git Script-Tools-Feature

# Option B: If parent is empty, clone directly there
cd ..
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git .
```

### **Method 4: Clone Branch with Depth Limit (Faster, Less History)**

**When to use:** You only need the latest code, not full history. Saves time and space!

```bash
# Clone only the last commit from the branch (super fast!)
git clone -b branch-name --single-branch --depth 1 https://github.com/username/repo-name.git folder-name

# Or clone last 10 commits if you need a bit of history
git clone -b branch-name --single-branch --depth 10 https://github.com/username/repo-name.git folder-name
```

**Example:**
```bash
# Quick clone of just the latest code from feature branch
git clone -b feature/new-ui --single-branch --depth 1 https://github.com/afaaubry/Script-Tools.git Script-Tools-UI
```

### **🚨 Troubleshooting: "Destination path '.' already exists and is not an empty directory"**

**Problem:** You tried to use the dot (`.`) method but your directory isn't empty.

**Solution:** Use Method 2 (custom folder name) instead! Here's what to do:

```bash
# Check what's in your current directory first
dir  # Windows
# or
ls   # Linux/Mac

# If you see any files/folders, use a custom folder name instead of dot
git clone -b feature/path-manager-upgrades --single-branch https://github.com/afaaubry/Script-Tools.git Script-Tools-Feature
```

**Quick Decision Tree:**
- ✅ Directory is **EMPTY** → Use Method 1 (dot `.`)
- ❌ Directory has **files/folders** → Use Method 2 (custom folder name)
- 🤔 Not sure? → Use Method 2 (custom folder name) - it always works!

---

### **⚠️ Important Notes:**

1. **The dot (.) trick:** Using `.` at the end clones into current directory. **REQUIRES an EMPTY directory** - Git will refuse if there are any files or folders present!

2. **`--single-branch` flag:** This only downloads the branch you specify, saving bandwidth and time. Perfect for when you only need one branch!

3. **Custom folder names:** Always use a different name if you're cloning into a location that already has a folder with the repo name. This is the safest method and works in any directory!

4. **Check before cloning:** Use `dir` (Windows) or `ls` (Linux/Mac) to see what's in your current directory before cloning. If you see anything, use a custom folder name!

5. **When in doubt:** Use Method 2 (custom folder name) - it works in both empty and non-empty directories, and prevents nested folder issues!

---

# Part II: Creating & Managing Branches 🎭

Keep your masterpieces safe, Bry. This section walks you through saving local changes into a brand-new Git branch so the original `main` stays untouched until you're ready.

## 1. Create and Switch to a New Branch

Pick a name that reflects the feature or fixes:

```bash
git checkout -b feature/path-manager-upgrades
```

This command both creates the branch **and** moves you onto it. From now on, commits land here—not on `main`.

---

## 2. Stage Your Changes (Including This Guide)

Add everything you want to keep:

```bash
git add .
```

Prefer precision? Stage files individually:

```bash
git add tools/data_cleaning_transformation/column_order_harmonizer.py
git add docs/github_branch_workflow.md
```

Check staged items anytime with:

```bash
git status
```

---

## 3. Commit with Context

```bash
git commit -m "Document branch workflow and refine PathManager defaults"
```

No staged changes? Git will tell you—stage again and retry.

---

## 4. Push the Branch to GitHub

```bash
git push -u origin feature/path-manager-upgrades
```

The `-u` flag links your local branch to the remote branch, so future pushes are just `git push`.

---

## 5. Verify Everything

- `git branch` → confirms you're still on your feature branch.
- `git status` → should say "nothing to commit, working tree clean".
- On GitHub, you'll now see your branch ready for a pull request whenever you're feeling dramatic.

---

## 6. Optional Next Moves

- Open a Pull Request targeting `main` (only when you're ready).
- Keep iterating locally: stage → commit → push.
- When finished, merge via PR or `git merge feature/path-manager-upgrades` from `main`.

---

# Part III: Importing Files from Branches 📥

*Your complete guide to importing files from GitHub branches into your Cursor project*

## 🚀 Quick Methods

### **Scenario A: You want files from a branch in the SAME repository**

```bash
# Switch to the branch you want to copy from
git checkout branch-name

# Copy the files you need, then switch back
git checkout your-current-branch
```

### **Scenario B: You want files from a branch in a DIFFERENT repository**

```bash
# Add the remote repository
git remote add upstream https://github.com/username/repo-name.git

# Fetch the branch
git fetch upstream branch-name

# Checkout the branch (creates a local copy)
git checkout -b local-branch-name upstream/branch-name
```

---

## 📥 Method 1: Clone Specific Branch

**When to use:** Starting fresh or working with a completely different repository.

> 💡 **Want to avoid nested folders?** Check out [Cloning a Specific Branch Directly](#-cloning-a-specific-branch-directly-avoid-nested-folders) in Part I for methods to clone directly into your current directory or a custom folder name!

```bash
# Clone only a specific branch (saves time and space)
git clone -b branch-name --single-branch https://github.com/username/repo-name.git

# Or clone all branches but checkout specific one
git clone https://github.com/username/repo-name.git
cd repo-name
git checkout branch-name
```

**Example:**
```bash
git clone -b feature/new-ui --single-branch https://github.com/bry/awesome-project.git
```

**To avoid nested folders, use the dot (.) trick:**
```bash
# Clone directly into current directory (no nested folder!)
git clone -b feature/new-ui --single-branch https://github.com/bry/awesome-project.git .
```

---

## 🔄 Method 2: Fetch & Checkout Branch

**When to use:** You already have the repository cloned and want to access another branch.

```bash
# Fetch all branches from remote
git fetch origin

# List all available branches (local and remote)
git branch -a

# Checkout the remote branch (creates local tracking branch)
git checkout -b local-branch-name origin/remote-branch-name

# Or simply checkout if branch exists locally
git checkout branch-name
```

**Example:**
```bash
git fetch origin
git checkout -b feature/new-feature origin/feature/new-feature
```

---

## 📋 Method 3: Copy Files from Another Branch

**When to use:** You want specific files from another branch without switching branches.

```bash
# Copy a single file from another branch
git checkout branch-name -- path/to/file.py

# Copy multiple files
git checkout branch-name -- path/to/file1.py path/to/file2.py

# Copy an entire directory
git checkout branch-name -- path/to/directory/

# Copy all files matching a pattern
git checkout branch-name -- "*.py"
```

**Example:**
```bash
# You're on feature/path-manager-upgrades
# You want main.py from the main branch
git checkout main -- main.py

# You want entire styles directory from feature/new-themes branch
git checkout feature/new-themes -- styles/
```

**After copying, you'll need to commit:**
```bash
git add .
git commit -m "Import files from branch-name"
```

---

## 🔀 Method 4: Merge Specific Files

**When to use:** You want to merge changes from another branch into specific files.

```bash
# Method A: Using checkout (replaces your file with branch version)
git checkout branch-name -- path/to/file.py

# Method B: Using show (view file first, then manually copy)
git show branch-name:path/to/file.py > temp-file.py
# Review temp-file.py, then copy what you need

# Method C: Interactive merge for specific files
git checkout --patch branch-name path/to/file.py
# This shows you each change and asks if you want to apply it
```

**Example:**
```bash
# See what's different first
git diff main -- main.py

# Then checkout the file if you want to replace yours
git checkout main -- main.py

# Or use patch mode to selectively apply changes
git checkout --patch main main.py
```

---

## 🌐 Method 5: Pull from Remote Branch

**When to use:** The branch exists on GitHub but not locally, and you want to work with it.

```bash
# Fetch the remote branch
git fetch origin branch-name

# Checkout and track the remote branch
git checkout -b local-branch-name origin/branch-name

# Or if branch name matches, simply:
git checkout branch-name
# Git will automatically set up tracking if branch exists remotely
```

**Example:**
```bash
# Someone created a new branch on GitHub
git fetch origin
git checkout feature/cool-new-feature
```

---

## 🛠️ Troubleshooting

### **Problem: "Branch not found"**

```bash
# Make sure you've fetched from remote
git fetch origin

# List all remote branches
git branch -r

# List all branches (local and remote)
git branch -a
```

### **Problem: "File conflicts after checkout"**

```bash
# If you get conflicts, you can:
# 1. Stash your changes first
git stash
git checkout branch-name -- path/to/file.py
git stash pop

# 2. Or force checkout (WARNING: loses your changes)
git checkout -f branch-name -- path/to/file.py
```

### **Problem: "Want to preview changes before importing"**

```bash
# See what files differ between branches
git diff branch-name --name-only

# See actual differences in a file
git diff branch-name -- path/to/file.py

# See file from another branch without checking it out
git show branch-name:path/to/file.py
```

### **Problem: "Want to import but keep your current changes"**

```bash
# Stash your current work
git stash

# Import files from other branch
git checkout other-branch -- path/to/file.py

# Apply your stashed changes back
git stash pop
# Resolve any conflicts if they occur
```

---

## 💡 Pro Tips

### **1. Always check what you're importing:**

```bash
# Preview the file first
git show branch-name:path/to/file.py

# Or see the diff
git diff HEAD branch-name -- path/to/file.py
```

### **2. Import multiple files at once:**

```bash
# Create a list of files to import
git checkout branch-name -- \
  file1.py \
  file2.py \
  directory1/ \
  directory2/file3.py
```

### **3. Import and immediately review:**

```bash
# Import file
git checkout branch-name -- path/to/file.py

# See what changed
git diff --cached path/to/file.py

# If you don't like it, unstage
git restore --staged path/to/file.py
git restore path/to/file.py
```

### **4. Create a backup branch before importing:**

```bash
# Create backup of current state
git branch backup-before-import

# Now safely import files
git checkout other-branch -- path/to/file.py
```

---

## 🎯 Common Workflows

### **Workflow 1: Import a component from feature branch**

```bash
# You're on main, want a component from feature/ui-updates
git checkout feature/ui-updates -- components/Button.tsx
git add components/Button.tsx
git commit -m "Import Button component from feature/ui-updates"
```

### **Workflow 2: Sync specific files from main to your feature branch**

```bash
# You're on feature/my-feature, want latest utils from main
git checkout main -- utils/helpers.py
git add utils/helpers.py
git commit -m "Sync helpers from main branch"
```

### **Workflow 3: Import entire directory structure**

```bash
# Import entire tools directory from another branch
git checkout feature/new-tools -- tools/
git add tools/
git commit -m "Import new tools directory"
```

---

## ⚠️ Important Notes

1. **Always commit or stash changes** before importing files to avoid conflicts
2. **Review imported files** before committing - you might not want everything
3. **Test after importing** - imported code might have dependencies you don't have
4. **Check for conflicts** - especially if the file exists in your current branch
5. **Consider using `git show`** to preview files before importing

---

## 🔐 Security Reminder

When importing from external repositories:

- **Review the code** before importing (especially from untrusted sources)
- **Check for sensitive data** (API keys, passwords, tokens)
- **Verify dependencies** match your project requirements
- **Test thoroughly** after importing

---

## 💙 Remember

Branching is your shield. `main` remains a pristine ocean until *you* decide to unleash the storm. Continue crafting with abandon, knowing your changes live safely on their own tide. Whether you're creating branches or importing files between them, you're in control of your code's destiny. ✨🌊

---

*Created with 💙 by Rafayel - Your AI Muse* ✨🌊
