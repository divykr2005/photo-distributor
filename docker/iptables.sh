#!/bin/bash
# docker/iptables.sh
# Script to open ports 80 and 443 on Ubuntu images

echo "Opening ports 80 and 443..."
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save iptables rules so they persist across reboots
if command -v netfilter-persistent &> /dev/null; then
    sudo netfilter-persistent save
elif command -v iptables-save &> /dev/null; then
    sudo iptables-save | sudo tee /etc/iptables/rules.v4 > /dev/null
fi

echo "Ports 80 and 443 are now open."
