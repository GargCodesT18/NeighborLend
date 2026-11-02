"""Copy legacy /uploads listing photos to Supabase without deleting source files.

The default mode is a read-only dry run. Use --apply to upload and update rows.
For APP_ENV=production, also pass --confirm-production-write after taking a
database backup and obtaining approval to modify that database.
"""

import argparse
import ipaddress
import mimetypes
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.database import SessionLocal
from app.models import ListingPhoto
from app.services import storage_service


def _is_private_or_local_host(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain", "0.0.0.0"} or host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
        return address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified
    except ValueError:
        return False


def _legacy_relative_path(url: str, configured_base_url: str) -> Path | None:
    try:
        parsed = urlsplit(url)
        if not parsed.path.startswith("/uploads/"):
            return None
        if parsed.hostname:
            configured_host = urlsplit(configured_base_url).hostname
            if not _is_private_or_local_host(parsed.hostname) and parsed.hostname != configured_host:
                return None
        relative = Path(unquote(parsed.path.removeprefix("/uploads/")))
        if relative.is_absolute() or ".." in relative.parts:
            return None
        return relative
    except (TypeError, ValueError):
        return None


def _find_source_file(relative_path: Path, upload_roots: list[Path]) -> Path | None:
    for root in upload_roots:
        resolved_root = root.resolve()
        candidate = (resolved_root / relative_path).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upload source files and update listing_photos.url. Without this flag, no writes occur.",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required with --apply when APP_ENV is production/prod.",
    )
    parser.add_argument(
        "--uploads-dir",
        type=Path,
        help="Override UPLOAD_DIR for locating existing local source images.",
    )
    args = parser.parse_args()

    settings = get_settings()
    production = settings.app_env.lower() in {"production", "prod"}
    if args.apply and production and not args.confirm_production_write:
        print("Refusing to write: production APP_ENV requires --confirm-production-write.", file=sys.stderr)
        return 2
    if args.apply and storage_service.supabase is None:
        print("Refusing to write: configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on the backend first.", file=sys.stderr)
        return 2

    upload_roots = [args.uploads_dir or Path(settings.upload_dir_abs)]
    project_uploads = Path(__file__).resolve().parents[2] / "uploads"
    if project_uploads not in upload_roots:
        upload_roots.append(project_uploads)

    db = SessionLocal()
    candidates = missing = skipped = migrated = failed = 0
    try:
        photos = db.query(ListingPhoto).order_by(ListingPhoto.id).all()
        for photo in photos:
            relative_path = _legacy_relative_path(photo.url, settings.public_base_url)
            if relative_path is None:
                skipped += 1
                continue

            candidates += 1
            source = _find_source_file(relative_path, upload_roots)
            if source is None:
                missing += 1
                continue

            object_path = f"legacy/{photo.listing_id}/{photo.id}{source.suffix.lower()}"
            if not args.apply:
                continue

            try:
                content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
                public_url = storage_service.save_upload_from_bytes(
                    source.read_bytes(),
                    source.name,
                    content_type,
                    "images",
                    require_supabase=True,
                    object_path=object_path,
                )
                photo.url = public_url
                db.commit()
                migrated += 1
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"FAILED listing photo {photo.id}: {type(exc).__name__}")
    finally:
        db.close()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(
        f"{mode}: bucket={storage_service.LISTING_PHOTOS_BUCKET}, "
        f"candidates={candidates}, migrated={migrated}, "
        f"missing_source={missing}, failed={failed}, skipped_nonlocal={skipped}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
