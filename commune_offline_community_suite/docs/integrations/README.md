# Connecting devices to Commune

Commune is the hub. Devices never import its code or call it over the network. Each device type gets its own folder in the drive's library folder (`OfflineLibrary/` or the package's name), and the device and Commune talk only through files there:

| Direction | File | Who writes it |
|---|---|---|
| Device → Commune | `<device-folder>/inbox/*.json` or `*.zip` | The device. Write `name.part` first, then rename it, so Commune never reads half a file. |
| Commune → device | `<device-folder>/device.json` (or similar) | Commune, whenever the drive is built or new data arrives |
| Commune's record | `<device-folder>/journal.json`, `imported/`, `rejected/` | Commune only |

Each format carries a version number (`communeFieldPackage: 1`, …), so a new device can be added, or an old one replaced, without changing the others.

## Devices

- **Field identifier**: `field-id/`. See [field-identifier.md](field-identifier.md). The reference device client is in [field_identifier/commune_link/](../../../field_identifier/commune_link/).
- **Automated planter**: see [planter.md](planter.md). It's the exception: its data is kept on the Commune computer, not on the drive. It reaches Commune through a Wi-Fi bridge (a Raspberry Pi mailbox that Commune syncs with), its SD card, or its own phone setup page. The firmware and the bridge are in [automated_planter_system/](../../../automated_planter_system/).
