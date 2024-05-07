# Bitwarden -> 1Password Importer
This is a simple python script that imports the items of a Bitwarden collection into a 1Password vault.

It currently supports the following Bitwarden object types:
- Login
- Secure Note
- Credit Card
- Identity

## Requirements
- A recent version of Python 3 (tested with 3.12.3)
- The Python packages listed in `requirements.txt`
- The [Bitwarden CLI](https://bitwarden.com/help/cli/#download-and-install)
- The [1Password CLI](https://developer.1password.com/docs/cli/get-started/)

## Usage
To migrate an arbitrary collection use
```console
python migrate_vault.py BITWARDEN_COLLECTION 1PASSWORD_VAULT
``` 
where `BITWARDEN_COLLECTION` is the ID of the Bitwarden collection to read from and `1PASSWORD_VAULT` is the name or ID of the 1Password vault to import into.

For advanced options see `python migrate_vault.py --help`.

###  Importing your personal Vault
To import your personal Bitwarden vault into 1Password on macOS, you can use the `migrate_personal_vault.sh` command line script. It will install the necessary dependencies and run the migration script with the correct parameters. To use it, simply run:
```console
curl -L https://github.com/sdv-werbestudio/bitwarden-1password-importer/archive/main.zip -o importer.zip && unzip -qq importer.zip && chmod +x bitwarden-1password-importer-main/migrate_personal_vault.sh && ./bitwarden-1password-importer-main/migrate_personal_vault.sh && rm -rf importer.zip bitwarden-1password-importer-main
```

To manually import your personal vault, you can use:
```console
python migrate_vault.py null Employee
```