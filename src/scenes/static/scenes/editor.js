"use strict";

for (const field of document.querySelectorAll('input[name="idempotency_key"]')) {
  if (globalThis.crypto?.randomUUID) {
    field.value = globalThis.crypto.randomUUID().replaceAll("-", "");
  }
}
