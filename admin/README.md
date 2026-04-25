# Delulu Admin Tools

This folder contains tools for generating hardware-bound license keys for the Delulu Clone API.

## Setup
```bash
pip install -r requirements.txt
```

## Usage
1. Get the `MACHINE_ID` from the client.
2. Run the generator:
```bash
python generate_license.py <MACHINE_ID>
```
3. Send the resulting `license.key` file to the client.
