# 🌊 Branch Workflow Guide — Rafayel’s Velvet Lightning Playbook

Keep your masterpieces safe, Bry. This guide walks you through saving local changes (including this very guide) into a brand-new Git branch so the original `main` stays untouched until you’re ready.

---

## 0. Prerequisites
- Git is installed and configured (`git --version`).
- You’re inside the project root (`Script-Tools`).
- Your working tree has the latest changes you want to preserve (run `git status` to confirm).

---

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
- `git branch` → confirms you’re still on your feature branch.
- `git status` → should say “nothing to commit, working tree clean”.
- On GitHub, you’ll now see your branch ready for a pull request whenever you’re feeling dramatic.

---

## 6. Optional Next Moves
- Open a Pull Request targeting `main` (only when you’re ready).
- Keep iterating locally: stage → commit → push.
- When finished, merge via PR or `git merge feature/path-manager-upgrades` from `main`.

---

### Remember
Branching is your shield. `main` remains a pristine ocean until *you* decide to unleash the storm. Continue crafting with abandon, knowing your changes live safely on their own tide. 💙

