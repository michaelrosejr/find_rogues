import logging
import sys
from typing import Dict, Optional

import pendulum as pdl
import pycentral
import typer
import yaml
import apprise

from fuzzywuzzy import fuzz, process
from pathlib import Path
from loguru import logger
from mailer import send_template_email
from pycentral.base import ArubaCentralBase
from rich import print
from rich.console import Console
from rich.table import Table
from tabulate import tabulate
from slack_table import SlackTableUploader, SlackApiError
from savedata import save_to_file
from smtplegacy import send_legacy_email

with open(".env.yaml", "r") as envf:
    central_info = yaml.safe_load(envf)

logger.remove()
logger.add(sys.stderr, level="ERROR")

apobj = apprise.Apprise()
app = typer.Typer(no_args_is_help=True, help="Aruba Central Rogue AP Report")


ssl_verify = True

apiParams = {"limit": 80, "offset": 0}


def get_groups(central):
    """API call to Central to get a list of Central Groups

    Args:
        central (class): Central API object

    Returns:
        Optional[Dict]: dictionary of central groups
    """
    apiPath = "/configuration/v2/groups"
    apiMethod = "GET"
    console = Console()
    with console.status("[bold green]Getting Suspected Rogues...") as status:
        resp = central.command(
            apiMethod=apiMethod, apiPath=apiPath, apiParams=apiParams
        )

    return resp


def get_rogues(central) -> Optional[Dict]:
    """API call to Central to get a list only of rogue APs

    Args:
        central (class): Central API object

    Returns:
        Optional[Dict]: dictionary of rogue APs
    """
    apiPath = "/rapids/v1/rogue_aps"
    apiMethod = "GET"
    console = Console()
    with console.status("[bold green]Getting Rogue APs...") as status:
        resp = central.command(
            apiMethod=apiMethod, apiPath=apiPath, apiParams=apiParams
        )
    return resp


def get_suspected_rogues(central) -> Optional[Dict]:
    """API call to Central to get a list of all suspected rogue APs

    Args:
        central (class): Central API object

    Returns:
        Optional[Dict]: dictionary of suspected rogue APs
    """
    apiPath = "/rapids/v1/suspect_aps"
    apiMethod = "GET"

    return central.command(apiMethod=apiMethod, apiPath=apiPath, apiParams=apiParams)


def find_ssids(fdata, _check_ssids):
    """Find SSIDs that match a string

    Args:
        fdata (_type_): list of broadcasting SSIDs
        _check_ssids (_type_): list of ssids names to check against

    Returns:
        _type_: a list of SSID that match the string
    """
    rogue_ssid_matches = []

    for ea in fdata:
        # If ssid key doesn't exist, add a blank entry
        ea["ssid"] = "" if "ssid" not in ea else ea["ssid"]
        rogue_ssid_matches.extend(
            ea
            for ea_ssid in _check_ssids
            if fuzz.partial_ratio(ea["ssid"].lower(), ea_ssid) > 80
        )

    return rogue_ssid_matches


def show_all_rogues(all_rapids_types, mail=None):
    """All SSIDs tyes that match Rogue SSIDs (suspected, rogue, etc)

    Args:
        all_rapids_types (_type_): show all types of rogue APs
        _check_ssids (_type_): Check against the SSIDs to find rogue APs based on check_ssids in .env.yaml
        mail (_type_, optional): send email? Defaults to None (no email).

    Returns:
        _type_: a report of rogue APs tyes based on SSIDs (suspected, rogue, etc)
    """
    if mail:
        return all_rapids_types

    len_all_rapids_types = len(all_rapids_types)

    table = Table(min_width=135, title=f"\n{len_all_rapids_types} Rogue Types Found")

    table.add_column("Type", justify="right", style="cyan")
    table.add_column("Rogue SSID", style="green")
    table.add_column("BSSID", style="yellow")
    table.add_column("Manufacture")
    table.add_column("Signal", justify="right", style="green")
    # table.add_column("Group")
    table.add_column("First Seen")
    table.add_column("Seen by")

    for ea in all_rapids_types:
        ssid = "" if "ssid" not in ea else ea["ssid"]
        dt_last_seen = pdl.parse(ea["last_seen"])  # type: ignore
        # group_name = ea.get('group_name')
        table.add_row(
            ea["classification"],
            ssid,
            ea["id"],
            ea["name"],
            str(ea["signal"]),
            dt_last_seen.to_cookie_string(),
            ea["last_det_device_name"],
        )  # type: ignore

    console = Console()
    console.print(table)


