# Kite AI Auto Bot

This is a Dockerized version of the Kite AI Auto Bot application.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier management)

## Setup

1. Make sure you have your `wallets.txt` and `proxies.txt` files ready in the project directory.

2. Using Docker Compose (Recommended):
```bash
# Build and start the container
docker-compose up --build

# To run in detached mode
docker-compose up -d

# To stop the container
docker-compose down
```

3. Using Docker directly:
```bash
# Build the Docker image
docker build -t kite-ai-bot .

# Run the container
docker run -it --rm -v $(pwd)/wallets.txt:/app/wallets.txt -v $(pwd)/proxies.txt:/app/proxies.txt kite-ai-bot
```

## File Structure

- `wallets.txt`: Contains wallet addresses (one per line)
- `proxies.txt`: Contains proxy configurations (one per line)
- `docker-compose.yml`: Docker Compose configuration file
- `Dockerfile`: Docker build instructions

## Notes

- The container will mount your local `wallets.txt` and `proxies.txt` files, so you can modify them without rebuilding the container.
- The application will run in interactive mode so you can see the output and interact with it.
- Using Docker Compose provides better container management and automatic restart capabilities.
- The container will automatically restart unless explicitly stopped.

## Docker Compose Features

- Automatic container restart on failure
- Proper volume mounting for configuration files
- Interactive mode support
- Isolated network for the container
- Easy to manage with simple commands

## Troubleshooting

If you encounter any issues:

1. Make sure your `wallets.txt` and `proxies.txt` files are properly formatted
2. Check if the files have the correct permissions
3. Ensure you have enough system resources allocated to Docker
4. Check Docker logs:
```bash
docker-compose logs
# or for specific service
docker-compose logs kite-ai-bot
```
