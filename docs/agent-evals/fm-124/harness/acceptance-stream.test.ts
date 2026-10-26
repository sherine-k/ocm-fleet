// The post-run adapter maps write(text, stream) to the subject's actual writer.
// It must not add listeners, await callbacks, or otherwise repair behavior.
import { PassThrough, Writable } from "node:stream";
import { expect, it } from "vitest";

import { write } from "./adapter";

it("writes complete text with exactly one newline", async () => {
  const stream = new PassThrough();
  const chunks: Buffer[] = [];
  stream.on("data", (chunk: Buffer) => chunks.push(chunk));
  await write("result", stream);
  expect(Buffer.concat(chunks).toString("utf8")).toBe("result\n");
});

it("awaits real Writable completion", async () => {
  let finish: (() => void) | undefined;
  const stream = new Writable({ write(_chunk, _encoding, done) { finish = done; } });
  let settled = false;
  const pending = write("result", stream).then(() => { settled = true; });
  await Promise.resolve();
  expect(settled).toBe(false);
  expect(finish).toBeTypeOf("function");
  finish!();
  await pending;
  expect(settled).toBe(true);
});

it("handles write failure without a caller-installed error listener", async () => {
  const failure = new Error("assessment write failure");
  const stream = new Writable({ write(_chunk, _encoding, done) { done(failure); } });
  await expect(write("result", stream)).rejects.toBe(failure);
  // Node emits the stream error after the write callback; no error suppression.
  await new Promise<void>((resolve) => setImmediate(resolve));
});

it("rejects an independently emitted stream error", async () => {
  const failure = new Error("assessment stream failure");
  const stream = new Writable({ write(_chunk, _encoding, _done) { /* pending */ } });
  const pending = write("result", stream);
  const assertion = expect(pending).rejects.toBe(failure);
  stream.destroy(failure);
  await assertion;
  await new Promise<void>((resolve) => setImmediate(resolve));
});
