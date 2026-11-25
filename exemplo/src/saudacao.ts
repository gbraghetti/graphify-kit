import { Pessoa } from "./pessoa";

export function saudar(p: Pessoa): string {
  return `Oi, ${p.nome}`;
}
