/** Encode repo slug for URL path segments (owner/name → owner__name). */
export function encodeRepoId(repoId: string): string {
  return repoId.replace(/\//g, "__");
}

export function decodeRepoId(encoded: string): string {
  return encoded.replace(/__/g, "/");
}

export function repoIdFromSelection(owner: string, name: string): string {
  return `${owner}/${name}`;
}
