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

    items = subprocess.check_output(
        ["bw", "list", "items", f"--collectionid={collection_id}"]
    )
    items = json.loads(items)
    return items


def translate(item: Dict[str, Any]) -> Dict[str, Any]:
    """Translates a single item from Bitwarden's format into 1Password's format."""

    if item["type"] == 1:
        return translate_login(item)
    elif item["type"] == 2:
        return translate_secure_note(item)
    elif item["type"] == 3:
        return translate_card(item)
    elif item["type"] == 4:
        return translate_identity(item)
    else:
        raise ValueError(f"Item type {item['type']} is not supported.")


def translate_login(item: Dict[str, Any]) -> Dict[str, Any]:
    fields = [
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
    ]

    if item["login"].get("totp"):
        fields.append(
            {
                "id": "totp",
                "type": "OTP",
                "value": f"otpauth://totp/{item['name']}:{item["login"]["username"]}?secret={item["login"]["totp"]}",
            }
        )

    fields += translate_custom_fields(item.get("fields", []))

    translated_login = {
        "title": item["name"],
        "category": "LOGIN",
        "sections": [
            {"id": "custom_fields", "label": "Custom Fields"},
        ]
        if item.get("fields")
        else [],
        "fields": fields,
        "urls": [{"href": uri["uri"]} for uri in item["login"]["uris"]],
    }

    return translated_login


def translate_secure_note(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_secure_note = {}
    return translated_secure_note


def translate_card(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_card = {}
    return translated_card


def translate_identity(item: Dict[str, Any]) -> Dict[str, Any]:
    translated_identity = {}
    return translated_identity


def translate_custom_fields(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    translated_fields = []

    for field in fields:
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

    return translated_fields


def dump_item(item: Dict[str, Any], filename: str) -> None:
    """Write an item to a JSON file."""

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as file:
        json.dump(item, file, indent=4)


def import_item(item: Dict[str, Any], vault: str) -> str:
    """Imports an item into 1Password."""

    item_json = json.dumps(item, indent=None)
    stdout, stderr = subprocess.Popen(
        ["op", "item", "create", "--vault", vault, "--format=json", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).communicate(input=item_json)

    if stderr:
        raise RuntimeError(stderr)

    return json.loads(stdout)["id"]


def import_attachments(attachments: List[Dict[str, Any]], item_id: str) -> None:
    """Fetches all attachments for the given item and imports them into 1Password."""

    for attachment in attachments:
        subprocess.run(
            [
                "bw",
                "get",
                "attachment",
                attachment["id"],
                f"--itemid={item["id"]}",
                f"--output=data/attachments/{item_id}/{attachment["fileName"]}",
            ],
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "op",
                "item",
                "edit",
                item_id,
                f"[file]=data/attachments/{item_id}/{attachment["fileName"]}",
            ],
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    args = parse_args()

    print("Fetching items...")
    items = fetch_items(args.input_id)
    print(f"Found {len(items)} items.")

    print("Importing items...")
    for item in tqdm(items):
        # dump item to file in bitwarden format
        if args.dump:
            filename = "".join(
                c for c in item["name"] if c.isalnum() or c == " "
            ).rstrip()
            dump_item(item, f"data/bitwarden_items/{filename}.json")

        # translate item to 1password format
        try:
            translated_item = translate(item)
        except KeyError as e:
            print(f"ERROR: Item {item.get('name', '')} has no {e}. Skipping.")
            continue

        # dump item to file in 1password format
        if args.dump:
            dump_item(translated_item, f"data/1password_items/{filename}.json")

        # import item and its attachments into 1password
        if not args.dry_run:
            try:
                item_id = import_item(translated_item, args.vault)
            except RuntimeError as e:
                print(
                    f"ERROR: Could not import item {item.get('name', '')} ({e}). Skipping."
                )
                continue
            import_attachments(item.get("attachments", []), item_id)

    if args.cleanup:
        print("Cleaning up...")
        os.system("rm -rf data")

    print("\nDone.")
