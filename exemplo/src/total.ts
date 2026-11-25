export interface Item {
  nome: string;
  centavos: number;
}

export function total(itens: Item[]): number {
  return itens.reduce((soma, item) => soma + item.centavos, 0);
}
