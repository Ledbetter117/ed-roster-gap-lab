# Security and private reports

Report a suspected vulnerability through [GitHub private vulnerability reporting](https://github.com/Ledbetter117/ed-roster-gap-lab/security/advisories/new). Include the affected version, a minimal synthetic example, expected behavior and actual behavior. Do not attach credentials, private rosters or personal records. Please do not disclose sensitive details in a public issue.

## Supported use

This is a local Python workbench for synthetic data. It has no hosted service, authentication system, model endpoint or clinical deployment. Core commands use the standard library and need no network access or credentials. The optional PDF renderer requires Python 3.11+ and has a separately pinned stack in `paper/requirements.txt`; this includes Pillow 13.0.0 to avoid the advisories reported for the previously unconstrained older Pillow dependency. Core commands still support Python 3.10+.

The current branch receives security fixes. Earlier tags remain immutable evidence snapshots and may contain defects corrected later. Read the [security audit and corrections](docs/SECURITY-AUDIT.md) before reusing an older release.

## Boundaries

- Run only source you trust. The release manifest detects accidental changes relative to that manifest; it is not a signature, malware scanner or defense against someone who can edit both files and hashes.
- Use synthetic inputs only. Token checks do not anonymize records or detect all sensitive text. Keep genuine future study labels and any private material outside the repository and public artifacts.
- Measurement set IDs are validated as tokens. Internal set paths must stay inside the set and must not be symlinks or supported Windows junctions. A label sheet is issued once; existing sheet files and standalone detector CLI `--out` files are refused. Before a sheet is issued, `seal` may intentionally replace its internal detector JSON. Internal JSON writes replace directory entries instead of truncating a hard-linked file.
- Use one operator/process per study set. These checks do not defend against a hostile process that can concurrently replace the same user's directories. Sealed files are readable, not encrypted; blinding is a study procedure, and a rater declaration does not authenticate a person.
- Large or deeply nested inputs can consume local memory or processing time. The CLI is not a sandbox for arbitrary hostile files. The optional publication renderer is for reviewed local source and evidence, not an upload service.
- CI uses synthetic examples and minimal read permissions. Tests and a clean secret scan do not establish absence of every vulnerability, confidentiality leak or scientific error.

The human agreement study remains unfinished. A security correction does not establish clinical validity or complete the original research endpoint.
