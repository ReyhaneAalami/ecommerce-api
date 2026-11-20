# Phase 3 — PostgreSQL Product Search

## Included
- Public product search by name and description.
- Multi-word search: every word must match either the product name or description.
- Filters: category, vendor, minimum/maximum price, and stock availability.
- Sorting: newest, price ascending, price descending, and name ascending.
- Pagination metadata (`items`, `total`, `skip`, `limit`).
- PostgreSQL `pg_trgm` GIN indexes for substring `ILIKE` queries.
- Automated API tests.

## Apply
1. Make sure the project is on the expected branch and has no uncommitted changes you need to preserve.
2. Extract this archive into a separate folder, for example `C:\\Users\\iLap\\phase3_package` (do not extract over the project files yet).
3. Open PowerShell, change to the project root `C:\\Users\\iLap\\ecommerce-api`, then run `& 'C:\\Users\\iLap\\phase3_package\\APPLY_PHASE3.ps1'` (adjust the package path if you chose another folder).
4. Run `uv run alembic upgrade head`.
5. Run `uv run pytest -v`.

The apply script creates timestamped backups before replacing files. It locates the Alembic versions directory by finding the existing `7e4c9b2a1d60` migration, then copies the new migration into that directory.

## API

`GET /api/v1/products/search`

Parameters:
- `q`: optional text query, up to 200 characters.
- `category_id`: optional positive category ID.
- `vendor_id`: optional positive vendor ID.
- `min_price`, `max_price`: optional price bounds in integer rial.
- `in_stock`: optional boolean.
- `sort_by`: `newest` (default), `price_asc`, `price_desc`, `name_asc`.
- `skip`: zero-based offset (default 0).
- `limit`: page size (default 20, maximum 100).

Example:
`GET /api/v1/products/search?q=phone&category_id=2&min_price=100000&max_price=900000&in_stock=true&sort_by=price_asc&skip=0&limit=20`

The existing `GET /api/v1/products` endpoint remains available and backward compatible.

## Notes
- Prices are integer rial, matching the current database model.
- Search uses PostgreSQL `ILIKE`; English case matching is case-insensitive. Persian text is matched as stored (Arabic and Persian code-point variants such as ي/ی are not automatically transliterated).
- Popularity/best-selling sorting is intentionally excluded until a trustworthy product sales metric is defined.
- The `pg_trgm` extension is not removed on downgrade because it may be used by other indexes.
