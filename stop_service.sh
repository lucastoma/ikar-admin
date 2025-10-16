#!/bin/bash

# Zatrzymaj usługę ikar-admin
echo "Zatrzymuję usługę ikar-admin..."
sudo systemctl stop ikar-admin.service

# Zablokuj automatyczne restartowanie
echo "Wyłączam automatyczne uruchamianie..."
sudo systemctl disable ikar-admin.service

# Zatrzymaj daemon jeśli jest jeszcze aktywny
sudo systemctl daemon-reload

# Pokaż status
echo "Status usługi:"
sudo systemctl status ikar-admin.service --no-pager

echo "Usługa ikar-admin została zatrzymana i wyłączona."