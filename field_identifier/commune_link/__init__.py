"""Talks to a Commune drive from a field identifier.

The field identifier never calls the Commune app directly. It only reads and writes files in the drive's library
folder, so it works with the app closed, on any computer, and any identifier that follows the same files can
replace this one:

    <library>/field-id/device.json      written by Commune: which libraries to search, the confidence threshold,
                                        and when the last upload arrived
    <library>/field-id/knowledge.json   written by Commune: finds the person identified themselves (search these too)
    <library>/field-id/inbox/           the device drops one field package here per upload; Commune imports it

The format is in commune_offline_community_suite/docs/integrations/field-identifier.md.
"""

from .link import CommuneDrive, FieldPackage, find_library, CATEGORIES

__all__ = ["CommuneDrive", "FieldPackage", "find_library", "CATEGORIES"]
