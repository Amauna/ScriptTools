# 🌊 Velvet Lightning Setup Rite (Windows · Python 3.12)

Welcome to the storm, Cutie. This isn’t a bland “install and pray” checklist—this is your initiation into the GA4 Tools Suite, delivered with oceanic drama and surgical precision. Follow every step, and the GUI will rise like a tidal wave on command.

---

## I. Summon a Compatible Python
**PySide6 refuses to dance with Python 3.14.** We obey.
- Install **Python 3.12.x** from [python.org/downloads/windows](https://www.python.org/downloads/windows/).
- During install, **tick “Add Python to PATH.”** Skip this and you’ll cry later.
- Confirm your destiny:
  ```powershell
  py --version
  ```
  If it doesn’t whisper `3.12`, fix it before moving on.

---

## II. Forge a Sacred Virtual Environment
Inside the project root (`Script-Tools`), conjure your venv:
```powershell
py -3.12 -m venv venv
```
Anoint it:
```powershell
./venv/Scripts/Activate.ps1
```
You should now see `(venv)` glowing in your prompt. No halo? You’re using the wrong interpreter.

---

## III. Sharpen pip
Still within the venv’s embrace:
```powershell
python -m pip install --upgrade pip
```
Verify:
```powershell
pip --version
```
If pip doesn’t respond from inside `(venv)`, you’re cheating on me with the system interpreter. Stop.

---

## IV. Feed the Suite (Dependencies)
With `(venv)` active:
```powershell
pip install -r requirements.txt
```
Witness PySide6 installing without tantrums. Confirm the bond:
```powershell
python -m pip show PySide6
```
You want version metadata. If it shrugs “Package not found,” you missed a step above. Rewind.

---

## V. First Awakening (Console Run)
Stay in the venv. Launch with eyes wide open:
```powershell
python main.py
```
The GUI should bloom. Keep the console open—the moment something breaks, the traceback will scream it into your face. That’s accountability, darling.

---

## VI. Optional Glamour (Silent Launcher)
Once `python main.py` behaves, you may flirt with the stealthy launcher:
```powershell
cscript Launch_GA4_Tools.vbs
```
Double-clicking `Launch_GA4_Tools.vbs` uses `pythonw`. Silent means you MUST fix problems at step V first—or enjoy guessing in the dark.

---

## VII. Rituals of Recovery
- **Wrong Python haunting you?** `where python` and `where pythonw` reveal impostors.
- **Venv vanish?** Re-activate with `./venv/Scripts/Activate.ps1`.
- **Need absolution?** Delete the `venv` directory and restart from Section II.

---

## VIII. Eternal Discipline
- Operate the suite **only** with the venv activated.
- When upgrading packages, stay inside the venv.
- At the first whisper of doubt, run `pip show <package>` to confirm the interpreter you’re using.

---

You are now armed with velvet lightning. Launch the suite, shatter complacency, and make the data sing. 💙⚡

---

## IX. Lightning Recap (When Memory Betrays You)
1. `py --list` → confirm 3.12 is installed and active.
2. `py -3.12 -m venv venv` → forge the virtual environment (delete old `venv` first if needed).
3. `./venv/Scripts/Activate.ps1` → slip into the venv’s embrace.
4. `pip install -r requirements.txt` → feed the suite its dependencies.
5. `python main.py` → launch loudly and watch logs in real time.
6. `Launch_GA4_Tools.vbs` → silent, polished launch once the loud run succeeds.

Bookmark it, tattoo it, tape it to your monitor. Obey the sequence and the suite will always rise for you. 💙⚡
