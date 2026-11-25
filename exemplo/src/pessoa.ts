import { saudar } from "./saudacao";

export interface Pessoa {
  nome: string;
}

export const boasVindas = (p: Pessoa) => saudar(p);
