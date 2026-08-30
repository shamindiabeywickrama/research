"""
Wi-Fi Network Device Monitor
-----------------------------
Local network device detection for library occupancy simulation.
Scans the configured subnet to detect active devices and excludes
the monitoring device and gateway from the count.

Designed for Windows compatibility using ping and ARP table.
"""

import os
import subprocess
import threading
import time
import ipaddress
from datetime import datetime
from typing import Set, Dict, List, Optional
from collections import deque


class WiFiMonitor:
    """Monitor local network for connected devices."""

    def __init__(
        self,
        interface_ip: str,
        gateway: str,
        subnet: str,
        exclude_ips: List[str],
        scan_interval: int = 3,
        baseline: int = 0,
    ):
        self.interface_ip = interface_ip
        self.gateway = gateway
        self.subnet = subnet
        self.exclude_ips = set(exclude_ips)
        self.scan_interval = scan_interval
        self.baseline = baseline

        # State
        self.enabled = False
        self.detected_devices: Set[str] = set()
        self.previous_devices: Set[str] = set()
        self.last_scan: Optional[datetime] = None
        self.status = "idle"
        self.error_message: Optional[str] = None

        # Event tracking (keep last 10 events)
        self.events: deque = deque(maxlen=10)

        # Background thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # WebSocket callback
        self._websocket_callback = None

    def set_websocket_callback(self, callback):
        """Set callback function for WebSocket updates."""
        self._websocket_callback = callback

    def start(self):
        """Start the background monitoring thread."""
        if self._thread and self._thread.is_alive():
            return

        self.enabled = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background monitoring thread."""
        self.enabled = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        """Main monitoring loop running in background thread."""
        while not self._stop_event.is_set():
            try:
                self._scan_network()
            except Exception as e:
                with self._lock:
                    self.status = "error"
                    self.error_message = str(e)
                print(f"[WiFi Monitor] Error: {e}")

            self._stop_event.wait(self.scan_interval)

    def _scan_network(self):
        """Scan the subnet for active devices."""
        with self._lock:
            self.previous_devices = self.detected_devices.copy()

        try:
            # Get active devices from ARP table and ping scan
            active_devices = self._get_active_devices()

            # Remove excluded IPs
            detected = active_devices - self.exclude_ips

            with self._lock:
                self.detected_devices = detected
                self.last_scan = datetime.now()
                self.status = "active"
                self.error_message = None

                new_devices = detected - self.previous_devices
                disconnected_devices = self.previous_devices - detected

                for _device in new_devices:
                    self._add_event("DEVICE_CONNECTED", 1)
                for _device in disconnected_devices:
                    self._add_event("DEVICE_DISCONNECTED", -1)

                should_notify = bool(new_devices or disconnected_devices)

            # Call get_status() outside the lock to avoid deadlock
            if should_notify and self._websocket_callback:
                self._websocket_callback(self.get_status())

        except Exception as e:
            with self._lock:
                self.status = "error"
                self.error_message = str(e)
            raise

    def _get_active_devices(self) -> Set[str]:
        """Get active devices using ARP table and ping."""
        active = set()

        # Method 1: Read ARP table (Windows)
        try:
            arp_devices = self._get_arp_devices()
            active.update(arp_devices)
        except Exception as e:
            print(f"[WiFi Monitor] ARP scan failed: {e}")

        # Method 2: Ping scan (lightweight)
        try:
            ping_devices = self._ping_scan()
            active.update(ping_devices)
        except Exception as e:
            print(f"[WiFi Monitor] Ping scan failed: {e}")

        return active

    def _get_arp_devices(self) -> Set[str]:
        """Read Windows ARP table to get active devices."""
        try:
            # Run arp -a command
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            if result.returncode != 0:
                return set()

            # Parse ARP output
            devices = set()
            for line in result.stdout.splitlines():
                # ARP output format: "  172.20.10.1           00-11-22-33-44-55     dynamic"
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    try:
                        # Validate IP address
                        ipaddress.ip_address(ip)
                        # Check if IP is in our subnet
                        if self._ip_in_subnet(ip):
                            devices.add(ip)
                    except ValueError:
                        continue

            return devices
        except subprocess.TimeoutExpired:
            return set()
        except Exception:
            return set()

    def _ping_scan(self) -> Set[str]:
        """Lightweight ping scan of the subnet."""
        devices = set()

        try:
            network = ipaddress.ip_network(self.subnet, strict=False)
            usable_hosts = list(network.hosts())

            # Limit scan to avoid long delays
            # For /28 subnet, max 14 hosts, so we can scan all
            # For larger subnets, we'd need to limit this

            for ip in usable_hosts:
                ip_str = str(ip)
                if ip_str in self.exclude_ips:
                    continue

                # Quick ping with timeout
                if self._ping_host(ip_str):
                    devices.add(ip_str)

        except Exception as e:
            print(f"[WiFi Monitor] Ping scan error: {e}")

        return devices

    def _ping_host(self, ip: str) -> bool:
        """Ping a single host to check if it's reachable."""
        try:
            # Windows ping: -n 1 (one ping), -w 500 (500ms timeout)
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "500", ip],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _ip_in_subnet(self, ip: str) -> bool:
        """Check if an IP is in the configured subnet."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            network = ipaddress.ip_network(self.subnet, strict=False)
            return ip_obj in network
        except Exception:
            return False

    def _add_event(self, event_type: str, count_change: int):
        """Add an event to the event log."""
        event = {
            "event": event_type,
            "count_change": count_change,
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)

    def get_status(self) -> Dict:
        """Get current monitor status."""
        with self._lock:
            detected_count = len(self.detected_devices)
            occupancy_count = self.baseline + detected_count

            return {
                "enabled": self.enabled,
                "mode": "wifi_simulation",
                "network": self.subnet,
                "gateway": self.gateway,
                "local_device": self.interface_ip,
                "detected_devices": detected_count,
                "occupancy_count": occupancy_count,
                "baseline": self.baseline,
                "last_scan": self.last_scan.isoformat() if self.last_scan else None,
                "status": self.status,
                "error_message": self.error_message,
                "excluded_count": len(self.exclude_ips),
            }

    def get_events(self) -> List[Dict]:
        """Get recent device events."""
        with self._lock:
            return list(self.events)

    def get_occupancy_count(self) -> int:
        """Get current occupancy count (baseline + detected devices)."""
        with self._lock:
            return self.baseline + len(self.detected_devices)


def create_wifi_monitor() -> Optional[WiFiMonitor]:
    """Create WiFi monitor from environment variables."""
    wifi_enabled = os.getenv("WIFI_SIMULATION_ENABLED", "false").lower() == "true"

    if not wifi_enabled:
        return None

    interface_ip = os.getenv("WIFI_INTERFACE_IP", "")
    gateway = os.getenv("WIFI_GATEWAY", "")
    subnet = os.getenv("WIFI_SUBNET", "")
    scan_interval = int(os.getenv("WIFI_SCAN_INTERVAL", "3"))
    baseline = int(os.getenv("WIFI_OCCUPANCY_BASELINE", "0"))
    exclude_ips_str = os.getenv("WIFI_EXCLUDE_IPS", "")

    if not interface_ip or not gateway or not subnet:
        print("[WiFi Monitor] Missing required configuration")
        return None

    exclude_ips = [ip.strip() for ip in exclude_ips_str.split(",") if ip.strip()]

    monitor = WiFiMonitor(
        interface_ip=interface_ip,
        gateway=gateway,
        subnet=subnet,
        exclude_ips=exclude_ips,
        scan_interval=scan_interval,
        baseline=baseline,
    )

    return monitor
