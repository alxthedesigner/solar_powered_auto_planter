# Field identifier

The handheld scanner with five identifiers: plants and fungi, animals and bugs, languages, tech (hardware and software), and first aid. This folder is the device side: the code that connects the scanning hardware to Commune. Commune's side (importing finds, the Field identification page, the knowledge base) lives in `commune_offline_community_suite/`.

```
field_identifier/
  commune_link/     reads what Commune left on the drive, and writes field packages into its inbox
```

Hardware drivers and identification models will go next to `commune_link/` when they exist. Keep them apart from it, so the link to Commune stays the same whatever hardware is used.

## Using `commune_link`

It uses only the Python standard library.

```python
from commune_link import CommuneDrive, FieldPackage

drive = CommuneDrive.find("/Volumes/MY_DRIVE")     # finds the library folder on the drive
drive.sources("plant")                             # ZIM files to search for plants
drive.knowledge()                                  # the person's own identifications: search these too
drive.confidence_to_identify()                     # 0.8: below this, a find goes to "Needs identification"

pkg = FieldPackage("FI-0001", firmware="0.2.0", since=drive.last_upload_created())
pkg.add("plant", name="Common yarrow", scientific="Achillea millefolium", confidence=0.94,
        photo="captures/0001.jpg", details={"watering": "Low"},
        quotes=[{"text": "…copied word for word…", "library": "wikipedia_en_all", "path": "Achillea_millefolium"}])
drive.send(pkg)                                    # field-id/inbox/<id>.zip; Commune imports it
```

The full format, including every category's `details`, is in [field-identifier.md](../commune_offline_community_suite/docs/integrations/field-identifier.md). Any other identifier that writes the same files works with Commune too.
