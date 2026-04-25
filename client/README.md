# Delulu Clone API - Production Ready

An API to apply AI styles to images using Stable Diffusion Turbo. This version has been prepared for full production environments and includes a hardware-bound licensing system to prevent unauthorized copying.

## Features
- Fast Image-to-Image transformation using `stabilityai/sd-turbo`
- Hardware-bound license verification
- Production-ready Docker containerization (`Dockerfile` and `docker-compose.yml`)
- Gunicorn setup with Uvicorn workers
- Quick setup scripts for Windows and Linux/macOS

## Project Setup

### Development Setup (Local)
You can quickly set up the project on your local machine using the provided setup scripts. These scripts will create a Python virtual environment, install dependencies, and pre-download the AI model to save time on startup.

**For Windows:**
Double-click `setup.bat` or run it from the command line:
```cmd
setup.bat
```

**For Linux/macOS:**
Run the shell script:
```bash
./setup.sh
```

### Production Setup (Docker)
For full production, it is highly recommended to use Docker. We have provided a `Dockerfile` and a `docker-compose.yml`.

1. Make sure you have Docker and Docker Compose installed.
2. If you are using an NVIDIA GPU, ensure the NVIDIA Container Toolkit is installed and uncomment the `deploy` block in the `docker-compose.yml` file.
3. Build and run the container:
```bash
docker-compose up -d --build
```
This will run the application on port `8000`.

## Hardware-Bound Licensing
This software includes a strict license gate. The program will **refuse to start** unless a valid `license.key` file is present in the root directory. The license is bound to the exact hardware it was generated for (based on MAC address and system info).

### Generating a License
When a client runs the application for the first time without a license (or if you run `license_manager.py`), it will output a `Machine ID`.

1. Obtain the `Machine ID` from the client PC:
   ```bash
   python license_manager.py
   ```
2. On your admin machine, generate a valid license key using that Machine ID:
   ```bash
   python generate_license.py <MACHINE_ID>
   ```
   This will output a `license.key` file.
3. Send the `license.key` to the client and place it in the application's root directory (or mount it via Docker). The software will now run genuinely.

If a user copies the program folder to another PC, the Machine ID will change, the `license.key` will fail validation, and the program will crash on startup, catching the user and advising them to act genuinely.

## Configuration
Use the `.env` file to configure production settings. You can copy the `.env.example`:
```bash
cp .env.example .env
```
Available variables:
- `HOST`: The host to bind to (default: `0.0.0.0`)
- `PORT`: The port to run on (default: `8000`)
- `GUNICORN_WORKERS`: Number of workers (default: `1`. Keep low for AI models to save memory)
- `GUNICORN_TIMEOUT`: Worker timeout in seconds (default: `120`)
