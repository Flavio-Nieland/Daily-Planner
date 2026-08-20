import { strict as assert } from "node:assert";
import { test } from "node:test";

import { aplicar, valido } from "./merge.js";

test("recusa seção que não existe", () => {
  assert.equal(valido({ secao: "cargas", chave: "2026-08-19", valor: 1 }), false);
});

test("recusa chave vazia, gigante ou valor ausente", () => {
  assert.equal(valido({ secao: "peso", chave: "", valor: 1 }), false);
  assert.equal(valido({ secao: "peso", chave: "x".repeat(65), valor: 1 }), false);
  assert.equal(valido({ secao: "peso", chave: "2026-08-19" }), false);
  assert.equal(valido(null), false);
});

test("aceita um registro de peso", () => {
  assert.equal(valido({ secao: "peso", chave: "2026-08-19", valor: 78.4 }), true);
});

test("dois registros no mesmo dia deixam o último", () => {
  let estado = {};
  estado = aplicar(estado, { secao: "peso", chave: "2026-08-19", valor: 78.4 }, "t1");
  estado = aplicar(estado, { secao: "peso", chave: "2026-08-19", valor: 78.1 }, "t2");
  assert.deepEqual(estado.peso, { "2026-08-19": 78.1 });
  assert.equal(estado.atualizado_em, "t2");
});

test("dias diferentes convivem e o que já existia não se perde", () => {
  let estado = { peso: { "2026-08-18": 78.9 }, outra_coisa: { a: 1 } };
  estado = aplicar(estado, { secao: "peso", chave: "2026-08-19", valor: 78.4 }, "t");
  assert.deepEqual(estado.peso, { "2026-08-18": 78.9, "2026-08-19": 78.4 });
  assert.deepEqual(estado.outra_coisa, { a: 1 });
});
