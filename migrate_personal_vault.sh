#!/bin/bash
# This script installs all necessary dependencies and runs the migrate_vault.py script on macOS.

echo "Dieses Skript importiert deine Passwörter, Notizen, etc. aus deinem Bitwarden-Tresor in deinen perönlichen 1Password-Vault."
read -p "Drücke Enter, um fortzufahren..."

# Install Homebrew if not already installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. Installing Homebrew..."
    read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Update Homebrew
echo "Updating Homebrew..."
read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
brew update

# Install Dependencies
echo "Installing Python, Bitwarden CLI, and 1Password CLI..."
read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
brew install python bitwarden-cli 1password-cli

# Install python dependencies
echo "Installing Python dependencies..."
read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# Run Python script
echo "Running migration script..."
read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
python3 migrate_vault.py --dry-run null Employee

echo "Script execution completed."
read -p "Drücke Enter, um fortzufahren..." # TODO: Remove this line
