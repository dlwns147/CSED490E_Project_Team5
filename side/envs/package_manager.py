"""SIDE-ENV (docs/prereg/PREREG_SIDE.md): a generated agent environment in BFCL v4's multi-turn format, for testing the agent-loop
methods on an environment no verifier was trained on. A package manager with versioned dependencies: the agent must read the registry
(search_package), install missing dependencies before the package, pick versions by the stated policy, and remove or upgrade without
breaking installed packages. Every call's result depends only on its arguments and the state before it (never on call order), so BFCL's
checker (end state + unordered ground-truth results) accepts any order that reaches the same state.

State (initial_config["PackageManagerAPI"]): registry {name: {version: {"depends": {dep: [allowed versions]}, "size_mb": int}}},
installed {name: version}, disk_free_mb.
Version 2 (SIDE-ENV-2): each user request states what it implies (which dependencies, which versions, what to clean up), as BFCL's
requests do; version 1 (commit 301ac98) left two conventions to the function docs (an as_dependency flag and clean-up after a
removal), and no model followed them, thinking or not (PREREG_SIDE.md, SIDE-ENV results)."""
from copy import deepcopy


def vkey(v):
    return tuple(int(x) for x in v.split("."))


class PackageManagerAPI:
    def __init__(self):
        self.registry = {}
        self.installed = {}
        self.disk_free_mb = 0
        self._api_description = ("This tool belongs to the PackageManagerAPI, which installs, removes and upgrades software packages "
                                  "with versioned dependencies on one machine.")

    def _load_scenario(self, scenario: dict, long_context=False) -> None:
        s = deepcopy(scenario)
        self.registry = s.get("registry", {})
        self.installed = s.get("installed", {})
        self.disk_free_mb = s.get("disk_free_mb", 10000)

    def _needs(self, name, version, skip=None):
        """the installed packages (other than skip) whose installed version depends on `name`, with the versions they allow"""
        out = {}
        for p, v in self.installed.items():
            if p != skip:
                d = self.registry[p][v]["depends"]
                if name in d:
                    out[p] = d[name]
        return out

    def search_package(self, name: str) -> dict:
        """
        Look up a package in the registry.

        Args:
            name (str): Package name.
        Returns:
            name (str): Package name.
            versions (list): Each version with its size and its dependencies (dependency name -> allowed versions).
            installed_version (str): The installed version, or "none".
        """
        if name not in self.registry:
            return {"error": f"No package named '{name}' in the registry."}
        vs = sorted(self.registry[name], key=vkey)
        return {"name": name, "versions": [{"version": v, "size_mb": self.registry[name][v]["size_mb"],
                                            "depends": self.registry[name][v]["depends"]} for v in vs],
                "installed_version": self.installed.get(name, "none")}

    def list_installed(self) -> dict:
        """
        List the installed packages.

        Returns:
            installed (dict): Package name -> installed version.
        """
        return {"installed": dict(sorted(self.installed.items()))}

    def get_disk_space(self) -> dict:
        """
        Free disk space.

        Returns:
            disk_free_mb (int): Free space in MB.
        """
        return {"disk_free_mb": self.disk_free_mb}

    def install_package(self, name: str, version: str) -> dict:
        """
        Install one version of a package. Every dependency of that version must already be installed at an allowed version.

        Args:
            name (str): Package name.
            version (str): Version to install.
        Returns:
            status (str): "installed".
            package (str): Package name.
            version (str): Installed version.
        """
        if name not in self.registry:
            return {"error": f"No package named '{name}' in the registry."}
        if version not in self.registry[name]:
            return {"error": f"{name} has no version {version}."}
        if name in self.installed:
            return {"error": f"{name} {self.installed[name]} is already installed; upgrade it or remove it first."}
        for d, allowed in self.registry[name][version]["depends"].items():
            if d not in self.installed:
                return {"error": f"Missing dependency: {name} {version} needs {d} (one of {', '.join(allowed)})."}
            if self.installed[d] not in allowed:
                return {"error": f"Dependency conflict: {name} {version} needs {d} in [{', '.join(allowed)}], "
                                 f"but {d} {self.installed[d]} is installed."}
        size = self.registry[name][version]["size_mb"]
        if size > self.disk_free_mb:
            return {"error": f"Not enough disk space: {name} {version} needs {size} MB."}
        self.installed[name] = version
        self.disk_free_mb -= size
        return {"status": "installed", "package": name, "version": version}

    def remove_package(self, name: str) -> dict:
        """
        Remove an installed package. No other installed package may depend on it.

        Args:
            name (str): Package name.
        Returns:
            status (str): "removed".
            package (str): Package name.
            version (str): The version that was removed.
        """
        if name not in self.installed:
            return {"error": f"{name} is not installed."}
        need = self._needs(name, self.installed[name])
        if need:
            return {"error": f"Cannot remove {name}: needed by {', '.join(sorted(need))}."}
        v = self.installed.pop(name)
        self.disk_free_mb += self.registry[name][v]["size_mb"]
        return {"status": "removed", "package": name, "version": v}

    def upgrade_package(self, name: str, version: str) -> dict:
        """
        Change an installed package to another version. Every installed package that depends on it must allow the new version, and
        the new version's dependencies must already be installed at allowed versions.

        Args:
            name (str): Package name.
            version (str): The new version.
        Returns:
            status (str): "upgraded".
            package (str): Package name.
            from_version (str): The previous version.
            to_version (str): The new version.
        """
        if name not in self.installed:
            return {"error": f"{name} is not installed."}
        if version not in self.registry[name]:
            return {"error": f"{name} has no version {version}."}
        old = self.installed[name]
        if version == old:
            return {"error": f"{name} {version} is already installed."}
        for p, allowed in self._needs(name, old).items():
            if version not in allowed:
                return {"error": f"Cannot change {name} to {version}: {p} {self.installed[p]} needs {name} in [{', '.join(allowed)}]."}
        for d, allowed in self.registry[name][version]["depends"].items():
            if d not in self.installed:
                return {"error": f"Missing dependency: {name} {version} needs {d} (one of {', '.join(allowed)})."}
            if self.installed[d] not in allowed:
                return {"error": f"Dependency conflict: {name} {version} needs {d} in [{', '.join(allowed)}], "
                                 f"but {d} {self.installed[d]} is installed."}
        delta = self.registry[name][version]["size_mb"] - self.registry[name][old]["size_mb"]
        if delta > self.disk_free_mb:
            return {"error": f"Not enough disk space for {name} {version}."}
        self.installed[name] = version
        self.disk_free_mb -= delta
        return {"status": "upgraded", "package": name, "from_version": old, "to_version": version}
