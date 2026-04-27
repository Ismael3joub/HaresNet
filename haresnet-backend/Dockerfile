FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    hostapd \
    dnsmasq \
    nftables \
    iproute2 \
    net-tools \
    wpasupplicant \
    wireless-tools \
    iw \
    iptables \
    procps \
    kmod \
    tzdata \
    isc-dhcp-client \
    conntrack \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /var/lib/misc /etc/hostapd /var/log /etc/wpa_supplicant

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose API port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PORT=5000

ENTRYPOINT ["/app/entrypoint.sh"]

