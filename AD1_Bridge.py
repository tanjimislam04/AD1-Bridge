# -*- coding: utf-8 -*-
"""
AD1-Bridge: Autopsy Ingest Module for AccessData AD1 Logical Images.
Automatically extracts .ad1 containers and ingests them into the active Case as a new Data Source.
Cross-platform: Works on Linux, macOS, and Windows.
Compatible with Autopsy 4.x (Jython 2.7).
"""

import inspect
import os
from subprocess import Popen, PIPE, STDOUT
import time

from java.lang import System
from java.util import UUID, ArrayList
from java.util.logging import Level
from org.sleuthkit.autopsy.casemodule import Case
from org.sleuthkit.autopsy.casemodule.services.FileManager import FileAddProgressUpdater
from org.sleuthkit.autopsy.coreutils import Logger, PlatformUtil
from org.sleuthkit.autopsy.ingest import (
    DataSourceIngestModule,
    IngestMessage,
    IngestModule,
    IngestModuleException,
    IngestModuleFactoryAdapter,
    IngestServices,
)
from org.sleuthkit.datamodel import BlackboardArtifact, BlackboardAttribute


def _which(name):
    """Portable which() implementation for Jython 2.7."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    # Common Linux locations fallback
    path_dirs.extend(["/usr/local/bin", "/usr/bin", "/bin", os.path.expanduser("~/.local/bin")])
    for directory in path_dirs:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        if PlatformUtil.isWindowsOS():
            for ext in [".exe", ".bat", ".cmd"]:
                cand_ext = candidate + ext
                if os.path.isfile(cand_ext):
                    return cand_ext
    return None


class ProgressUpdater(FileAddProgressUpdater):
    """Tracks files added as new data sources into the case."""

    def __init__(self):
        self.files = []

    def fileAdded(self, newfile):
        self.files.append(newfile)

    def getFiles(self):
        return self.files


class AD1BridgeIngestModuleFactory(IngestModuleFactoryAdapter):
    """Defines the AD1-Bridge module metadata in Autopsy."""

    moduleName = "AD1 Auto-Bridge"

    def getModuleDisplayName(self):
        return self.moduleName

    def getModuleDescription(self):
        return "Automatically extracts AccessData AD1 images and registers contents as a new Data Source."

    def getModuleVersionNumber(self):
        return "1.0.0"

    def isDataSourceIngestModuleFactory(self):
        return True

    def createDataSourceIngestModule(self, ingestOptions):
        return AD1BridgeDataSourceIngestModule()


class AD1BridgeDataSourceIngestModule(DataSourceIngestModule):
    """Executes background extraction and automatic ingestion of AD1 images."""

    _logger = Logger.getLogger(AD1BridgeIngestModuleFactory.moduleName)

    def log(self, level, msg):
        self._logger.logp(level, self.__class__.__name__, inspect.stack()[1][3], msg)

    def startUp(self, context):
        self.context = context

        # 1. Locate python3 interpreter
        self.python_bin = _which("python3") or _which("python")
        if not self.python_bin and PlatformUtil.isWindowsOS():
            # Check standard Windows paths
            for p in ["C:\\Python312\\python.exe", "C:\\Python311\\python.exe", "C:\\Python310\\python.exe"]:
                if os.path.isfile(p):
                    self.python_bin = p
                    break

        if not self.python_bin:
            raise IngestModuleException("Python 3 interpreter could not be found on PATH.")

        # 2. Locate ad1_extractor.py engine
        module_dir = os.path.dirname(os.path.abspath(__file__))
        self.extractor_script = os.path.join(module_dir, "ad1_extractor.py")

        if not os.path.isfile(self.extractor_script):
            raise IngestModuleException("AD1-Bridge engine script not found at: " + self.extractor_script)

        self.log(Level.INFO, "AD1-Bridge initialized. Python: " + self.python_bin)

    def process(self, dataSource, progressBar):
        self.log(Level.INFO, "AD1-Bridge starting inspection on data source.")
        progressBar.switchToIndeterminate()

        current_case = Case.getCurrentCase()
        file_manager = current_case.getServices().getFileManager()

        # Find all files in the current data source
        all_files = file_manager.findFiles(dataSource, "%", "/")
        ad1_targets = []

        for f in all_files:
            if f.isDir():
                continue
            name_lower = f.getName().lower()
            if name_lower.endswith(".ad1"):
                local_path = f.getLocalAbsPath()
                if local_path and os.path.isfile(local_path):
                    ad1_targets.append((f, local_path))

        if not ad1_targets:
            self.log(Level.INFO, "No .ad1 files found in this data source.")
            return IngestModule.ProcessResult.OK

        self.log(Level.INFO, "Found " + str(len(ad1_targets)) + " AD1 file(s) to process.")

        # Module base output directory inside the active Case
        base_output_dir = os.path.join(current_case.getModulesOutputDirAbsPath(), "AD1_Extracted")
        if not os.path.exists(base_output_dir):
            try:
                os.makedirs(base_output_dir)
            except Exception as e:
                self.log(Level.WARNING, "Failed to create base dir: " + str(e))

        extracted_sources = []

        for target_file, ad1_abs_path in ad1_targets:
            filename = target_file.getName()
            clean_name = os.path.splitext(filename)[0]
            target_out_dir = os.path.join(base_output_dir, clean_name)

            progressBar.progress("AD1-Bridge: Extracting " + filename)
            self.log(Level.INFO, "Extracting " + ad1_abs_path + " -> " + target_out_dir)

            cmd = [self.python_bin, self.extractor_script, "-i", ad1_abs_path, "-o", target_out_dir, "--engine", "auto"]

            try:
                proc = Popen(cmd, stdout=PIPE, stderr=STDOUT)
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if "[STATUS]" in line or "Extracting" in line:
                        progressBar.progress("AD1: " + line.replace("[STATUS]", "").strip())
                proc.wait()

                if proc.returncode != 0:
                    self.log(Level.SEVERE, "Extraction failed for " + filename + " with code: " + str(proc.returncode))
                    continue

                self.log(Level.INFO, "Extraction completed for " + filename)

                # Locate actual evidence root inside the extracted directory
                ingest_root = target_out_dir
                # If extraction created a partition folder with [root], find the cleanest root
                for root_dir, dirs, files in os.walk(target_out_dir):
                    if "[root]" in dirs:
                        ingest_root = os.path.join(root_dir, "[root]")
                        break

                # Automatically register into Autopsy as a new Data Source!
                progressBar.progress("Registering extracted evidence into Case...")
                progress_updater = ProgressUpdater()
                device_id = UUID.randomUUID()

                current_case.notifyAddingDataSource(device_id)

                new_data_source = file_manager.addLocalFilesDataSource(
                    str(device_id),
                    "AD1: " + clean_name,
                    "",
                    [ingest_root],
                    progress_updater
                )

                for added_file in progress_updater.getFiles():
                    current_case.notifyDataSourceAdded(added_file, device_id)

                extracted_sources.append(filename)

                # Send success message to Autopsy notifications inbox
                msg = IngestMessage.createMessage(
                    IngestMessage.MessageType.DATA,
                    "AD1-Bridge",
                    "Successfully extracted and indexed: " + filename
                )
                IngestServices.getInstance().postMessage(msg)

            except Exception as ex:
                self.log(Level.SEVERE, "Error running AD1-Bridge for " + filename + ": " + str(ex))

        return IngestModule.ProcessResult.OK
