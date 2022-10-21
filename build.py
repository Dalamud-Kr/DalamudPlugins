#!/bin/python3

from genericpath import isdir
import json
import os
import pathlib
from shutil import copytree, rmtree
from typing import Dict, Final, List, Optional, Tuple, Union

DALAMUD_API_LEVEL: Final = 6

IN_EXCLUDE_PATH: Final = "exclude.csv"
IN_COMPATIBLE_DIR: Final = "_compatible"
IN_PLUGINS: Final = "_plugins"

GOATCORP_DIR: Final = "goatcorp_DalamudPlugins"

URL_PREFIX_BASE: Final = (
    "https://raw.githubusercontent.com/Dalamud-Kr/DalamudPlugins/api6/"
)
URL_PREFIX_PLUGINS: Final = (
    "https://raw.githubusercontent.com/Dalamud-Kr/DalamudPlugins/api6/plugins/"
)
URL_PREFIX_TESTING: Final = (
    "https://raw.githubusercontent.com/Dalamud-Kr/DalamudPlugins/api6/testing/"
)
URL_PREFIX_LIST = [URL_PREFIX_PLUGINS, URL_PREFIX_TESTING]


OUT_PLUGINS: Final = "../api6/plugins"
OUT_TESTING: Final = "../api6/testing"
OUT_PLUGINMASTERS: Final = "../api6/pluginmaster.json"


PluginInfo = Dict[str, Optional[Union[str, int]]]

list_exclude: List[str] = []
lst_compatible: Dict[str, str] = {}
lst_korea: Dict[str, PluginInfo] = {}
lst_global: Dict[str, PluginInfo] = {}


def main():
    try:
        rmtree(OUT_PLUGINS)
    except:
        pass

    try:
        rmtree(OUT_TESTING)
    except:
        pass

    read_ignores()
    read_tested_plugins()
    read_goatcorp()
    read_korea()

    plugin_json: List[PluginInfo] = []

    for pk, p in lst_korea.items():
        p["IsTestingExclusive"] = False
        plugin_json.append(p)

    for pk, p in lst_global.items():
        if pk in lst_korea or pk in list_exclude:
            continue

        is_compatible = (
            pk in lst_compatible and lst_compatible[pk] == p["AssemblyVersion"]
        )
        p["IsTestingExclusive"] = not is_compatible
        if is_compatible:
            prefix_new = URL_PREFIX_PLUGINS
            target_dir = OUT_PLUGINS

        else:
            prefix_new = URL_PREFIX_TESTING
            target_dir = OUT_TESTING

        plugin_json.append(p)

        p = p["DownloadLinkInstall"].removeprefix(URL_PREFIX_BASE)

        dir_src = os.path.dirname(os.path.join(GOATCORP_DIR, p))
        dir_dst = os.path.join(target_dir, *list(pathlib.Path(p).parts[1:-1]))
        copytree(dir_src, dir_dst)

        p["DownloadLinkInstall"] = change_prefix(
            p["DownloadLinkInstall"], URL_PREFIX_LIST, prefix_new
        )
        p["DownloadLinkTesting"] = change_prefix(
            p["DownloadLinkTesting"], URL_PREFIX_LIST, prefix_new
        )
        p["DownloadLinkUpdate"] = change_prefix(
            p["DownloadLinkUpdate"], URL_PREFIX_LIST, prefix_new
        )

    for p in plugin_json:
        p["DownloadCount"] = 0

    with open(OUT_PLUGINMASTERS, "w", encoding="utf-8-sig") as fs:
        fs.truncate(0)
        json.dump(plugin_json, fs, indent=2)


def read_ignores():
    with open(IN_EXCLUDE_PATH, "r") as fs:
        for line in fs:
            list_exclude.append(line.strip())


def read_tested_plugins():
    for dir, _, files in os.walk(IN_COMPATIBLE_DIR):
        for file in files:
            p = os.path.join(dir, file)
            with open(p, "r", encoding="utf-8-sig") as fs:
                jo = json.load(fs)

            try:
                lst_compatible[jo["InternalName"]] = jo["AssemblyVersion"]
            except:
                print(f"Passed: {p}")


def read_korea():
    for dir_name in os.listdir(IN_PLUGINS):
        dir_path = os.path.join(IN_PLUGINS, dir_name)
        if not os.path.isdir(dir_path):
            continue

        path_json = os.path.join(
            dir_path, [x for x in os.listdir(dir_path) if x.endswith(".json")][0]
        )

        jo: Dict[str, any]
        with open(path_json, "r", encoding="utf-8-sig") as fs:
            jo = {k: v for k, v in json.load(fs).items() if v is not None}

        jo["IsTestingExclusive"] = False

        zip_name = [x for x in os.listdir(dir_path) if x.endswith(".zip")][0]
        zip_url = f"{URL_PREFIX_PLUGINS}/{dir_name}/{zip_name}"

        jo["DownloadLinkInstall"] = zip_url
        jo["DownloadLinkTesting"] = zip_url
        jo["DownloadLinkUpdate"] = zip_url

        k = jo["InternalName"] if "InternalName" in jo else jo["Name"]
        lst_korea[k] = jo

        copytree(dir_path, os.path.join(OUT_PLUGINS, dir_name))


def read_goatcorp():
    ja: Dict[str, PluginInfo]
    with open(
        os.path.join(GOATCORP_DIR, "pluginmaster.json"),
        "r",
        encoding="utf-8-sig",
    ) as fs:
        ja = json.load(fs)

    for jo in ja:
        if "DalamudApiLevel" in jo and jo["DalamudApiLevel"] != DALAMUD_API_LEVEL:
            continue

        dir = "plugins" if jo["IsTestingExclusive"] == "False" else "testing"
        zip_url = f"{URL_PREFIX_BASE}{dir}/{jo['InternalName']}/latest.zip"

        jo["DownloadLinkInstall"] = zip_url
        jo["DownloadLinkTesting"] = zip_url
        jo["DownloadLinkUpdate"] = zip_url

        k = jo["InternalName"] if "InternalName" in jo else jo["Name"]

        # use testing version
        if (k in lst_global) and lst_global[k]["IsTestingExclusive"] == True:
            print(f"Passed: {jo['InternalName']} (@{jo['Author']}) v{jo['Version']}")
            continue

        lst_global[k] = jo


def change_prefix(s: str, prefix_old_list: List[str], prefix_new: str) -> str:
    for prefix_old in prefix_old_list:
        if s.startswith(prefix_old):
            return prefix_new + s.removeprefix(prefix_old)

    return s


if __name__ == "__main__":
    main()
