import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/** Same rule as repo.NAME_RE on the backend: letters (incl. Chinese), digits, _ and -. */
export const NAME_RE = /^[\p{L}\p{N}_-]{1,40}$/u;
