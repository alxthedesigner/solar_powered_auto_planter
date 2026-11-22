# solar_powered_auto_planter

A solar-powered automated watering and monitoring project. A gravity-fed rainwater collector waters a standalone 2 ft × 6 ft planter. It's low-power and runs with no external water line, no mains electricity, and with or without Wi-Fi. Control it from a computer or a phone.

An automated planter that needs as little human help as possible. It is built from three separate parts, and each one can be swapped out on its own.

```
solar_powered_auto_planter/
  commune_offline_community_suite/   the hub: where all the data meets
  field_identifier/                  the scanner that identifies plants, animals, etc., and its link to Commune
  automated_planter_system/          the planter's control board: watering, vents, moisture and temperature sensors
```

## How the parts connect

```
 field_identifier ◀──▶ Commune drive ◀──▶ Commune app (Mac/PC) ◀── you: knowledge base, websites, settings
                      (the identifier's     │ planter data kept on this computer
                       storage: ZIMs,       ▲
                       finds, knowledge)    │ Wi-Fi bridge (Raspberry Pi) · SD card · phone page
                                     automated_planter (solar, runs on its own)
```

- **Commune** (`commune_offline_community_suite/`) holds everything: what the field identifier finds, the planter's readings (temperature, moisture and so on), and the knowledge base and websites you add yourself. It is the only part that knows about all the others.
- **Devices** (`field_identifier/`, `automated_planter_system/`) never call into each other or into Commune's code. The field identifier reads and writes files in its folder on the Commune drive. The planter stays home, so it reaches the Commune computer through a Wi-Fi bridge (a Raspberry Pi), its SD card, or its own phone page.
- **Any device can be replaced.** A different field identifier or planter works as long as it follows the same files. The specs live in Commune, under [commune_offline_community_suite/docs/integrations/](commune_offline_community_suite/docs/integrations/).

| Device | Folder on the drive | Spec | Status |
|---|---|---|---|
| Field identifier | `field-id/` | [field-identifier.md](commune_offline_community_suite/docs/integrations/field-identifier.md) | Commune side built; device client in [field_identifier/commune_link/](field_identifier/commune_link/) |
| Automated planter | none: kept on the Commune computer | [planter.md](commune_offline_community_suite/docs/integrations/planter.md) | Built: firmware, Raspberry Pi bridge, SD card and phone page in [automated_planter_system/](automated_planter_system/); Planter page in Commune |

## License

[Apache License 2.0](LICENSE): free for anyone to use, change and share, including commercially, with a patent grant from every contributor.
