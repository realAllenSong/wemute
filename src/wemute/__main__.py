import os
import sys


def _use_bundled_certificates() -> None:
    """HTTPS in the packaged app trusts the bundled certifi roots.

    The bundled OpenSSL otherwise looks for certificates where the build
    machine's Homebrew keeps them, which most Macs don't have: every model and
    component download would fail there.
    """
    if not getattr(sys, "frozen", False) or os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi

        os.environ["SSL_CERT_FILE"] = certifi.where()
    except Exception:  # noqa: BLE001 - fall back to macOS's own bundle
        if os.path.exists("/etc/ssl/cert.pem"):
            os.environ["SSL_CERT_FILE"] = "/etc/ssl/cert.pem"


_use_bundled_certificates()

from wemute.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
