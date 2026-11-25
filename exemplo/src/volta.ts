import { ida } from "./ida";

export function volta(n: number): number {
  return n <= 0 ? 0 : ida(n - 1);
}
