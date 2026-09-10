import type { SyntheticEvent } from 'react';

// Inline so it always renders: the backend returns cover_url = null when a book
// has no cover or when Filebase credentials are missing, and presigned URLs
// expire, so <img src={null}> and dead links both need a fallback.
export const COVER_PLACEHOLDER =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
       <rect width="200" height="300" fill="#e9edf3"/>
       <rect x="0" y="0" width="200" height="300" fill="none" stroke="#d7dce3" stroke-width="2"/>
       <text x="100" y="150" text-anchor="middle" font-family="system-ui, sans-serif"
             font-size="15" fill="#8a97a8">No cover</text>
     </svg>`
  );

/** Cover URL, or the placeholder when it is missing/blank. */
export function coverSrc(url?: string | null): string {
  return url && url.trim() ? url : COVER_PLACEHOLDER;
}

/** Swap in the placeholder when a cover URL fails to load (expired/404). */
export function onCoverError(e: SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget;
  if (!img.src.startsWith('data:')) {
    img.src = COVER_PLACEHOLDER;
  }
}
