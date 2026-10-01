/** Calls `fn` at most every `ms`, always delivering the latest arguments */
export function throttle<A extends unknown[]>(fn: (...args: A) => void, ms: number): (...args: A) => void {
  let last = 0;
  let timer: number | undefined;
  let pending: A | undefined;
  return (...args: A) => {
    pending = args;
    const wait = last + ms - Date.now();
    if (wait <= 0) {
      last = Date.now();
      fn(...args);
    } else if (timer === undefined) {
      timer = window.setTimeout(() => {
        timer = undefined;
        last = Date.now();
        if (pending) fn(...pending);
      }, wait);
    }
  };
}
