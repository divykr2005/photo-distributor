#!/bin/bash
# Phase 2: Edge Hardening for Oracle Cloud (Ubuntu)
# Oracle's Ubuntu images ship with iptables rules that drop everything except 22, in addition to the VCN security list.
# Let's Encrypt HTTP-01 will fail silently until you fix both.

echo "Adding iptables rules for port 80 and 443..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
echo "Done! Make sure you also update your Oracle VCN Security Lists."
