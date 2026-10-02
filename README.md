# AD1-Bridge 🌉

> **Universal Autopsy Plugin & Portable Engine for AccessData AD1 Evidence Containers**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)]()
[![Autopsy](https://img.shields.io/badge/Autopsy-4.x-brightgreen.svg)](https://www.autopsy.com/)

**AD1-Bridge** is an open-source, cross-platform Autopsy plugin and standalone engine designed to seamlessly parse, extract, and ingest **AccessData (.ad1)** logical forensic images directly into Autopsy cases without requiring manual compilation, root permissions, or external dependencies.

---

## 💥 The Problem

AccessData FTK Imager (`.ad1`) is one of the most widely used logical forensic image formats. However:
- **Autopsy cannot read `.ad1` files directly** because they are proprietary logical archives, not sector-by-sector disk images.
- **Previous plugins only supported Windows**, hardcoding `.exe` dependencies that crash on Linux.
- **Compiling native Linux tools from source often fails** due to deprecated FUSE 2 headers and conflicting build environments.

**AD1-Bridge solves this for everyone.**

---

## ⚡ Features

- **🚀 1-Click Drop-In Installation:** No `make`, `gcc`, or `pip install` required.
- **🔄 Dual-Engine Architecture:**
  1. **Native Fast Engine:** Bundled standalone statically-linked binary for x86_64 Linux.
  2. **Pure Python 3 Fallback Engine:** 100% standard library implementation that runs anywhere Python 3 exists (ARM, macOS, Windows).
- **📥 Automatic Autopsy Ingest:** Adds the extracted filesystem directly into the active case as a native **Data Source**.
- **⏱️ Forensic Fidelity:** Preserves original MACB (Modified, Accessed, Created, Birth) timestamps and file integrity.
- **💻 Standalone CLI Mode:** Can also be used as a terminal tool independently of Autopsy.

---

## 📦 Installation for Autopsy

### 🎯 Universal Method (Recommended for All OS)
Because the exact plugin path can differ between operating systems, distros, and Autopsy versions, the easiest way to find your system's exact folder is inside Autopsy:

1. Launch **Autopsy**.
2. In the top menu bar, click **Tools** $\rightarrow$ **Python Plugins**.
   *(Autopsy will instantly open your machine's exact Python plugin folder in your file manager).*
3. Copy or clone the `AD1-Bridge` folder into that opened folder:
   ```bash
   git clone https://github.com/tanjimislam04/AD1-Bridge.git
   ```
4. Restart Autopsy.

---

### 💻 Direct Terminal Installation (Linux)
For Linux users installing directly via CLI:
```bash
# Standard Autopsy (NetBeans/Source build):
mkdir -p ~/.autopsy/dev/python_modules
git clone https://github.com/tanjimislam04/AD1-Bridge.git ~/.autopsy/dev/python_modules/AD1-Bridge

# If your installation uses ~/.autopsy/python_modules:
# mkdir -p ~/.autopsy/python_modules
# git clone https://github.com/tanjimislam04/AD1-Bridge.git ~/.autopsy/python_modules/AD1-Bridge
```

---

### 🪟 Windows Manual Installation
1. Click **Code** $\rightarrow$ **Download ZIP** on GitHub and extract the archive.
2. In Autopsy, open **Tools** $\rightarrow$ **Python Plugins** (this opens `%AppData%\autopsy\python_modules\`).
3. Copy the extracted `AD1-Bridge` folder into that directory.
4. Restart Autopsy.

---

## 🔍 How to Use in Autopsy

1. **Add Data Source:**
   - In Autopsy, click **Add Data Source** (or right-click an existing Logical File in your case tree $\rightarrow$ **Run Ingest Modules**).
   - Choose **Logical Files**.
   - Add your `.ad1` file (or a folder containing `.ad1` images).
2. **Configure Ingest Modules:**
   - ⚠️ **IMPORTANT:** In the Ingest Modules checklist, you MUST check:
     ```text
     ☑ AD1 Auto-Bridge
     ```
   - *(Tip for Linux Users)*: If Autopsy warns that an Ingest job cannot start, make sure Windows-only modules (e.g. *YARA Analyzer*) or unlicensed modules (e.g. *Cyber Triage*) are unchecked.
3. **Analyze:**
   - Click **Finish**.
   - AD1-Bridge extracts the evidence in the background, preserves all timestamps, and automatically injects the extracted directory tree (`Windows`, `Users`, Registry hives, `$Recycle.Bin`, etc.) as a new native Data Source in your case tree!

---

### 💡 Linux Troubleshooting Tip
If Autopsy's built-in **Windows Prefetch Analyzer** displays an error during analysis on Linux (`Exec failed, error: 13 Permission denied`), ensure execute permissions are set on Autopsy's internal artifact parser binary:
```bash
chmod +x /path/to/autopsy/autopsy/markmckinnon/mm_artifact_parser_x64_linux
```

---

## 🖥️ Standalone CLI Usage

You can also use AD1-Bridge directly in your terminal without Autopsy:

```bash
# Auto mode (uses fast native binary if available, otherwise pure Python)
python3 ad1_extractor.py -i /path/to/evidence.ad1 -o /path/to/extracted_folder

# Force pure Python engine (zero binary dependencies)
python3 ad1_extractor.py -i /path/to/evidence.ad1 -o /path/to/extracted_folder --engine python

# Verbose output
python3 ad1_extractor.py -i /path/to/evidence.ad1 -o /path/to/extracted_folder -v
```

---

## 🛠️ Repository Layout

```text
AD1-Bridge/
├── AD1_Bridge.py            # Autopsy Ingest Module (Jython 2.7)
├── ad1_extractor.py         # Cross-platform CLI runner and bridge
├── ad1_core/                # Pure Python 3 parser (standard library only)
│   ├── __init__.py
│   └── parser.py            # AD1 v3/v4 binary chunk decompressor
├── bin/
│   └── linux_x86_64/
│       └── ad1extract       # Statically linked Linux binary
├── LICENSE                  # MIT License
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
