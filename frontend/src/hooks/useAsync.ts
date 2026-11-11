import { useEffect, useState, type DependencyList } from "react";

/** Runs an async loader and tracks its result. Re-runs when deps change. */
export function useAsync<T>(load: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    load().then(
      (d) => {
        if (!cancelled) setData(d);
      },
      (e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e : new Error(String(e)));
      },
    );
    return () => {
      cancelled = true;
    };
    // The caller controls re-runs through deps.
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, error, loading: data === undefined && error === undefined };
}
