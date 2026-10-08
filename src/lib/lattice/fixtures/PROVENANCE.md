# Fixture provenance

The original CSV is unchanged. The two migration JSON files record expectations
from the pinned source, independently of the renamed engine. Source commits,
runtime versions, parameters, generation commands, and SHA-256 fingerprints
are recorded in [ORIGINS.md](../../../../ORIGINS.md).

These files are regression artifacts. They are not external performance results.
The Python hashes are a historical runtime snapshot. Current Python migration
tests compare the pinned original and migrated code exactly within the same
runtime and report any differences from that snapshot. The JSON remains unchanged.
