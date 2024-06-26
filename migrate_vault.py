from typing import List, Dict, Any
import json
import subprocess
import os
from argparse import ArgumentParser, Namespace
from tqdm import tqdm


def parse_args() -> Namespace:
    """Parse command line arguments."""

    parser = ArgumentParser(
        prog="migrate_vault.py",
        description="Import the items of a Bitwarden collection into a 1Password vault.",
    )
    parser.add_argument("input_id", help="the ID of the Bitwarden collection to import")
    parser.add_argument(
        "account",
        help="the account shorthand, sign-in address, account ID, or user ID of the 1Password account to use",
    )
    parser.add_argument(
        "vault", help="the name or ID of the 1Password vault to import into"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not import the items, useful in combination with --dump",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="dump the imported items to JSON files in the data directory",
    )
    parser.add_argument(
        "--no-cleanup",
        dest="cleanup",
        action="store_false",
        help="do not clean up the data directory after importing",
    )

    return parser.parse_args()


def fetch_items(collection_id: str) -> List[Dict[str, Any]]:
    """Fetches all items within a collection using the Bitwarden CLI."""

    fetch_process = subprocess.Popen(
        ["bw", "list", "items", f"--collectionid={collection_id}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = fetch_process.communicate()

    if fetch_process.returncode != 0:
        print("ERROR: Failed to fetch items.")
        print(stderr)
        exit(1)

    return json.loads(stdout)


def translate(item: Dict[str, Any]) -> Dict[str, Any]:
    """Translates a single item from Bitwarden's format into 1Password's format."""

    if item["type"] == 1:
        translated_item = translate_login(item)
    elif item["type"] == 2:
        translated_item = translate_secure_note(item)
    elif item["type"] == 3:
        translated_item = translate_card(item)
    elif item["type"] == 4:
        translated_item = translate_identity(item)

    else:
        raise ValueError(f"Item type {item['type']} is not supported.")

    append_custom_fields(item, translated_item)

    return translated_item


def translate_login(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_login = {
        "title": item["name"],
        "category": "LOGIN",
        "fields": [
            {
                "id": "username",
                "type": "STRING",
                "purpose": "USERNAME",
                "label": "username",
                "value": item["login"]["username"],
            },
            {
                "id": "password",
                "type": "CONCEALED",
                "purpose": "PASSWORD",
                "label": "password",
                "value": item["login"]["password"],
            },
            {
                "id": "notesPlain",
                "type": "STRING",
                "purpose": "NOTES",
                "label": "notes",
                "value": item["notes"],
            },
        ],
        "urls": [{"href": uri["uri"]} for uri in item["login"]["uris"]],
    }

    if item["login"].get("totp"):
        translated_login["fields"].append(
            {
                "id": "totp",
                "type": "OTP",
                "value": f"otpauth://totp/{item['name']}:{item['login']['username']}?secret={item['login']['totp']}",
            }
        )

    return translated_login


def translate_secure_note(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_secure_note = {
        "title": item["name"],
        "category": "SECURE_NOTE",
        "fields": [
            {
                "id": "notesPlain",
                "type": "STRING",
                "purpose": "NOTES",
                "label": "Notes",
                "value": item["notes"],
            }
        ],
    }

    return translated_secure_note


def translate_card(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_card = {
        "title": item["name"],
        "category": "CREDIT_CARD",
        "fields": [
            {
                "id": "notesPlain",
                "type": "STRING",
                "purpose": "NOTES",
                "label": "notes",
                "value": item["notes"],
            },
            {
                "id": "cardholder",
                "type": "STRING",
                "label": "cardholder name",
                "value": item["card"]["cardholderName"],
            },
            {
                "id": "type",
                "type": "CREDIT_CARD_TYPE",
                "label": "type",
                "value": item["card"]["brand"],
            },
            {
                "id": "ccnum",
                "type": "CREDIT_CARD_NUMBER",
                "label": "number",
                "value": item["card"]["number"],
            },
            {
                "id": "cvv",
                "type": "CONCEALED",
                "label": "verification number",
                "value": item["card"]["code"],
            },
            {
                "id": "expiry",
                "type": "MONTH_YEAR",
                "label": "expiry date",
                "value": translate_month_year_field(
                    item["card"]["expMonth"], item["card"]["expYear"]
                ),
            },
        ],
    }

    return translated_card


def translate_identity(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_identity = {
        "title": item["name"],
        "category": "IDENTITY",
        "sections": [
            {"id": "address", "label": "Address"},
            {"id": "name", "label": "Identification"},
            {"id": "internet", "label": "Internet Details"},
        ],
        "fields": [
            {
                "id": "notesPlain",
                "type": "STRING",
                "purpose": "NOTES",
                "label": "notes",
                "value": item["notes"],
            },
            {
                "id": "title",
                "section": {"id": "name", "label": "Identification"},
                "type": "STRING",
                "label": "title",
                "value": item["identity"]["title"],
            },
            {
                "id": "firstname",
                "section": {"id": "name", "label": "Identification"},
                "type": "STRING",
                "label": "first name",
                "value": item["identity"]["firstName"],
            },
            {
                "id": "middlename",
                "section": {"id": "name", "label": "Identification"},
                "type": "STRING",
                "label": "middle name",
                "value": item["identity"]["middleName"],
            },
            {
                "id": "lastname",
                "section": {"id": "name", "label": "Identification"},
                "type": "STRING",
                "label": "last name",
                "value": item["identity"]["lastName"],
            },
            {
                "id": "company",
                "section": {"id": "name", "label": "Identification"},
                "type": "STRING",
                "label": "company",
                "value": item["identity"]["company"],
            },
            {
                "id": "address",
                "section": {"id": "address", "label": "Address"},
                "type": "STRING",
                "label": "address",
                "value": translate_address_field(item),
            },
            {
                "id": "phone",
                "section": {"id": "address", "label": "Address"},
                "type": "PHONE",
                "label": "phone",
                "value": item["identity"]["phone"],
            },
            {
                "id": "username",
                "section": {"id": "internet", "label": "Internet Details"},
                "type": "STRING",
                "label": "username",
                "value": item["identity"]["username"],
            },
            {
                "id": "email",
                "section": {"id": "internet", "label": "Internet Details"},
                "type": "STRING",
                "label": "email",
                "value": item["identity"]["email"],
            },
        ],
    }

    return translated_identity


def append_custom_fields(item: Dict[str, Any], translated_item: Dict[str, Any]) -> None:
    """Translates and appends custom fields to an item."""

    translated_fields = []

    for field in item.get("fields", []):
        if field["type"] == 3:
            continue  # skip "verknüpfte" fields

        translated_fields.append(
            {
                "section": {
                    "id": "custom_fields",
                },
                "type": "CONCEALED" if field["type"] == 1 else "STRING",
                "label": field["name"],
                "value": field["value"],
            }
        )

    if translated_fields:
        if "sections" not in translated_item:
            translated_item["sections"] = []
        translated_item["sections"].append(
            {"id": "custom_fields", "label": "Custom Fields"}
        )
        translated_item["fields"] += translated_fields


def translate_month_year_field(month, year) -> str:
    """Translate a month and year field into 1Password's format.

    Args:
        month: the number of the month
        year: the number of the year

    Returns:
        str: Format "YYYY/MM
    """

    if not month or not year:
        return ""

    month = str(month).zfill(2)
    year = str(year)
    if len(year) <= 2:
        year = f"20{year.zfill(2)}"
    elif len(year) != 4:
        raise ValueError(f"Invalid year: {year}")
    return f"{year}/{month}"


def translate_address_field(item: Dict[str, Any]) -> str:
    """Translate the address field of an identity item into 1Password's format."""
    lines = []
    if item["identity"]["address1"]:
        lines.append(item["identity"]["address1"])
    if item["identity"]["address2"]:
        lines.append(item["identity"]["address2"])
    if item["identity"]["address3"]:
        lines.append(item["identity"]["address3"])
    if item["identity"]["city"] or item["identity"]["postalCode"]:
        lines.append(f"{item['identity']['city']} {item['identity']['postalCode']}")
    if item["identity"]["state"] or item["identity"]["country"]:
        lines.append(f"{item['identity']['state']}, {item['identity']['country']}")

    return "\n".join(lines)


def dump_item(item: Dict[str, Any], filename: str) -> None:
    """Write an item to a JSON file."""

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as file:
        json.dump(item, file, indent=4)


def import_item(item: Dict[str, Any], vault: str) -> str:
    """Imports an item into 1Password."""

    item_json = json.dumps(item, indent=None)
    import_process = subprocess.Popen(
        [
            "op",
            "--account",
            args.account,
            "item",
            "create",
            "--vault",
            vault,
            "--format=json",
            "-",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = import_process.communicate(input=item_json)

    if import_process.returncode != 0:
        raise RuntimeError(stderr)

    return json.loads(stdout)["id"]


def import_attachments(attachments: List[Dict[str, Any]], item_id: str) -> None:
    """Fetches all attachments for the given item and imports them into 1Password."""

    for attachment in attachments:
        fetch_process = subprocess.Popen(
            [
                "bw",
                "get",
                "attachment",
                attachment["id"],
                f"--itemid={item['id']}",
                f"--output=data/attachments/{item_id}/{attachment['fileName']}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = fetch_process.communicate()
        if fetch_process.returncode != 0:
            raise RuntimeError(stderr)
        
        attach_process = subprocess.Popen(
            [
                "op",
                "--account",
                args.account,
                "item",
                "edit",
                item_id,
                f"[file]=data/attachments/{item_id}/{attachment['fileName']}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = attach_process.communicate()
        if attach_process.returncode != 0:
            raise RuntimeError(stderr)


def migrate_item(item: Dict[str, Any]) -> None:
    """Handles the migration of a single item."""

    # dump item to file in bitwarden format
    if args.dump:
        filename = "".join(c for c in item["name"] if c.isalnum() or c == " ").rstrip()
        dump_item(item, f"data/bitwarden_items/{filename}.json")

    # translate item to 1password format
    translated_item = translate(item)

    # dump item to file in 1password format
    if args.dump:
        dump_item(translated_item, f"data/1password_items/{filename}.json")

    # import item and its attachments into 1password
    if not args.dry_run:
        item_id = import_item(translated_item, args.vault)
        import_attachments(item.get("attachments", []), item_id)


if __name__ == "__main__":
    args = parse_args()

    print("Fetching items...")
    items = fetch_items(args.input_id)
    print(f"Found {len(items)} items.")

    print("\nImporting items...")
    while len(items) > 0:
        remaining_items = []
        for item in tqdm(items):
            try:
                migrate_item(item)

            except KeyError as e:
                print(f"ERROR: Item {item.get('name', '')} has no {e}.")
                print("Skipping this item.")
                continue
            except Exception as e:
                print(f"ERROR: Could not import item {item.get('name', '')} ({e}).")
                if input("\nShould this item be skipped? (y/n) ").lower() == "y":
                    print("Skipping this item.")
                    continue
                else:
                    print("Trying again later.")
                    remaining_items.append(item)

        if len(remaining_items) > 0:
            print(f"\n\nRetrying {len(remaining_items)} remaining items...")
        items = remaining_items

    if args.cleanup:
        print("\nCleaning up...")
        os.system("rm -rf data")

    print("\nDone.")
