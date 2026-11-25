import { volta } from "./volta";

export function ida(n: number): number {
  return n <= 0 ? 0 : volta(n - 1);
}
