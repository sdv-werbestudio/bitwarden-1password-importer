#!/bin/bash
# This script installs all necessary dependencies and runs the migrate_vault.py script on macOS.

clear
echo ""
echo "Dieses Skript importiert deine Passwörter, Notizen, etc. aus deinem Bitwarden-Tresor in deinen perönlichen 1Password-Vault."
echo ""
read -p "Drücke Enter, um fortzufahren..."

clear
echo ""
echo "Das Skript wird nun alles für den Import vorbereiten. Dies kann einige Zeit dauern."
sleep 5
echo ""

# Install Homebrew if not already installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew update

# Install Dependencies
brew install python bitwarden-cli 1password-cli

# Install python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# Authenticate Bitwarden
if ! bw login --check; then
    clear
    echo ""
    echo "Bitte authentifiziere dich bei Bitwarden:"
    echo ""
    echo "Hinweis: Um deine client_id und client_secret zu finden, gehe auf https://vault.bitwarden.com/#/settings/security/security-keys und klicke unten auf 'API-Schlüssel anzeigen'."
    echo ""
    until bw login --apikey; do
        echo ""
    done
    export BW_SESSION=""
fi
if ! bw unlock --check; then
    clear
    echo ""
    echo "Bitte entsperre deinen Bitwarden-Tresor:"
    until export BW_SESSION=$(bw unlock --raw); do
        echo ""
    done
fi

# Authenticate 1Password
until [[ $(op account list | wc -l) -ge 1 ]]; do
    clear
    echo ""
    echo "Bitte aktiviere die 1Password-CLI integration:"
    echo ""
    echo "  1. Öffne die 1Password-App"
    echo "  2. Klicke oben links auf das Account-Menü"
    echo "  3. Gehe zu 'Einstellungen' > 'Entwickler'"
    echo "  4. Setze den Haken bei 'In 1Password-CLI integrieren'"
    echo ""
    read -p "Drücke Enter, wenn du fertig bist..."
done
clear
if [[ $(op account list | wc -l) -ge 2 ]]; then
    echo ""
    echo "Bitte wähle, welcher 1Password-Account verwendet werden soll:"
    echo ""
    op account list
    echo ""
    echo "Gib dazu die in der Spalte 'ID' stehende Nummer des Accounts ein."
    read -p "USER ID: " ACCOUNT_ID
else
    ACCOUNT_ID=$(op account list | tail -n 1 | awk '{print $3}')
fi

# Run Python script
clear
echo ""
if ! python3 migrate_vault.py --dry-run null $ACCOUNT_ID Employee; then
    echo ""
    echo "Es ist ein Fehler Aufgetreten! Bitte kontaktiere einen Administrator."
    exit 1
fi

echo ""
echo "Der Import wurde erfolgreich abgeschlossen!"

# Clean up
bw lock
deactivate
rm -rf .venv
