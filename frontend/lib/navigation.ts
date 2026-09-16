/**
 * Navigate to an application route without letting a malformed deployment
 * base path turn `/route` into the protocol-relative URL `//route`.
 */
export function navigateWithinOrigin(path: `/${string}`, replace = false): void {
  const url = new URL(path, window.location.origin);

  if (url.origin !== window.location.origin) {
    throw new Error("Refusing to navigate outside the application origin");
  }

  if (replace) {
    window.location.replace(url.href);
    return;
  }

  window.location.assign(url.href);
}
