"""Connects the automated planter to Commune.

`bridge.py` runs on an always-on computer (a Raspberry Pi) as a mailbox: the planter posts readings to it over
Wi-Fi, and Commune collects them and leaves new settings whenever it's open. The planter also works with no
bridge at all: it logs to its SD card and has its own setup hotspot for a phone.
The format is in commune_offline_community_suite/docs/integrations/planter.md.
"""

from .link import Mailbox, package_from_report

__all__ = ["Mailbox", "package_from_report"]
