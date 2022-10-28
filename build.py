#!/bin/python3

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
    read_korea()
    read_goatcorp()

    plugin_json: List[PluginInfo] = []

    for pluginName, plugin in lst_korea.items():
        if plugin_global := lst_global.get(pluginName):
            if "RepoUrl" not in plugin and (v := plugin_global.get("RepoUrl")):
                plugin["RepoUrl"] = v
            if "IconUrl" not in plugin and (v := plugin_global.get("IconUrl")):
                plugin["IconUrl"] = v
            if "ImageUrls" not in plugin and (v := plugin_global.get("ImageUrls")):
                plugin["ImageUrls"] = v
            if "CategoryTags" not in plugin and (
                v := plugin_global.get("CategoryTags")
            ):
                plugin["CategoryTags"] = v

        plugin["IsTestingExclusive"] = False
        plugin_json.append(plugin)

    for pluginName, plugin in lst_global.items():
        if pluginName in lst_korea or pluginName in list_exclude:
            continue

        is_compatible = (
            pluginName in lst_compatible
            and lst_compatible[pluginName] == plugin["AssemblyVersion"]
        )
        plugin["IsTestingExclusive"] = not is_compatible
        if is_compatible:
            prefix_new = URL_PREFIX_PLUGINS
            target_dir = OUT_PLUGINS

        else:
            prefix_new = URL_PREFIX_TESTING
            target_dir = OUT_TESTING

        plugin_json.append(plugin)

        path = plugin["DownloadLinkInstall"].removeprefix(URL_PREFIX_BASE)

        dir_src = os.path.dirname(os.path.join(GOATCORP_DIR, path))
        dir_dst = os.path.join(target_dir, *list(pathlib.Path(path).parts[1:-1]))
        copytree(dir_src, dir_dst)

        plugin["DownloadLinkInstall"] = change_prefix(
            plugin["DownloadLinkInstall"], URL_PREFIX_LIST, prefix_new
        )
        plugin["DownloadLinkTesting"] = change_prefix(
            plugin["DownloadLinkTesting"], URL_PREFIX_LIST, prefix_new
        )
        plugin["DownloadLinkUpdate"] = change_prefix(
            plugin["DownloadLinkUpdate"], URL_PREFIX_LIST, prefix_new
        )

    for plugin in plugin_json:
        plugin["DownloadCount"] = 0
        plugin["LastUpdate"] = 0

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

        json_path = os.path.join(
            dir_path, [x for x in os.listdir(dir_path) if x.endswith(".json")][0]
        )

        plugin: Dict[str, any]
        with open(json_path, "r", encoding="utf-8-sig") as fs:
            plugin = {k: v for k, v in json.load(fs).items() if v is not None}

        plugin["IsTestingExclusive"] = False

        zip_name = [x for x in os.listdir(dir_path) if x.endswith(".zip")][0]
        zip_url = f"{URL_PREFIX_PLUGINS}/{dir_name}/{zip_name}"

        plugin["DownloadLinkInstall"] = zip_url
        plugin["DownloadLinkTesting"] = zip_url
        plugin["DownloadLinkUpdate"] = zip_url

        images_path = os.path.join(dir_path, "images")
        if os.path.exists(images_path) and os.path.isdir(images_path):
            images = os.listdir(images_path)
            images_not_icon = [x for x in images if x != "icon.png"]

            if "icon.png" in images:
                plugin["IconUrl"] = f"{URL_PREFIX_PLUGINS}{dir_name}/images/icon.png"

            if len(images_not_icon):
                plugin["ImageUrls"] = [
                    f"{URL_PREFIX_PLUGINS}{dir_name}/images/{x}"
                    for x in images_not_icon
                ]

        k = plugin["InternalName"] if "InternalName" in plugin else plugin["Name"]
        lst_korea[k] = plugin

        copytree(dir_path, os.path.join(OUT_PLUGINS, dir_name))


def read_goatcorp():
    lst: Dict[str, PluginInfo]
    with open(
        os.path.join(GOATCORP_DIR, "pluginmaster.json"),
        "r",
        encoding="utf-8-sig",
    ) as fs:
        lst = json.load(fs)

    for plugin in lst:
        if (
            "DalamudApiLevel" not in plugin
            or plugin["DalamudApiLevel"] != DALAMUD_API_LEVEL
        ):
            continue

        dir = "plugins" if plugin["IsTestingExclusive"] == "False" else "testing"
        zip_url = f"{URL_PREFIX_BASE}{dir}/{plugin['InternalName']}/latest.zip"

        plugin["DownloadLinkInstall"] = zip_url
        plugin["DownloadLinkTesting"] = zip_url
        plugin["DownloadLinkUpdate"] = zip_url

        k = plugin["InternalName"] if "InternalName" in plugin else plugin["Name"]

        # use testing version
        if (k in lst_global) and lst_global[k]["IsTestingExclusive"] == True:
            print(
                f"Passed: {plugin['InternalName']} (@{plugin['Author']}) v{plugin['Version']}"
            )
            continue

        lst_global[k] = plugin


def change_prefix(s: str, prefix_old_list: List[str], prefix_new: str) -> str:
    for prefix_old in prefix_old_list:
        if s.startswith(prefix_old):
            return prefix_new + s.removeprefix(prefix_old)

    return s


if __name__ == "__main__":
    main()
