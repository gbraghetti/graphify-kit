import { total, type Item } from "./total";

interface ListaProps {
  itens: Item[];
}

export function Lista({ itens }: ListaProps) {
  return <p>Total: {total(itens)}</p>;
}