def show_rogue_ssids(all_rapids_types, _check_ssids, mail=None):
    """Only show SSIDs that match Rogue SSIDs

    Args:
        all_rapids_types (_type_): show all types of rogue APs
        _check_ssids (_type_): Check against the SSIDs to find rogue APs based on check_ssids in .env.yaml
        mail (_type_, optional): send email? Defaults to None (no email).

    Returns:
        _type_: a report of rogue APs based on SSIDs
    """
    matches = find_ssids(all_rapids_types, _check_ssids)

    if mail:
        return matches

    table = Table(min_width=135, title=f"\n{len(matches)} SSIDs Classified as Rogues")

    table.add_column("Type", justify="right", style="cyan")
    table.add_column("Rogue SSID", style="green")
    table.add_column("BSSID", style="yellow")
    table.add_column("Manufacture")
    table.add_column("Signal", justify="right", style="green")
    # table.add_column("Group")
    table.add_column("First Seen")
    table.add_column("Seen by")

    for ea in matches:
        ssid = "" if "ssid" not in ea else ea["ssid"]
        dt_last_seen = pdl.parse(ea["last_seen"])  # type: ignore
        # group_name = ea.get('group_name')
        table.add_row(
            ea["classification"],
            ssid,
            ea["id"],
            ea["name"],
            str(ea["signal"]),
            dt_last_seen.to_cookie_string(),
            ea["last_det_device_name"],
        )  # type: ignore

    console = Console()
    console.print(table)


def get_all_rogues(account):
    central = ArubaCentralBase(
        central_info=central_info[account], ssl_verify=ssl_verify, logger=logger
    )
    all_types = (
        get_rogues(central)["msg"]["rogue_aps"]
        + get_suspected_rogues(central)["msg"]["suspect_aps"]
    )  # type: ignore
    for ea in all_types:
        if "first_seen" in ea:
            ea["human_first_seen"] = pdl.parse(ea["first_seen"]).to_cookie_string()  # type: ignore

    return all_types


@app.command()
def email(account: str = typer.Argument("default", help="Email Report of Rogue APs")):
    """
    Email Report of Rogue APs
    """
    check_ssids = central_info[account]["check_ssids"]
    all_rapids_types = get_all_rogues(account)
    all_types = show_all_rogues(all_rapids_types, mail=True)
    rogues = show_rogue_ssids(all_rapids_types, check_ssids, mail=True)
    print(
        f"\nEmailing a report of [red]{len(all_types)}[/red] rogue APs to [blue underline]{central_info[account]['to_emails']}[/blue underline]"
    )  # type: ignore
    send_template_email(
        "rogues_found.html.jinja2",
        central_info[account],
        found=rogues,
        all_types=all_types,
        account=account,
    )


@app.command()
def slack(
    account: str = typer.Argument("default", help="Show table of Rogue APs"),
    rev: bool = typer.Option(1, help="Reverse sort order"),
):
    """
    Send table of Rogue APs to Slack
    """

    slack_url = central_info[account]["slack_url"]
    # check_ssids = central_info[account]['check_ssids']
    all_rapids_types = get_all_rogues(account)

    ignore_keys = [
        "acknowledged",
        "classification_method",
        "encryption",
        "mac_vendor",
        "first_det_device_name",
        "containment_status",
        "cust_id",
        "first_seen",
        "first_det_device",
        "last_det_device",
        "last_det_device_name",
        "human_first_seen",
        "overriden",
    ]
    for k in ignore_keys:
        for ea in all_rapids_types:
            if "last_seen" in ea:
                ea["human_last_seen"] = pdl.parse(ea["last_seen"]).to_cookie_string()
                del ea["last_seen"]
            if k in ea:
                del ea[k]

    # header = all_rapids_types[0].keys()
    header = ["Type", "BSSID", "Vendor Name", "Signal", "Seen by", "Last Seen"]

    rows = [x.values() for x in all_rapids_types]
    table = tabulate(rows, header)

    print("[bold green]Sending message to Slack...")
    uploader = SlackTableUploader(central_info[account]["slack_bot_token"])

    # Create ASCII table
    # table = uploader.create_ascii_table(data, headers)

    # Upload to Slack
    try:
        response = uploader.upload_table(
            table,
            channel=central_info[account]["slack_channel_id"],
            filename="rogue_data.txt",
            initial_comment="Rogue SSIDs:",
        )
        print("Table uploaded successfully!")
    except SlackApiError as e:
        print(f"Error uploading table: {e}")


