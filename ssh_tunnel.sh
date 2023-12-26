#!/bin/bash
while true; do
    autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -R 6100:localhost:22 hanvir@101.50.2.29 -p 6100
    sleep 5
done
