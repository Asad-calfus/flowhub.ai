// Anonymous, no-login workspace scoping - an opaque id stored in the browser, sent as
// X-Workspace-Id on every API call (see lib/api.ts). The backend defaults to "demo"
// when the header is absent, so this file is the only thing that decides which
// workspace a given browser is looking at.

const STORAGE_KEY = "flowhub_workspace_id";
export const DEMO_WORKSPACE_ID = "demo";

export function getStoredWorkspaceId(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // localStorage unavailable (SSR, privacy mode, opaque test origin)
  }
}

export function setWorkspaceId(id: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // localStorage unavailable - workspace just won't persist across reloads
  }
}

export function chooseDemoWorkspace(): void {
  setWorkspaceId(DEMO_WORKSPACE_ID);
}

export function startNewWorkspace(): string {
  const id = crypto.randomUUID();
  setWorkspaceId(id);
  return id;
}

export function clearWorkspace(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage unavailable
  }
}

export function isDemoWorkspace(id: string | null): boolean {
  return id === DEMO_WORKSPACE_ID;
}