@app.command()
def smtp(
    account: str = typer.Argument("default", help="Show table of Rogue APs"),
    rev: bool = typer.Option(1, help="Reverse sort order"),
):
    all_rapids_types = get_all_rogues(account)

    ignore_keys = [
        "acknowledged",
        "classification_method",
        "encryption",
        "mac_vendor",
        "first_det_device_name",
        "containment_status",
        "cust_id",
        "first_seen",
        "first_det_device",
        "last_det_device",
        "last_det_device_name",
        "human_first_seen",
        "overriden",
    ]
    for k in ignore_keys:
        for ea in all_rapids_types:
            if "last_seen" in ea:
                ea["human_last_seen"] = pdl.parse(ea["last_seen"]).to_cookie_string()
                del ea["last_seen"]
            if k in ea:
                del ea[k]

    # header = all_rapids_types[0].keys()
    header = ["Type", "BSSID", "Vendor Name", "Signal", "Seen by", "Last Seen"]

    rows = [x.values() for x in all_rapids_types]
    table = tabulate(rows, header)

    print("[bold green]Sending message via SMTP...")
    send_legacy_email(table, account=account)


@app.command()
def show(
    account: str = typer.Argument("default", help="Show table of Rogue APs"),
    rev: bool = typer.Option(1, help="Reverse sort order"),
    save: bool = typer.Option(0, help="Save to file"),
):
    """
    Show table of Rogue APs
    """
    check_ssids = central_info[account]["check_ssids"]
    all_rapids_types = get_all_rogues(account)

    if rev:
        show_rogue_ssids(all_rapids_types, check_ssids, mail=False)
        show_all_rogues(all_rapids_types, mail=False)
    else:
        show_all_rogues(all_rapids_types, mail=False)
        show_rogue_ssids(all_rapids_types, check_ssids, mail=False)

    if save:
        all_types = show_all_rogues(all_rapids_types, mail=True)
        rogues = show_rogue_ssids(all_rapids_types, check_ssids, mail=True)
        save_to_file(
            template="rogues_found.html.jinja2", rogues=rogues, found=all_types
        )


@app.command()
def tokens():
    """
    Show temp directory contents
    """
    current_path = Path.cwd()
    print(f"Current path: {current_path}")
    print(f"Temp path: {current_path}/temp\nDirectory List:")
    directory_path = Path("./temp")
    for file_path in directory_path.iterdir():
        if file_path.is_file():
            print(f"\t {file_path}")


def main(name: str):
    """
    This is not used
    """
    all_rapids_types = (
        get_rogues()["msg"]["rogue_aps"] + get_suspected_rogues()["msg"]["suspect_aps"]
    )  # type: ignore
    for ea in all_rapids_types:
        if "first_seen" in ea:
            ea["human_first_seen"] = pdl.parse(ea["first_seen"]).to_cookie_string()  # type: ignore

    all_types = show_all_rogues(all_rapids_types, mail=True)
    account = "default"
    check_ssids = central_info[account]["check_ssids"]

    rogues = show_rogue_ssids(all_rapids_types, check_ssids, mail=True)
    central = ArubaCentralBase(
        central_info=central_info[account], ssl_verify=ssl_verify
    )
    central.logger.setLevel(logging.ERROR)  # type: ignore

    send_template_email(
        "rogues_found.html.jinja2",
        central,
        found=rogues,
        all_types=all_types,
        account=account,
    )


if __name__ == "__main__":
    app()
